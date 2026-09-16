from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
import webbrowser
from datetime import date
from pathlib import Path
from typing import Any, Callable

from PIL import ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QDate, QEvent, QObject, QPointF, QRectF, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox as _QComboBox,
    QTabBar,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QDoubleSpinBox as _QDoubleSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QAbstractSpinBox,
    QHeaderView,
    QToolButton,
    QInputDialog,
)

from feishu_client import CONFIG_URL_PROGRESS, FeishuError, complete_user_auth, configure_and_begin_auth, environment_status, load_feishu_data, validate_feishu_url
from label_core import (
    LabelRecord,
    LabelLayout,
    LabelSettings,
    MAX_TEXT_LINES,
    CONTENT_FIELD_SLOTS,
    LOGO_WIDTH_MAX_MM,
    LOGO_WIDTH_MIN_MM,
    QR_SIZE_MAX_MM,
    QR_SIZE_MIN_MM,
    auto_mapping,
    clean,
    image_to_zpl,
    list_printers,
    load_local_rows,
    cancel_print_jobs,
    problematic_print_jobs,
    print_queue_jobs,
    records_from_rows,
    render_label,
    render_label_with_regions,
    send_raw,
    zebra_calibration_zpl,
    zebra_printers,
)


class QComboBox(_QComboBox):
    """Paper presets and field menus must not change when the mouse wheel passes over."""

    def wheelEvent(self, event):
        event.ignore()


class QDoubleSpinBox(_QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()


APP_NAME = "Crelabel"
APP_VERSION = "0.8.13"
MACHINE_URL = "https://ncn5zs910x3g.feishu.cn/base/SsZVbzJLvaZRKAsHQn0cKh82nJh?table=tblk6TQzvZ0yJgeh&view=vew9VeGGN3"
MACHINE_CODE_FIELDS = ("样机编号", "自动编号")
MATERIAL_URL = "https://ncn5zs910x3g.feishu.cn/wiki/FUmMw16QLiZcODka0WYcp7nZn8b?table=tblFeazbWqYNoWOj"


def machine_code_header(headers: list[str]) -> str:
    """整机编号优先用「样机编号」；旧表若仍有「自动编号」则回退。"""
    for name in MACHINE_CODE_FIELDS:
        if name in headers:
            return name
    return ""


NO_PRINT_OPTION = "<不打印>"
CUSTOM_OPTION = "<自定义内容>"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Crelabel"
CONFIG_FILE = CONFIG_DIR / "config.json"
ZEBRA_SETUP_URL = "https://www.zebra.com/us/en/support-downloads/software/printer-software/zebra-nucleus-connector.html"


STYLE = """
QWidget {
    color: #1D1D1F;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QMainWindow, QWidget#Root { background: #F5F5F7; }
QFrame#Header { background: rgba(255,255,255,245); border-bottom: 1px solid #E5E5EA; }
QFrame#Card { background: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 16px; }
QScrollArea#RightScroll, QWidget#RightPanel { background: #F5F5F7; border: none; }
QLabel#Brand { font-size: 23px; font-weight: 700; letter-spacing: -0.5px; }
QLabel#Subtitle { color: #6E6E73; font-size: 12px; }
QLabel#SectionTitle { font-size: 15px; font-weight: 650; }
QLabel#Hint { color: #6E6E73; font-size: 12px; }
QLabel#StatusChip { background: #EDF7EF; color: #207A39; border-radius: 11px; padding: 4px 10px; font-weight: 600; }
QLabel#WarningChip { background: #FFF4E5; color: #9A5B00; border-radius: 11px; padding: 4px 10px; font-weight: 600; }
QPushButton {
    background: #FFFFFF; border: 1px solid #D2D2D7; border-radius: 8px;
    padding: 7px 13px; min-height: 20px; font-weight: 550;
}
QPushButton:hover { background: #F5F5F7; border-color: #B8B8BD; }
QPushButton:pressed { background: #EDEDF0; }
QPushButton#Primary { background: #007AFF; color: white; border: 1px solid #007AFF; font-weight: 650; }
QPushButton#Primary:hover { background: #0873DD; }
QPushButton#Soft { background: #EEF5FF; color: #0066CC; border-color: #D7E8FF; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton#DateField {
    background: #FAFAFC; border: 1px solid #D8D8DD; border-radius: 8px;
    padding: 6px 9px; min-height: 22px; selection-background-color: #007AFF;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPushButton#DateField:focus { border: 1px solid #007AFF; background: white; }
QComboBox::drop-down { border: none; width: 24px; }
QFrame#Stepper { background: #FAFAFC; border: 1px solid #D8D8DD; border-radius: 9px; }
QDoubleSpinBox#StepValue { background: transparent; border: none; border-radius: 0; padding: 5px 2px; font-weight: 600; }
QToolButton#StepButton { background: transparent; border: none; min-width: 30px; max-width: 30px; min-height: 31px; font-size: 17px; font-weight: 650; color: #0066CC; }
QToolButton#StepButton:hover { background: #EEF5FF; }
QToolButton#StepButton:pressed { background: #DCEBFF; }
QLabel#ValuePill { background: #F2F2F7; color: #5B5B60; border-radius: 9px; padding: 6px 10px; font-size: 12px; font-weight: 600; }
QTableWidget { background: white; border: none; gridline-color: #ECECF0; selection-background-color: #E8F2FF; selection-color: #1D1D1F; }
QHeaderView::section { background: #F7F7F9; color: #55555A; border: none; border-bottom: 1px solid #E2E2E7; padding: 8px; font-weight: 600; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #C8C8CC; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: transparent; width: 14px; }
QFrame#CalendarSurface { background: white; border: 1px solid #DADAE0; border-radius: 16px; }
QLabel#CalendarMonth { font-size: 15px; font-weight: 650; }
QLabel#CalendarWeekday { color: #8E8E93; font-size: 11px; font-weight: 600; }
QToolButton#CalendarNav { background: #F2F2F7; border: none; border-radius: 14px; min-width: 28px; min-height: 28px; font-size: 20px; color: #0066CC; }
QToolButton#CalendarNav:hover { background: #E7F0FF; }
QPushButton#CalendarDay { background: transparent; border: none; border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0; font-weight: 500; }
QPushButton#CalendarDay:hover { background: #EEF5FF; color: #0066CC; }
QPushButton#CalendarDay[outside="true"] { color: #C7C7CC; }
QPushButton#CalendarDay[today="true"] { border: 1px solid #8EBEFF; color: #0066CC; }
QPushButton#CalendarDay[selected="true"] { background: #007AFF; color: white; border: none; font-weight: 650; }
QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E5E5EA;
    padding: 2px 10px;
    font-size: 13px;
}
QMenuBar::item {
    padding: 7px 12px;
    border-radius: 6px;
    background: transparent;
    margin: 3px 2px;
}
QMenuBar::item:selected { background: #EEF5FF; color: #0066CC; }
QMenuBar::item:pressed { background: #DCEBFF; color: #0066CC; }
QTabBar { background: transparent; border: none; }
QTabBar::tab {
    padding: 10px 24px; background: #F2F2F7; color: #1D1D1F;
    border: none; border-radius: 6px; margin-right: 6px;
}
QTabBar::tab:selected { background: #007AFF; color: white; }
QTabBar::tab:hover:!selected { background: #E8E8ED; }
"""


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)


class Worker(QRunnable):
    def __init__(self, function: Callable, *args, with_progress: bool = False, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.with_progress = with_progress
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.with_progress:
                self.kwargs["progress"] = self.signals.progress.emit
            result = self.function(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:
            details = str(exc).strip() or "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.signals.error.emit(details)


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    frame.setStyleSheet("QFrame#Card { background-color: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 16px; }")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    return frame, layout


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


def create_app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#007AFF"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 120, 120, 28, 28)
    painter.setPen(QColor("white"))
    font = QFont("Arial", 58, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "C")
    painter.end()
    return QIcon(pixmap)


class PreviewLabel(QLabel):
    elementSelected = Signal(str)
    elementMoved = Signal(str, float, float)
    elementResized = Signal(str, float, float)

    def __init__(self, text: str = ""):
        super().__init__(text)
        self.source_pixmap: QPixmap | None = None
        self.source_regions: dict[str, tuple[int, int, int, int]] = {}
        self.selected_element = "text_0"
        self.drag_position: QPointF | None = None
        self.drag_mode = ""
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_source_pixmap(self, pixmap: QPixmap | None, regions: dict[str, tuple[int, int, int, int]] | None = None):
        self.source_pixmap = pixmap
        self.source_regions = regions or {}
        if self.selected_element not in self.source_regions and self.source_regions:
            self.selected_element = next(iter(self.source_regions))
        self.fit_source()
        self.update()

    def set_selected_element(self, element: str):
        if element == "text" and "text_0" in self.source_regions:
            element = "text_0"
        if element in self.source_regions:
            self.selected_element = element
            self.update()

    def _display_rect(self) -> QRectF:
        displayed = self.pixmap()
        if not displayed or displayed.isNull():
            return QRectF()
        return QRectF(
            (self.width() - displayed.width()) / 2,
            (self.height() - displayed.height()) / 2,
            displayed.width(), displayed.height(),
        )

    def _widget_region(self, name: str) -> QRectF:
        if not self.source_pixmap or name not in self.source_regions:
            return QRectF()
        display = self._display_rect()
        x1, y1, x2, y2 = self.source_regions[name]
        sx = display.width() / self.source_pixmap.width()
        sy = display.height() / self.source_pixmap.height()
        width = max((x2 - x1) * sx, 28)
        height = max((y2 - y1) * sy, 28)
        return QRectF(display.x() + x1 * sx, display.y() + y1 * sy, width, height)

    def _element_at(self, position: QPointF) -> str:
        text_keys = sorted((name for name in self.source_regions if name.startswith("text_")), reverse=True)
        for name in ("logo", "qr", "barcode", *text_keys):
            if self._widget_region(name).adjusted(-12, -12, 12, 12).contains(position):
                return name
        return ""

    def _on_resize_handle(self, position: QPointF) -> bool:
        region = self._widget_region(self.selected_element)
        # Keep the visible handle compact, but give it a generous 30 px hit
        # target so it remains easy to grab on high-DPI and touch displays.
        handle = QRectF(region.right() - 15, region.bottom() - 15, 30, 30)
        return not region.isEmpty() and handle.contains(position)

    def fit_source(self):
        if not self.source_pixmap:
            super().setPixmap(QPixmap())
            return
        target = self.size() - QSize(24, 24)
        super().setPixmap(self.source_pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_source()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.source_pixmap:
            # Test the current handle before hit-testing overlapping elements.
            # Otherwise a click on the outer half of the handle can be treated
            # as a move (or as a neighbouring QR/barcode element).
            if self._on_resize_handle(event.position()):
                self.drag_position = event.position()
                self.drag_mode = "resize"
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                self.update()
                event.accept()
                return
            element = self._element_at(event.position())
            if element:
                self.selected_element = element
                self.elementSelected.emit(element)
            if not element:
                super().mousePressEvent(event)
                return
            self.drag_position = event.position()
            self.drag_mode = "resize" if self._on_resize_handle(event.position()) else "move"
            self.setCursor(Qt.CursorShape.SizeFDiagCursor if self.drag_mode == "resize" else Qt.CursorShape.ClosedHandCursor)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        displayed = self.pixmap()
        if self.drag_position is not None and displayed and displayed.width() > 0 and displayed.height() > 0:
            delta = event.position() - self.drag_position
            self.drag_position = event.position()
            signal = self.elementResized if self.drag_mode == "resize" else self.elementMoved
            signal.emit(self.selected_element, delta.x() / displayed.width(), delta.y() / displayed.height())
            event.accept()
            return
        if self._on_resize_handle(event.position()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._element_at(event.position()):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.drag_mode = ""
        self.setCursor(Qt.CursorShape.OpenHandCursor if self._element_at(event.position()) else Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for name in self.source_regions:
            if name == self.selected_element or not (name.startswith("text_") or name == "logo"):
                continue
            other = self._widget_region(name)
            if other.isEmpty():
                continue
            painter.setPen(QPen(QColor("#B8B8BD"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(other.adjusted(-3, -3, 3, 3), 3, 3)
        region = self._widget_region(self.selected_element)
        if not region.isEmpty():
            painter.setPen(QPen(QColor("#007AFF"), 2))
            painter.setBrush(QBrush(QColor(0, 122, 255, 18)))
            painter.drawRoundedRect(region.adjusted(-4, -4, 4, 4), 4, 4)
            handle = QRectF(region.right() - 6, region.bottom() - 6, 12, 12)
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(QColor("#007AFF"))
            painter.drawRoundedRect(handle, 2, 2)
        painter.end()


class ModernDateDialog(QDialog):
    def __init__(self, selected: QDate, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.selected = QDate(selected)
        self.visible_month = QDate(selected.year(), selected.month(), 1)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        surface = QFrame()
        surface.setObjectName("CalendarSurface")
        surface.setMinimumWidth(286)
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(16, 14, 16, 16)
        surface_layout.setSpacing(10)

        header = QHBoxLayout()
        self.previous_button = QToolButton()
        self.previous_button.setObjectName("CalendarNav")
        self.previous_button.setText("‹")
        self.previous_button.clicked.connect(lambda: self.change_month(-1))
        header.addWidget(self.previous_button)
        self.month_label = QLabel()
        self.month_label.setObjectName("CalendarMonth")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.month_label, 1)
        self.next_button = QToolButton()
        self.next_button.setObjectName("CalendarNav")
        self.next_button.setText("›")
        self.next_button.clicked.connect(lambda: self.change_month(1))
        header.addWidget(self.next_button)
        surface_layout.addLayout(header)

        self.days_grid = QGridLayout()
        self.days_grid.setContentsMargins(0, 0, 0, 0)
        self.days_grid.setHorizontalSpacing(6)
        self.days_grid.setVerticalSpacing(5)
        for column, text in enumerate(("一", "二", "三", "四", "五", "六", "日")):
            weekday = QLabel(text)
            weekday.setObjectName("CalendarWeekday")
            weekday.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.days_grid.addWidget(weekday, 0, column)
        surface_layout.addLayout(self.days_grid)

        today_button = QPushButton("回到今天")
        today_button.setObjectName("Soft")
        today_button.clicked.connect(self.choose_today)
        surface_layout.addWidget(today_button)
        outer.addWidget(surface)
        self.refresh_days()

    def change_month(self, offset: int):
        self.visible_month = self.visible_month.addMonths(offset)
        self.refresh_days()

    def choose_today(self):
        self.selected = QDate.currentDate()
        self.accept()

    def choose_date(self, value: QDate):
        self.selected = value
        self.accept()

    def refresh_days(self):
        self.month_label.setText(f"{self.visible_month.year()}年 {self.visible_month.month()}月")
        while self.days_grid.count() > 7:
            item = self.days_grid.takeAt(7)
            if item.widget():
                item.widget().deleteLater()
        first = self.visible_month.addDays(1 - self.visible_month.dayOfWeek())
        today = QDate.currentDate()
        for index in range(42):
            value = first.addDays(index)
            button = QPushButton(str(value.day()))
            button.setObjectName("CalendarDay")
            button.setProperty("outside", value.month() != self.visible_month.month())
            button.setProperty("today", value == today)
            button.setProperty("selected", value == self.selected)
            button.clicked.connect(lambda _checked=False, day=QDate(value): self.choose_date(day))
            self.days_grid.addWidget(button, 1 + index // 7, index % 7)


class ModernDateEdit(QPushButton):
    dateChanged = Signal(QDate)

    def __init__(self, value: QDate, parent: QWidget | None = None):
        super().__init__(parent)
        self._date = QDate(value)
        self.setObjectName("DateField")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.open_calendar)
        self.refresh_text()

    def date(self) -> QDate:
        return QDate(self._date)

    def setDate(self, value: QDate):
        if value != self._date:
            self._date = QDate(value)
            self.refresh_text()
            self.dateChanged.emit(QDate(self._date))

    def refresh_text(self):
        self.setText(f"{self._date.toString('yyyy-MM-dd')}     ▾")

    def open_calendar(self):
        popup = ModernDateDialog(self._date, self)
        point = self.mapToGlobal(self.rect().bottomLeft())
        popup.adjustSize()
        screen = self.screen().availableGeometry()
        x = min(point.x(), screen.right() - popup.width())
        y = point.y() if point.y() + popup.height() <= screen.bottom() else self.mapToGlobal(self.rect().topLeft()).y() - popup.height()
        popup.move(max(screen.left(), x), max(screen.top(), y))
        if popup.exec() == QDialog.DialogCode.Accepted:
            self.setDate(popup.selected)


class NumberStepper(QFrame):
    valueChanged = Signal(float)

    def __init__(self, minimum: float, maximum: float, step: float, value: float, decimals: int = 1, suffix: str = ""):
        super().__init__()
        self.setObjectName("Stepper")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.minus_button = QToolButton()
        self.minus_button.setObjectName("StepButton")
        self.minus_button.setText("−")
        self.spin = QDoubleSpinBox()
        self.spin.setObjectName("StepValue")
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setValue(value)
        self.spin.setMinimumWidth(78)
        self.plus_button = QToolButton()
        self.plus_button.setObjectName("StepButton")
        self.plus_button.setText("+")
        row.addWidget(self.minus_button)
        row.addWidget(self.spin, 1)
        row.addWidget(self.plus_button)
        self.minus_button.clicked.connect(lambda: self.spin.stepDown())
        self.plus_button.clicked.connect(lambda: self.spin.stepUp())
        self.spin.valueChanged.connect(self.valueChanged.emit)

    def value(self) -> float:
        return self.spin.value()

    def setValue(self, value: float):
        self.spin.setValue(value)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.spin.setEnabled(enabled)
        self.minus_button.setEnabled(enabled)
        self.plus_button.setEnabled(enabled)

class SetupDialog(QDialog):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crelabel 首次飞书配置")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("使用飞书扫码完成首次配置")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        import qrcode
        qr = qrcode.make(url).convert("RGB").resize((230, 230))
        qr_label = QLabel()
        qr_label.setPixmap(QPixmap.fromImage(ImageQt(qr)))
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qr_label)
        link = QLabel(f'<a href="{url}">无法扫码？在浏览器中打开配置页</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(link)
        hint = QLabel("在网页中完成应用配置后，Crelabel 会自动进入用户授权步骤。无需安装 Node.js 或命令行工具。")
        hint.setWordWrap(True)
        hint.setObjectName("Hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        waiting = QLabel("正在等待网页配置完成…")
        waiting.setObjectName("StatusChip")
        waiting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(waiting)


class AuthDialog(QDialog):
    complete_requested = Signal(str)

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.device_code = payload.get("device_code", "")
        self.setWindowTitle("飞书扫码授权")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("使用飞书扫码授权")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        url = payload.get("verification_url") or payload.get("verification_uri_complete") or ""
        if url:
            import qrcode
            qr = qrcode.make(url).convert("RGB").resize((230, 230))
            image = ImageQt(qr)
            qr_label = QLabel()
            qr_label.setPixmap(QPixmap.fromImage(image))
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(qr_label)
            link = QLabel(f'<a href="{url}">无法扫码？在浏览器中打开授权页</a>')
            link.setOpenExternalLinks(True)
            link.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(link)
        hint = QLabel("同事需要对目标多维表格拥有访问权限。完成授权后点击下方按钮。")
        hint.setWordWrap(True)
        hint.setObjectName("Hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self.complete_button = QPushButton("我已完成授权")
        self.complete_button.setObjectName("Primary")
        self.complete_button.clicked.connect(lambda: self.complete_requested.emit(self.device_code))
        layout.addWidget(self.complete_button)

    def set_waiting(self, waiting: bool):
        self.complete_button.setDisabled(waiting)
        self.complete_button.setText("正在确认授权…" if waiting else "我已完成授权")


class CrelabelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  {APP_VERSION}")
        self.setWindowIcon(create_app_icon())
        self.resize(1440, 900)
        self.setMinimumSize(1120, 720)
        self.thread_pool = QThreadPool.globalInstance()
        self.config_data = self._load_config()
        self._build_menu_bar()
        self.headers: list[str] = []
        self.raw_rows: list[dict[str, Any]] = []
        self.records: list[LabelRecord] = []
        self.mapping: dict[str, str] = {}
        self.display_headers: list[str] = []
        self.barcode_header = ""
        self._updating_columns = False
        self.line_scales = [100] * MAX_TEXT_LINES
        self.line_x = [0.0] * MAX_TEXT_LINES
        self.line_y = [0.0] * MAX_TEXT_LINES
        self.element_abs: dict[str, tuple[float, float]] = {}
        self.preview_pixmap: QPixmap | None = None
        self.setup_dialog: SetupDialog | None = None
        self.auth_dialog: AuthDialog | None = None
        self._updating_templates = False
        self._migrate_layout_templates()
        self._build_ui()
        self.refresh_printers()
        self._apply_saved_settings()
        self.on_printer_changed(self.printer_combo.currentText())

    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        profiles = self.config_data.setdefault("label_profiles", {})
        type_key = str(self.label_type.currentIndex())
        profile = profiles.setdefault(type_key, {})
        profile["show_logo"] = self.logo_check.isChecked()
        profile["show_barcode"] = self.barcode_check.isChecked()
        profile["show_qr"] = self.qr_check.isChecked()
        if self.records:
            profile["columns"] = [self.logical_column_selection(i) for i in range(len(self.column_combos))]
            profile["custom_contents"] = self.custom_values[:]
            profile["barcode_column"] = self.barcode_header
        payload = {
            "label_profiles": profiles,
            "machine_url": self.config_data.get("machine_url") or MACHINE_URL,
            "niimbot_symbol": self.niimbot_symbol.currentData(),
            "feishu_url": self._persistable_feishu_url(),
            "printer": self.printer_combo.currentText(),
            "width_mm": self.width_spin.value(),
            "height_mm": self.height_spin.value(),
            "dpi": 300,
            "date_mode": self.date_mode.currentIndex(),
            "print_method": self.print_method_combo.currentIndex(),
            "media_sensing": self.media_sensing_combo.currentData() or "gap",
            "layout_templates": self.config_data.get("layout_templates", {}),
            "active_template": self.config_data.get("active_template", {}),
            "layout": {
                "offset_x_mm": self.offset_x_step.value(),
                "offset_y_mm": self.offset_y_step.value(),
                "text_scale_percent": int(self.line_scales[0]),
                "text_spacing_mm": self.text_spacing_step.value(),
                "barcode_height_mm": self.barcode_height_step.value(),
                "barcode_width_percent": int(self.barcode_width_step.value()),
                "barcode_scale_percent": int(self.barcode_scale_step.value()),
                "qr_size_mm": self.qr_size_step.value(),
                "text_offset_x_mm": self.line_x[0],
                "text_offset_y_mm": self.line_y[0],
                "line_scale_percent": self.line_scales[:],
                "line_offset_x_mm": self.line_x[:],
                "line_offset_y_mm": self.line_y[:],
                "barcode_offset_x_mm": self.barcode_x_step.value(),
                "barcode_offset_y_mm": self.barcode_y_step.value(),
                "qr_offset_x_mm": self.qr_x_step.value(),
                "qr_offset_y_mm": self.qr_y_step.value(),
                "text_alignment": self.text_alignment_combo.currentData() or "center",
                "show_logo": self.logo_check.isChecked(),
                "show_barcode": self.barcode_check.isChecked(),
                "show_qr": self.qr_check.isChecked(),
                "logo_width_mm": self.logo_size_step.value(),
                "logo_offset_x_mm": self.logo_x_step.value(),
                "logo_offset_y_mm": self.logo_y_step.value(),
                "element_abs_mm": [[name, xy[0], xy[1]] for name, xy in sorted(self.element_abs.items())],
            },
            "columns": [self.logical_column_selection(index) for index in range(len(self.column_combos))],
            "custom_contents": self.custom_values,
            "barcode_column": self.barcode_header,
        }
        CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_menu_bar(self):
        bar = self.menuBar()
        bar.setNativeMenuBar(False)
        self.menu_actions = [
            bar.addAction("飞书扫码授权", self.start_auth),
            bar.addAction("检查飞书环境", self.check_environment),
            bar.addAction("导入 Excel / CSV", self.choose_file),
            bar.addAction("配置整机标签表格", self.configure_machine_source),
        ]

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 13, 22, 13)
        logo = QLabel()
        logo.setPixmap(create_app_icon().pixmap(42, 42))
        header_layout.addWidget(logo)
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel("Crelabel")
        brand.setObjectName("Brand")
        subtitle = QLabel("Prime Hand · 标签打印工作台")
        subtitle.setObjectName("Subtitle")
        brand_box.addWidget(brand)
        brand_box.addWidget(subtitle)
        header_layout.addLayout(brand_box)
        header_layout.addStretch()
        self.driver_chip = QLabel("正在检测打印机…")
        self.driver_chip.setObjectName("WarningChip")
        header_layout.addWidget(self.driver_chip)
        root_layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(14)
        splitter.setContentsMargins(18, 14, 18, 14)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        source_card, source_layout = card()
        source_layout.addWidget(section_title("标签类型"))
        source_row = QHBoxLayout()
        self.feishu_url = QLineEdit()
        self.label_type = QTabBar()
        self.label_type.addTab("物料标签")
        self.label_type.addTab("整机标签")
        self.label_type.setExpanding(False)
        self.label_type.setDrawBase(False)
        self.label_type.setDocumentMode(True)
        self.label_type.setUsesScrollButtons(False)
        self.label_type.setCurrentIndex(-1)
        self.label_type.currentChanged.connect(self.select_label_type)
        self.label_type.tabBarClicked.connect(
            lambda index: self.select_label_type(index)
            if index == self.label_type.currentIndex() and not self.feishu_url.text() else None
        )
        source_row.addWidget(self.label_type)
        source_row.addStretch()
        self.feishu_button = QPushButton("刷新数据")
        self.feishu_button.setObjectName("Primary")
        self.feishu_button.clicked.connect(lambda: self.load_feishu(True))
        source_row.addWidget(self.feishu_button)
        source_layout.addLayout(source_row)
        source_actions = QHBoxLayout()
        source_actions.addStretch()
        self.source_hint = QLabel("未加载数据")
        self.source_hint.setObjectName("Hint")
        source_actions.addWidget(self.source_hint)
        source_layout.addLayout(source_actions)
        left_layout.addWidget(source_card)

        columns_card, columns_layout = card()
        columns_header = QHBoxLayout()
        columns_header.addWidget(section_title("标签内容"))
        self.logo_check = QCheckBox("打印 Logo")
        self.logo_check.setToolTip("整机黑标纸会打成白 Logo。预览按黑底白字显示，可单独拖动和缩放。")
        self.logo_check.toggled.connect(self.on_logo_toggled)
        columns_header.addWidget(self.logo_check)
        self.barcode_check = QCheckBox("打印条形码")
        self.barcode_check.setToolTip("用料号/编号生成 Code 128。取消勾选后标签上不印条形码。")
        self.barcode_check.setChecked(True)
        self.barcode_check.toggled.connect(self.on_barcode_toggled)
        columns_header.addWidget(self.barcode_check)
        self.qr_check = QCheckBox("打印二维码")
        self.qr_check.setToolTip("用飞书记录链接生成二维码。取消勾选后标签上不印二维码。")
        self.qr_check.setChecked(True)
        self.qr_check.toggled.connect(self.on_qr_toggled)
        columns_header.addWidget(self.qr_check)
        columns_header.addStretch()
        self.barcode_hint = QLabel("条形码：等待数据")
        self.barcode_hint.setObjectName("Hint")
        columns_header.addWidget(self.barcode_hint)
        columns_layout.addLayout(columns_header)
        columns_row = QHBoxLayout()
        self.column_combos: list[QComboBox] = []
        saved_custom = self.config_data.get("custom_contents", [])
        self.custom_values: list[str] = [clean(saved_custom[index]) if index < len(saved_custom) else "" for index in range(CONTENT_FIELD_SLOTS)]
        self.custom_modes: list[bool] = [False] * CONTENT_FIELD_SLOTS
        for _index in range(CONTENT_FIELD_SLOTS):
            combo = QComboBox()
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            combo.setMinimumWidth(60)
            combo.setMinimumWidth(120)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.currentIndexChanged.connect(lambda combo_index, slot=_index: self.on_column_combo_changed(slot, combo_index))
            combo.editTextChanged.connect(lambda text, slot=_index: self.on_custom_text_edited(slot, text))
            self.column_combos.append(combo)
            columns_row.addWidget(combo, 1)
        self.date_controls = QWidget()
        date_row = QHBoxLayout(self.date_controls)
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(8)
        self.date_mode = QComboBox()
        self.date_mode.addItems(["不打印日期", "使用今天", "指定日期"])
        self.date_mode.setCurrentIndex(1)
        self.date_mode.setMinimumWidth(118)
        date_row.addWidget(self.date_mode, 1)
        self.date_edit = ModernDateEdit(QDate.currentDate())
        date_row.addWidget(self.date_edit, 1)
        columns_row.addWidget(self.date_controls, 1)
        columns_layout.addLayout(columns_row)
        self.niimbot_symbol = QComboBox()
        self.niimbot_symbol.addItem("不打印码 · 仅文字", "none")
        self.niimbot_symbol.addItem("文字 + 条形码（料号）", "barcode")
        self.niimbot_symbol.addItem("文字 + 二维码（记录链接）", "qr")
        self.niimbot_symbol.setCurrentIndex(max(0, self.niimbot_symbol.findData(self.config_data.get("niimbot_symbol", "barcode"))))
        self.niimbot_symbol.currentIndexChanged.connect(self.update_preview)
        columns_row.addWidget(self.niimbot_symbol, 1)
        self.niimbot_symbol.hide()
        left_layout.addWidget(columns_card)

        table_card, table_layout = card()
        table_header = QHBoxLayout()
        table_header.addWidget(section_title("选择记录"))
        table_header.addStretch()
        select_all = QPushButton("全选")
        select_all.clicked.connect(self.select_all_rows)
        table_header.addWidget(select_all)
        clear = QPushButton("清除选择")
        clear.clicked.connect(self.clear_selection)
        table_header.addWidget(clear)
        table_layout.addLayout(table_header)
        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.update_preview)
        self.table.cellDoubleClicked.connect(self.open_record_detail)
        self.table.setToolTip("点击选择记录；双击打开该行的飞书详情")
        table_layout.addWidget(self.table, 1)
        left_layout.addWidget(table_card, 1)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setObjectName("RightScroll")
        right = QWidget()
        right.setObjectName("RightPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 2, 0)
        right_layout.setSpacing(14)

        preview_card, preview_layout = card()
        preview_title_row = QHBoxLayout()
        preview_title_row.addWidget(section_title("实时预览"))
        preview_title_row.addStretch()
        preview_hint = QLabel("点击元素后拖动；拖右下角蓝点缩放")
        preview_hint.setObjectName("Hint")
        preview_title_row.addWidget(preview_hint)
        preview_layout.addLayout(preview_title_row)
        self.preview = PreviewLabel("加载数据后显示标签")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(285)
        self.preview.setStyleSheet("background:#ECECEF; border-radius:10px; color:#8E8E93;")
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview.elementSelected.connect(self.select_preview_element)
        self.preview.elementMoved.connect(self.move_preview_element)
        self.preview.elementResized.connect(self.resize_preview_element)
        preview_layout.addWidget(self.preview)
        editor_row = QHBoxLayout()
        editor_row.addWidget(QLabel("当前元素"))
        self.preview_element_combo = QComboBox()
        self.preview_element_combo.addItem("文字1", "text_0")
        self.preview_element_combo.addItem("条形码", "barcode")
        self.preview_element_combo.addItem("二维码", "qr")
        self.preview_element_combo.currentIndexChanged.connect(self.preview_element_changed)
        editor_row.addWidget(self.preview_element_combo, 1)
        editor_tip = QLabel("蓝框表示当前可编辑元素")
        editor_tip.setObjectName("Hint")
        editor_row.addWidget(editor_tip)
        preview_layout.addLayout(editor_row)
        right_layout.addWidget(preview_card)

        settings_card, settings_layout = card()
        settings_title_row = QHBoxLayout()
        settings_title_row.addWidget(section_title("标签设置"))
        settings_title_row.addStretch()
        device_pill = QLabel("ZD888TA / B1 Pro · 300 dpi")
        device_pill.setObjectName("ValuePill")
        settings_title_row.addWidget(device_pill)
        settings_layout.addLayout(settings_title_row)
        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(10)
        settings_grid.setVerticalSpacing(9)
        settings_grid.setColumnStretch(1, 1)
        settings_grid.setColumnStretch(3, 1)
        settings_grid.addWidget(QLabel("纸张预设"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["40 × 30 mm", "30 × 20 mm", "50 × 30 mm", "60 × 40 mm", "15 × 8 mm", "10 × 20 mm", "自定义"])
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        settings_grid.addWidget(self.preset_combo, 0, 1, 1, 3)
        settings_grid.addWidget(QLabel("宽度"), 1, 0)
        self.width_spin = NumberStepper(8, 120, 1, 40, 1, " mm")
        settings_grid.addWidget(self.width_spin, 1, 1)
        settings_grid.addWidget(QLabel("高度"), 1, 2)
        self.height_spin = NumberStepper(8, 100, 1, 30, 1, " mm")
        settings_grid.addWidget(self.height_spin, 1, 3)
        settings_grid.addWidget(QLabel("打印方式"), 2, 0)
        self.print_method_combo = QComboBox()
        self.print_method_combo.addItems(["热转印（碳带）", "热敏（无碳带）"])
        settings_grid.addWidget(self.print_method_combo, 2, 1)
        settings_grid.addWidget(QLabel("打印份数"), 2, 2)
        self.copies_spin = NumberStepper(1, 999, 1, 1, 0, "")
        settings_grid.addWidget(self.copies_spin, 2, 3)
        settings_grid.addWidget(QLabel("纸张感应"), 3, 0)
        self.media_sensing_combo = QComboBox()
        self.media_sensing_combo.addItem("间隙标签（常用）", "gap")
        self.media_sensing_combo.addItem("黑标标签", "mark")
        self.media_sensing_combo.addItem("连续标签纸", "continuous")
        self.media_sensing_combo.setToolTip("黑色标签表面不等于黑标纸；有标签间隙时请选择间隙标签。")
        settings_grid.addWidget(self.media_sensing_combo, 3, 1, 1, 3)
        settings_layout.addLayout(settings_grid)
        for widget in (self.width_spin, self.height_spin, self.copies_spin, self.print_method_combo, self.media_sensing_combo, self.date_mode, self.date_edit):
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.update_preview)
            if hasattr(widget, "currentIndexChanged"):
                widget.currentIndexChanged.connect(self.update_preview)
        self.date_edit.dateChanged.connect(self.update_preview)
        self.date_mode.currentIndexChanged.connect(self.update_date_controls)
        self.width_spin.valueChanged.connect(self.sync_preset_to_size)
        self.height_spin.valueChanged.connect(self.sync_preset_to_size)
        layout_card, layout_layout = card()
        layout_title_row = QHBoxLayout()
        layout_title_row.addWidget(section_title("版式调整"))
        layout_title_row.addStretch()
        layout_title_row.addWidget(QLabel("模板"))
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(150)
        self.template_combo.setToolTip("选择已保存的命名模板。可保存多套排版，例如 40×30 和 30×20。")
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        layout_title_row.addWidget(self.template_combo, 1)
        save_layout = QPushButton("保存模板")
        save_layout.setObjectName("Soft")
        save_layout.setToolTip("把当前纸张尺寸、元素位置、Logo/条码/二维码勾选保存成可命名模板")
        save_layout.clicked.connect(self.save_named_template)
        layout_title_row.addWidget(save_layout)
        delete_layout = QPushButton("删除模板")
        delete_layout.setToolTip("删除当前选中的命名模板，不影响出厂排版")
        delete_layout.clicked.connect(self.delete_named_template)
        layout_title_row.addWidget(delete_layout)
        reset_layout = QPushButton("恢复出厂")
        reset_layout.setToolTip("回到当前纸张尺寸的出厂排版，不删除已保存的模板")
        reset_layout.clicked.connect(self.reset_label_layout)
        layout_title_row.addWidget(reset_layout)
        layout_layout.addLayout(layout_title_row)
        layout_hint = QLabel("编号和 L/R 可单独拖动缩放。排好后点“保存模板”并命名，之后可从下拉框切换，例如 40×30 默认和 30×20 紧凑。")
        layout_hint.setObjectName("Hint")
        layout_hint.setWordWrap(True)
        layout_layout.addWidget(layout_hint)
        layout_grid = QGridLayout()
        layout_grid.setHorizontalSpacing(10)
        layout_grid.setVerticalSpacing(9)
        layout_grid.setColumnStretch(1, 1)
        layout_grid.setColumnStretch(3, 1)
        layout_grid.addWidget(QLabel("整体左右"), 0, 0)
        self.offset_x_step = NumberStepper(-4, 4, 0.5, 0, 1, " mm")
        layout_grid.addWidget(self.offset_x_step, 0, 1)
        layout_grid.addWidget(QLabel("整体上下"), 0, 2)
        self.offset_y_step = NumberStepper(-4, 4, 0.5, 0, 1, " mm")
        layout_grid.addWidget(self.offset_y_step, 0, 3)
        self.text_items_host = QWidget()
        self.text_items_box = QVBoxLayout(self.text_items_host)
        self.text_items_box.setContentsMargins(0, 0, 0, 0)
        self.text_items_box.setSpacing(8)
        self.line_scale_steppers: list[NumberStepper] = []
        self._text_control_signature: tuple = ()
        empty_items = QLabel("选择标签内容后，这里会单独列出每一项文字的大小，例如编号和 L/R。")
        empty_items.setObjectName("Hint")
        empty_items.setWordWrap(True)
        self.text_items_box.addWidget(empty_items)
        layout_grid.addWidget(self.text_items_host, 1, 0, 1, 4)
        layout_grid.addWidget(QLabel("文字间距"), 2, 0)
        self.text_spacing_step = NumberStepper(0, 0.8, 0.1, 0.2, 1, " mm")
        self.text_spacing_step.setToolTip("未单独拖开时，控制上下两行之间的默认距离")
        layout_grid.addWidget(self.text_spacing_step, 2, 1)
        layout_grid.addWidget(QLabel("文字对齐"), 2, 2)
        self.text_alignment_combo = QComboBox()
        self.text_alignment_combo.addItem("左对齐", "left")
        self.text_alignment_combo.addItem("居中对齐", "center")
        self.text_alignment_combo.addItem("右对齐", "right")
        self.text_alignment_combo.setCurrentIndex(1)
        layout_grid.addWidget(self.text_alignment_combo, 2, 3)
        layout_grid.addWidget(QLabel("二维码大小"), 3, 0)
        self.qr_size_step = NumberStepper(QR_SIZE_MIN_MM, QR_SIZE_MAX_MM, 0.5, 9.5, 1, " mm")
        self.qr_size_step.setToolTip("拖预览右下角或用此按钮调整二维码大小")
        layout_grid.addWidget(self.qr_size_step, 3, 1)
        layout_grid.addWidget(QLabel("条形码大小"), 3, 2)
        self.barcode_scale_step = NumberStepper(60, 125, 5, 100, 0, " %")
        self.barcode_scale_step.setToolTip("按比例同步调整条形码的宽度和高度")
        layout_grid.addWidget(self.barcode_scale_step, 3, 3)
        self.logo_size_label = QLabel("Logo 大小")
        layout_grid.addWidget(self.logo_size_label, 4, 0)
        self.logo_size_step = NumberStepper(LOGO_WIDTH_MIN_MM, LOGO_WIDTH_MAX_MM, 0.5, 10.0, 1, " mm")
        self.logo_size_step.setToolTip("按宽度缩放内置 Logo，高度按原图比例")
        layout_grid.addWidget(self.logo_size_step, 4, 1, 1, 3)
        self.text_scale_step = NumberStepper(50, 220, 5, 100, 0, " %")
        self.text_scale_step.hide()
        layout_layout.addLayout(layout_grid)

        # Element-specific geometry is edited directly in the preview. These
        # hidden steppers keep bounded numeric state and config compatibility.
        self.barcode_height_step = NumberStepper(4, 14, 0.5, 6.8, 1, " mm")
        self.text_x_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.text_y_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.barcode_x_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.barcode_y_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.qr_x_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.qr_y_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.logo_x_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.logo_y_step = NumberStepper(-120, 120, 0.2, 0, 1, " mm")
        self.barcode_width_step = NumberStepper(50, 125, 5, 100, 0, " %")
        for widget in (
            self.offset_x_step, self.offset_y_step, self.qr_size_step, self.logo_size_step,
            self.text_spacing_step,
            self.text_x_step, self.text_y_step, self.barcode_x_step, self.barcode_y_step,
            self.qr_x_step, self.qr_y_step, self.logo_x_step, self.logo_y_step,
        ):
            widget.valueChanged.connect(self.update_preview)
        self.logo_size_step.setEnabled(False)
        self.logo_size_label.setEnabled(False)
        self.text_scale_step.valueChanged.connect(self.on_text_scale_changed)
        self.barcode_scale_step.valueChanged.connect(self.sync_barcode_scale)
        self.text_alignment_combo.currentIndexChanged.connect(self.update_preview)
        right_layout.addWidget(layout_card)
        right_layout.addWidget(settings_card)

        printer_card, printer_layout = card()
        printer_layout.addWidget(section_title("打印机"))
        printer_row = QHBoxLayout()
        self.printer_combo = QComboBox()
        self.printer_combo.currentTextChanged.connect(self.on_printer_changed)
        printer_row.addWidget(self.printer_combo, 1)
        printer_refresh = QPushButton("刷新")
        printer_refresh.clicked.connect(self.refresh_printers)
        printer_row.addWidget(printer_refresh)
        printer_layout.addLayout(printer_row)
        self.driver_status = QLabel()
        self.driver_status.setObjectName("Hint")
        self.driver_status.setWordWrap(True)
        printer_layout.addWidget(self.driver_status)
        driver_button = QPushButton("安装 / 配置斑马驱动")
        driver_button.setObjectName("Soft")
        driver_button.clicked.connect(self.install_driver)
        printer_layout.addWidget(driver_button)
        printer_tools = QHBoxLayout()
        self.calibrate_button = QPushButton("校准纸张")
        self.calibrate_button.setObjectName("Soft")
        self.calibrate_button.clicked.connect(self.calibrate_zebra)
        printer_tools.addWidget(self.calibrate_button)
        repair_queue_button = QPushButton("检查 / 修复队列")
        repair_queue_button.clicked.connect(self.repair_print_queue)
        printer_tools.addWidget(repair_queue_button)
        printer_layout.addLayout(printer_tools)
        calibration_hint = QLabel("换纸或尺寸变化后先校准走纸；内容位置偏差用“整体左右 / 上下”微调。")
        calibration_hint.setObjectName("Hint")
        calibration_hint.setWordWrap(True)
        printer_layout.addWidget(calibration_hint)
        niimbot_driver = QPushButton("安装精臣 B1 Pro 驱动")
        niimbot_driver.clicked.connect(self.install_niimbot_driver)
        printer_layout.addWidget(niimbot_driver)
        printer_layout.addWidget(QLabel("精臣模式：一项文字 + 可选一种码，随纸张尺寸自动排版。"))
        right_layout.addWidget(printer_card)

        actions_card, actions_layout = card()
        export_button = QPushButton("导出 ZPL")
        export_button.clicked.connect(self.export_zpl)
        actions_layout.addWidget(export_button)
        print_selected = QPushButton("打印选中行")
        print_selected.setObjectName("Primary")
        print_selected.clicked.connect(lambda: self.print_rows(False))
        actions_layout.addWidget(print_selected)
        print_all = QPushButton("打印全部")
        print_all.clicked.connect(lambda: self.print_rows(True))
        actions_layout.addWidget(print_all)
        self.print_selected_button = print_selected
        self.print_all_button = print_all
        self.export_button = export_button
        self.selection_summary = QLabel("未选择记录")
        header_layout.addWidget(self.selection_summary)
        for button in (export_button, print_all, print_selected):
            actions_layout.removeWidget(button)
            header_layout.addWidget(button)
        actions_card.deleteLater()
        self.table.itemSelectionChanged.connect(self.update_action_state)
        self.copies_spin.valueChanged.connect(self.update_action_state)
        right_scroll.setWidget(right)
        right_scroll.setMinimumWidth(540)

        splitter.addWidget(left)
        splitter.addWidget(right_scroll)
        splitter.setSizes([850, 540])
        root_layout.addWidget(splitter, 1)

        status_frame = QFrame()
        status_frame.setObjectName("Header")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(18, 7, 18, 7)
        self.status = QLabel("就绪")
        self.status.setObjectName("Hint")
        status_layout.addWidget(self.status)
        status_layout.addStretch()
        self.version_label = QLabel(f"Crelabel {APP_VERSION}")
        self.version_label.setObjectName("Hint")
        status_layout.addWidget(self.version_label)
        root_layout.addWidget(status_frame)
        self.setCentralWidget(root)
        self.update_action_state()

    def _apply_saved_settings(self):
        self.feishu_url.setText("")
        self.width_spin.setValue(float(self.config_data.get("width_mm", 40)))
        self.height_spin.setValue(float(self.config_data.get("height_mm", 30)))
        self.date_mode.setCurrentIndex(int(self.config_data.get("date_mode", 1)))
        self.print_method_combo.setCurrentIndex(int(self.config_data.get("print_method", 0)))
        sensing_index = self.media_sensing_combo.findData(self.config_data.get("media_sensing", "gap"))
        self.media_sensing_combo.setCurrentIndex(max(0, sensing_index))
        saved_layout = self.config_data.get("layout", {})
        self.offset_x_step.setValue(float(saved_layout.get("offset_x_mm", 0)))
        self.offset_y_step.setValue(float(saved_layout.get("offset_y_mm", 0)))
        self.text_spacing_step.setValue(float(saved_layout.get("text_spacing_mm", 0.2)))
        barcode_scale = float(saved_layout.get("barcode_scale_percent", saved_layout.get("barcode_width_percent", 100)))
        self.barcode_scale_step.setValue(max(60, min(125, barcode_scale)))
        self.sync_barcode_scale(self.barcode_scale_step.value())
        self.qr_size_step.setValue(float(saved_layout.get("qr_size_mm", 9.5)))
        saved_scales = saved_layout.get("line_scale_percent") or [saved_layout.get("text_scale_percent", 100)]
        saved_xs = saved_layout.get("line_offset_x_mm") or [saved_layout.get("text_offset_x_mm", 0)]
        saved_ys = saved_layout.get("line_offset_y_mm") or [saved_layout.get("text_offset_y_mm", 0)]
        for index in range(MAX_TEXT_LINES):
            self.line_scales[index] = int(saved_scales[index]) if index < len(saved_scales) else 100
            self.line_x[index] = float(saved_xs[index]) if index < len(saved_xs) else 0.0
            self.line_y[index] = float(saved_ys[index]) if index < len(saved_ys) else 0.0
        self.text_scale_step.blockSignals(True)
        self.text_scale_step.setValue(self.line_scales[0])
        self.text_scale_step.blockSignals(False)
        self.text_x_step.setValue(self.line_x[0])
        self.text_y_step.setValue(self.line_y[0])
        self.barcode_x_step.setValue(float(saved_layout.get("barcode_offset_x_mm", 0)))
        self.barcode_y_step.setValue(float(saved_layout.get("barcode_offset_y_mm", 0)))
        self.qr_x_step.setValue(float(saved_layout.get("qr_offset_x_mm", 0)))
        self.qr_y_step.setValue(float(saved_layout.get("qr_offset_y_mm", 0)))
        self.logo_size_step.setValue(float(saved_layout.get("logo_width_mm", 10)))
        self.logo_x_step.setValue(float(saved_layout.get("logo_offset_x_mm", 0)))
        self.logo_y_step.setValue(float(saved_layout.get("logo_offset_y_mm", 0)))
        self.element_abs = self._parse_element_abs(saved_layout.get("element_abs_mm", []))
        self._apply_type_logo_default(self.label_type.currentIndex())
        alignment_index = self.text_alignment_combo.findData(saved_layout.get("text_alignment", "center"))
        self.text_alignment_combo.setCurrentIndex(alignment_index if alignment_index >= 0 else 1)
        self.update_date_controls()
        self.sync_preset_to_size()
        self._refresh_template_combo()
        self._sync_code_controls()

    def _persistable_feishu_url(self) -> str:
        url = self.feishu_url.text().strip()
        if not url or "/share/" in url:
            index = self.label_type.currentIndex()
            if index == 1:
                return self.config_data.get("machine_url") or MACHINE_URL
            if index == 0:
                return MATERIAL_URL
            return self.config_data.get("machine_url") or MACHINE_URL
        return url

    def set_busy(self, busy: bool, text: str = ""):
        self._busy = busy
        current = self.label_type.currentIndex()
        self.feishu_button.setDisabled(busy)
        self.label_type.blockSignals(True)
        self.label_type.setDisabled(busy)
        if current >= 0:
            self.label_type.setCurrentIndex(current)
        self.label_type.blockSignals(False)
        for action in getattr(self, "menu_actions", []):
            action.setEnabled(not busy)
        self.feishu_button.setText("正在读取…" if busy else "刷新数据")
        self.update_action_state()
        if text:
            self.status.setText(text)

    def run_worker(self, function: Callable, *args, on_finished: Callable | None = None, on_error: Callable | None = None, on_progress: Callable | None = None, with_progress: bool = False, **kwargs):
        worker = Worker(function, *args, with_progress=with_progress, **kwargs)
        worker.signals.progress.connect(on_progress or self.status.setText)
        worker.signals.error.connect(on_error or self.handle_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.thread_pool.start(worker)
        return worker

    def handle_error(self, message: str):
        self.set_busy(False)
        if self.setup_dialog:
            self.setup_dialog.accept()
            self.setup_dialog = None
        self.status.setText(message)
        QMessageBox.critical(self, APP_NAME, message)

    def choose_file(self):
        path, _filter = QFileDialog.getOpenFileName(self, "选择物料表", "", "物料表 (*.xlsx *.xlsm *.csv *.json)")
        if not path:
            return
        try:
            headers, rows, title = load_local_rows(path)
            self.apply_rows(headers, rows, title)
            self.source_hint.setText(Path(path).name)
            self.status.setText(f"已导入 {len(self.records)} 条记录")
        except Exception as exc:
            self.handle_error(str(exc))

    def select_label_type(self, index):
        if getattr(self, "_busy", False) or getattr(self, "_selecting_type", False):
            return
        self._selecting_type = True
        try:
            previous = self.label_type.currentIndex()
            self.label_type.blockSignals(True)
            self.label_type.setCurrentIndex(index)
            self.label_type.blockSignals(False)
            self._apply_type_logo_default(index)
            self._sync_date_controls_visibility()
            self.update_barcode_hint()
            self._refresh_template_combo()
            if previous != index:
                applied = False
                active_name = self.config_data.get("active_template", {}).get(str(index), "")
                if active_name:
                    applied = self._apply_named_template(active_name, record_active=False)
                if not applied:
                    saved = self.config_data.get("saved_layouts", {}).get(str(index))
                    if saved:
                        try:
                            self._apply_layout_snapshot(saved)
                            applied = True
                        except Exception:
                            self.element_abs = {}
            self.records = []
            self.table.setRowCount(0)
            self.preview.set_source_pixmap(None)
            self.barcode_header = ""
            self.update_action_state()
            url = MATERIAL_URL if index == 0 else (self.config_data.get("machine_url") or MACHINE_URL)
            self.feishu_url.setText(url)
            if not url:
                self.source_hint.setText("整机标签表格待配置：在顶部菜单填写链接")
                return
            self.load_feishu(index == 1)
        finally:
            self._selecting_type = False

    def configure_machine_source(self):
        url, ok = QInputDialog.getText(self, "整机标签表格", "填写整机多维表格原始链接：", text=self.config_data.get("machine_url", ""))
        if ok and url.strip():
            try:
                validate_feishu_url(url.strip())
            except FeishuError as exc:
                self.handle_error(str(exc))
                return
            self.config_data["machine_url"] = url.strip()
            self._save_config()
            if self.label_type.currentIndex() == 1:
                self.select_label_type(1)

    def load_feishu(self, force_refresh: bool):
        url = self.feishu_url.text().strip()
        if not url:
            QMessageBox.information(self, APP_NAME, "请先选择标签类型；整机表格可在顶部菜单配置。")
            return
        try:
            validate_feishu_url(url)
        except FeishuError as exc:
            self.source_hint.setText("链接类型不支持")
            self.feishu_url.setFocus()
            QMessageBox.warning(self, "请使用原始多维表格链接", str(exc))
            return
        self.set_busy(True, "正在连接飞书…")
        self.run_worker(
            load_feishu_data,
            url,
            force_refresh=force_refresh,
            with_progress=True,
            on_finished=self.feishu_loaded,
        )

    def feishu_loaded(self, data: dict):
        try:
            headers = [clean(value) for value in data.get("fields", [])]
            if "记录分享链接" not in headers:
                headers.append("记录分享链接")
            rows = []
            for item in data.get("records", []):
                values = {header: item.get("fields", {}).get(header, "") for header in headers}
                values["记录分享链接"] = item.get("record_share_link", "")
                rows.append(values)
            self.apply_rows(headers, rows, data.get("title", "飞书多维表格"))
            mode = "本机缓存" if data.get("cache_hit") else "飞书在线"
            self.source_hint.setText(f"{data.get('title', '飞书多维表格')} · {mode}")
            self.status.setText(f"已通过{mode}读取 {len(self.records)} 条；二维码链接 {sum(bool(r.link) for r in self.records)} 条")
        except Exception as exc:
            self.handle_error(str(exc) or "飞书数据已读取，但填入表格失败。")
        finally:
            self.set_busy(False)

    def apply_rows(self, headers: list[str], rows: list[dict[str, Any]], title: str):
        self.headers = headers
        self.raw_rows = rows
        self.mapping = auto_mapping(headers)
        machine = self.label_type.currentIndex() == 1
        self.date_mode.setEnabled(not machine and not self.is_niimbot())
        self.date_mode.setToolTip("整机标签打印样机编号，不附加入库日期" if machine else "")
        self._sync_date_controls_visibility()
        profile = self.config_data.get("label_profiles", {}).get(str(self.label_type.currentIndex()), {})
        code_header = ""
        if machine:
            code_header = machine_code_header(headers)
            if not code_header:
                raise ValueError("整机表缺少“样机编号”字段，请检查配置的表格。")
            self.mapping["code"] = code_header
            self.mapping["sn"] = code_header
            self.mapping["link"] = "记录分享链接"
        self.records = records_from_rows(headers, rows, self.mapping)
        link_header = self.mapping.get("link", "")
        available_headers = [header for header in headers if header != link_header]
        priority_headers = []
        for field_name in ("name", "code"):
            header = self.mapping.get(field_name, "")
            if header and header in available_headers and header not in priority_headers:
                priority_headers.append(header)
        self.display_headers = priority_headers + [header for header in available_headers if header not in priority_headers]
        if machine:
            preferred = [h for h in (code_header, "左右手", "整机状态", "当前所在位置") if h in available_headers]
            self.display_headers = preferred + [h for h in available_headers if h not in preferred]
        choices = [NO_PRINT_OPTION, CUSTOM_OPTION] + self.display_headers
        defaults = [self.mapping.get("name", ""), self.mapping.get("code", ""), self.mapping.get("supplier", "")]
        defaults = [value for value in defaults if value in self.display_headers]
        defaults += [header for header in self.display_headers if header not in defaults]
        if machine:
            machine_defaults = [header for header in (code_header, "左右手") if header in self.display_headers]
            defaults = machine_defaults + [header for header in self.display_headers if header not in machine_defaults]
        saved = profile.get("columns", self.config_data.get("columns", []))
        custom = profile.get("custom_contents", self.config_data.get("custom_contents", []))
        self.custom_values = [clean(custom[i]) if i < len(custom) else "" for i in range(CONTENT_FIELD_SLOTS)]
        if machine and not profile.get("columns"):
            saved = defaults[:2] + [NO_PRINT_OPTION] * max(0, CONTENT_FIELD_SLOTS - 2)
        used_headers: set[str] = set()
        for index, combo in enumerate(self.column_combos):
            combo.setVisible(not self.is_niimbot() or index == 0)
            combo.blockSignals(True)
            combo.setEditable(False)
            self.custom_modes[index] = False
            combo.clear()
            combo.addItems(choices)
            desired = saved[index] if index < len(saved) and saved[index] in choices else (defaults[index] if index < min(3, len(defaults)) else NO_PRINT_OPTION)
            if desired not in (NO_PRINT_OPTION, CUSTOM_OPTION) and desired in used_headers:
                desired = NO_PRINT_OPTION
            combo.setCurrentText(desired)
            if desired == CUSTOM_OPTION:
                self.custom_modes[index] = True
                combo.setEditable(True)
                combo.lineEdit().setPlaceholderText("输入自定义打印内容")
                combo.setEditText(self.custom_values[index])
            if desired not in (NO_PRINT_OPTION, CUSTOM_OPTION):
                used_headers.add(desired)
            combo.blockSignals(False)
        self.refresh_column_availability()
        configured_barcode = profile.get("barcode_column", self.config_data.get("barcode_column", ""))
        detected_barcode = self.mapping.get("code", "") or self.mapping.get("sn", "")
        if machine:
            self.barcode_header = code_header
        if self.barcode_header not in self.display_headers:
            self.barcode_header = configured_barcode if configured_barcode in self.display_headers else detected_barcode
        if not self.barcode_header and defaults:
            self.barcode_header = defaults[0]
        self.update_barcode_hint()
        self._sync_code_controls()
        self.populate_table()
        try:
            self.update_preview()
        except Exception as exc:
            self.preview.set_source_pixmap(None)
            self.preview.setText(str(exc))
            self.status.setText(f"预览失败：{exc}")
        self._save_config()

    def populate_table(self):
        columns = ["行"] + self.display_headers
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(self.records))
        for row_index, record in enumerate(self.records):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(record.source_row)))
            for column_index, header in enumerate(self.display_headers, start=1):
                self.table.setItem(row_index, column_index, QTableWidgetItem(record.raw_fields.get(header, "")))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 54)
        for index in range(1, min(self.table.columnCount(), 6)):
            self.table.setColumnWidth(index, 170 if index > 1 else 250)
        if self.records:
            self.table.selectRow(0)

    def selected_records(self, all_rows: bool = False) -> list[LabelRecord]:
        if all_rows:
            return self.records[:]
        indexes = sorted({item.row() for item in self.table.selectedItems()})
        return [self.records[index] for index in indexes]

    def open_record_detail(self, row: int, _column: int):
        if 0 <= row < len(self.records) and self.records[row].link:
            webbrowser.open(self.records[row].link)

    def update_action_state(self, *_args):
        selected = len(self.selected_records())
        busy = getattr(self, "_busy", False)
        self.selection_summary.setText(f"已选 {selected}/{len(self.records)} 条 · {selected * int(self.copies_spin.value())} 张")
        self.print_selected_button.setEnabled(bool(selected) and not busy)
        self.export_button.setEnabled(bool(selected) and not busy)
        self.print_all_button.setEnabled(bool(self.records) and not busy)

    def validate_print_records(self, records):
        if self.label_type.currentIndex() == 1:
            invalid = [str(r.source_row) for r in records if not r.code.strip(" -") or not r.link or not self.machine_side(r)]
            if invalid:
                raise ValueError("以下行缺少完整样机编号、左右手或详情链接，暂不能打印：" + "、".join(invalid))

    def machine_side(self, record):
        return {"左手": "L", "右手": "R", "L": "L", "R": "R"}.get(clean(record.raw_fields.get("左右手", "")), "")

    def selected_columns(self, record: LabelRecord) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        seen: set[str] = set()
        for index, combo in enumerate(self.column_combos):
            header = self.logical_column_selection(index)
            if self.is_niimbot() and index > 0:
                continue
            if header == CUSTOM_OPTION:
                value = clean(self.custom_values[index])
                if value:
                    result.append(("", value))
            elif header and header != NO_PRINT_OPTION and header not in seen:
                result.append((header, record.raw_fields.get(header, "")))
                seen.add(header)
        return result

    def logical_column_selection(self, index: int) -> str:
        if 0 <= index < len(self.custom_modes) and self.custom_modes[index]:
            return CUSTOM_OPTION
        return self.column_combos[index].currentText()

    def on_column_combo_changed(self, slot: int, combo_index: int):
        if self._updating_columns:
            return
        combo = self.column_combos[slot]
        selected = combo.itemText(combo_index) if combo_index >= 0 else ""
        if selected == CUSTOM_OPTION:
            self._updating_columns = True
            try:
                self.custom_modes[slot] = True
                combo.setEditable(True)
                combo.lineEdit().setPlaceholderText("输入自定义打印内容")
                combo.setEditText(self.custom_values[slot])
                combo.lineEdit().selectAll()
                combo.lineEdit().setFocus()
            finally:
                self._updating_columns = False
        elif combo_index >= 0:
            self.custom_modes[slot] = False
            combo.setEditable(False)
        self.refresh_column_availability()
        self.update_preview()

    def on_custom_text_edited(self, slot: int, text: str):
        if self._updating_columns or not self.custom_modes[slot]:
            return
        if text not in (NO_PRINT_OPTION, CUSTOM_OPTION, *self.display_headers):
            self.custom_values[slot] = text
        self.update_preview()

    def refresh_column_availability(self):
        self._updating_columns = True
        try:
            seen: set[str] = set()
            for combo_index, combo in enumerate(self.column_combos):
                current = self.logical_column_selection(combo_index)
                if current not in ("", NO_PRINT_OPTION, CUSTOM_OPTION) and current in seen:
                    self.custom_modes[combo_index] = False
                    combo.setEditable(False)
                    combo.setCurrentText(NO_PRINT_OPTION)
                    current = NO_PRINT_OPTION
                if current not in ("", NO_PRINT_OPTION, CUSTOM_OPTION):
                    seen.add(current)
            for combo_index, combo in enumerate(self.column_combos):
                current = self.logical_column_selection(combo_index)
                model = combo.model()
                for index in range(combo.count()):
                    header = combo.itemText(index)
                    item = model.item(index) if hasattr(model, "item") else None
                    if item:
                        item.setEnabled(header in (NO_PRINT_OPTION, CUSTOM_OPTION) or header == current or header not in seen)
        finally:
            self._updating_columns = False

    def update_barcode_hint(self):
        barcode = self.barcode_header or "未识别"
        if not self.barcode_check.isChecked():
            barcode = "不打印"
        qr = "飞书记录链接" if self.qr_check.isChecked() else "不打印"
        self.barcode_hint.setText(f"条形码：{barcode} · 二维码：{qr}")

    def barcode_value(self, record: LabelRecord) -> str:
        value = clean(record.raw_fields.get(self.barcode_header, "")) if self.barcode_header else ""
        return value or record.code or record.sn

    def label_settings(self) -> LabelSettings:
        return LabelSettings(self.width_spin.value(), self.height_spin.value(), 300)

    def label_layout(self) -> LabelLayout:
        return LabelLayout(
            show_barcode=self.barcode_check.isChecked(),
            show_qr=self.qr_check.isChecked(),
            niimbot_mode=("qr" if self.label_type.currentIndex() == 1 else (self.niimbot_symbol.currentData() or "none")) if self.is_niimbot() else "",
            offset_x_mm=self.offset_x_step.value(),
            offset_y_mm=self.offset_y_step.value(),
            text_scale_percent=int(self.line_scales[0]),
            text_spacing_mm=self.text_spacing_step.value(),
            barcode_height_mm=self.barcode_height_step.value(),
            barcode_width_percent=int(self.barcode_width_step.value()),
            qr_size_mm=self.qr_size_step.value(),
            text_offset_x_mm=0.0,
            text_offset_y_mm=0.0,
            barcode_offset_x_mm=self.barcode_x_step.value(),
            barcode_offset_y_mm=self.barcode_y_step.value(),
            qr_offset_x_mm=self.qr_x_step.value(),
            qr_offset_y_mm=self.qr_y_step.value(),
            text_alignment=self.text_alignment_combo.currentData() or "center",
            line_scale_percent=tuple(int(value) for value in self.line_scales),
            line_offset_x_mm=tuple(float(value) for value in self.line_x),
            line_offset_y_mm=tuple(float(value) for value in self.line_y),
            show_logo=self.logo_check.isChecked(),
            logo_width_mm=self.logo_size_step.value(),
            logo_offset_x_mm=self.logo_x_step.value(),
            logo_offset_y_mm=self.logo_y_step.value(),
            element_abs_mm=tuple((name, xy[0], xy[1]) for name, xy in sorted(self.element_abs.items())),
        )

    def _apply_type_logo_default(self, index: int):
        profile = self.config_data.get("label_profiles", {}).get(str(index), {}) if index in (0, 1) else {}
        if index not in (0, 1):
            logo = False
            barcode = True
            qr = True
        else:
            logo = bool(profile["show_logo"]) if "show_logo" in profile else index == 1
            barcode = bool(profile["show_barcode"]) if "show_barcode" in profile else index != 1
            qr = bool(profile["show_qr"]) if "show_qr" in profile else True
        self.logo_check.blockSignals(True)
        self.logo_check.setChecked(logo)
        self.logo_check.blockSignals(False)
        self.barcode_check.blockSignals(True)
        self.barcode_check.setChecked(barcode)
        self.barcode_check.blockSignals(False)
        self.qr_check.blockSignals(True)
        self.qr_check.setChecked(qr)
        self.qr_check.blockSignals(False)
        self._sync_code_controls()

    def on_logo_toggled(self, checked: bool):
        self._sync_code_controls()
        self.update_preview()

    def on_barcode_toggled(self, checked: bool):
        self._sync_code_controls()
        self.update_barcode_hint()
        self.update_preview()

    def on_qr_toggled(self, checked: bool):
        self._sync_code_controls()
        self.update_barcode_hint()
        self.update_preview()

    def _sync_code_controls(self):
        compact = self.is_niimbot()
        logo_on = self.logo_check.isChecked() and not compact
        barcode_on = self.barcode_check.isChecked() and not compact
        qr_on = self.qr_check.isChecked() and not compact
        self.logo_size_step.setEnabled(logo_on)
        self.logo_size_label.setEnabled(logo_on)
        self.barcode_scale_step.setEnabled(barcode_on)
        self.qr_size_step.setEnabled(qr_on)

    def _sync_date_controls_visibility(self):
        machine = self.label_type.currentIndex() == 1
        compact = self.is_niimbot()
        self.date_controls.setVisible(not machine and not compact)
        self.date_mode.setEnabled(not machine and not compact)
        self.date_edit.setEnabled(not machine and not compact)
        self.update_date_controls()

    def printed_date(self) -> str:
        if self.label_type.currentIndex() == 1:
            return ""
        if self.is_niimbot():
            return ""
        if self.date_mode.currentIndex() == 0:
            return ""
        if self.date_mode.currentIndex() == 1:
            return date.today().isoformat()
        return self.date_edit.date().toString("yyyy-MM-dd")

    def update_preview(self, *_args):
        self.update_date_controls()
        records = self.selected_records(False)
        if not records:
            self.preview.setText("加载数据后显示标签")
            self.preview.set_source_pixmap(None)
            return
        try:
            record = records[0]
            columns = self.selected_columns(record)
            image, regions = render_label_with_regions(
                record, columns, self.label_settings(),
                self.printed_date(), self.label_layout(), self.barcode_value(record),
            )
            image = image.convert("RGB")
            if self.label_type.currentIndex() == 1:
                image = ImageOps.invert(image)
            self.preview_pixmap = QPixmap.fromImage(ImageQt(image))
            self._refresh_preview_elements(regions, columns)
            self.preview.set_source_pixmap(self.preview_pixmap, regions)
            self._save_config()
        except Exception as exc:
            self.preview.set_source_pixmap(None)
            self.preview.setText(str(exc))
            self.status.setText(f"预览失败：{exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_preview()

    def _fit_preview(self):
        if not self.preview_pixmap:
            return
        self.preview.fit_source()

    def update_date_controls(self, *_args):
        self.date_edit.setVisible(self.date_mode.currentIndex() == 2)

    def _parse_element_abs(self, raw) -> dict[str, tuple[float, float]]:
        result: dict[str, tuple[float, float]] = {}
        for item in raw or []:
            try:
                name, x_mm, y_mm = item
            except (TypeError, ValueError):
                continue
            if isinstance(name, str):
                result[name] = (float(x_mm), float(y_mm))
        return result

    def _layout_snapshot(self) -> dict:
        return {
            "width_mm": self.width_spin.value(),
            "height_mm": self.height_spin.value(),
            "line_scales": self.line_scales[:],
            "line_x": self.line_x[:],
            "line_y": self.line_y[:],
            "show_logo": self.logo_check.isChecked(),
            "show_barcode": self.barcode_check.isChecked(),
            "show_qr": self.qr_check.isChecked(),
            "date_mode": self.date_mode.currentIndex(),
            "layout": {
                "offset_x_mm": self.offset_x_step.value(),
                "offset_y_mm": self.offset_y_step.value(),
                "text_spacing_mm": self.text_spacing_step.value(),
                "barcode_width_percent": int(self.barcode_width_step.value()),
                "barcode_scale_percent": int(self.barcode_scale_step.value()),
                "qr_size_mm": self.qr_size_step.value(),
                "barcode_offset_x_mm": self.barcode_x_step.value(),
                "barcode_offset_y_mm": self.barcode_y_step.value(),
                "qr_offset_x_mm": self.qr_x_step.value(),
                "qr_offset_y_mm": self.qr_y_step.value(),
                "text_alignment": self.text_alignment_combo.currentData() or "center",
                "logo_width_mm": self.logo_size_step.value(),
                "logo_offset_x_mm": self.logo_x_step.value(),
                "logo_offset_y_mm": self.logo_y_step.value(),
                "element_abs_mm": [[name, xy[0], xy[1]] for name, xy in sorted(self.element_abs.items())],
            },
        }

    def _type_template_key(self) -> str:
        index = self.label_type.currentIndex()
        return str(index if index in (0, 1) else 0)

    def _migrate_layout_templates(self):
        templates = self.config_data.setdefault("layout_templates", {})
        active = self.config_data.setdefault("active_template", {})
        saved = self.config_data.get("saved_layouts", {})
        if not isinstance(templates, dict):
            templates = {}
            self.config_data["layout_templates"] = templates
        for key, snapshot in saved.items():
            bucket = templates.setdefault(str(key), [])
            if not isinstance(bucket, list):
                bucket = []
                templates[str(key)] = bucket
            if bucket or not isinstance(snapshot, dict):
                continue
            named = dict(snapshot)
            named["name"] = "默认布局"
            bucket.append(named)
            active.setdefault(str(key), "默认布局")

    def _templates_for_type(self, type_key: str | None = None) -> list[dict]:
        key = type_key or self._type_template_key()
        bucket = self.config_data.setdefault("layout_templates", {}).setdefault(key, [])
        if not isinstance(bucket, list):
            bucket = []
            self.config_data["layout_templates"][key] = bucket
        return bucket

    def _find_template(self, name: str, type_key: str | None = None) -> dict | None:
        needle = clean(name)
        for item in self._templates_for_type(type_key):
            if clean(item.get("name", "")) == needle:
                return item
        return None

    def _refresh_template_combo(self, selected_name: str | None = None):
        if not hasattr(self, "template_combo"):
            return
        key = self._type_template_key()
        names = [clean(item.get("name", "")) for item in self._templates_for_type(key) if clean(item.get("name", ""))]
        current = selected_name or self.config_data.get("active_template", {}).get(key, "")
        self._updating_templates = True
        try:
            self.template_combo.clear()
            self.template_combo.addItem("未选择模板")
            for name in names:
                self.template_combo.addItem(name)
            target = current if current in names else "未选择模板"
            self.template_combo.setCurrentText(target)
        finally:
            self._updating_templates = False

    def on_template_selected(self, _index: int = 0):
        if self._updating_templates:
            return
        name = self.template_combo.currentText()
        if not name or name == "未选择模板":
            return
        self._apply_named_template(name)

    def save_named_template(self):
        if self.label_type.currentIndex() not in (0, 1):
            QMessageBox.information(self, APP_NAME, "请先选择物料标签或整机标签，再保存模板。")
            return
        kind = "物料" if self.label_type.currentIndex() == 0 else "整机"
        suggested = self.template_combo.currentText()
        if not suggested or suggested == "未选择模板":
            suggested = f"{kind} {int(self.width_spin.value())}×{int(self.height_spin.value())}"
        name, ok = QInputDialog.getText(self, "保存模板", "模板名称：", text=suggested)
        if not ok:
            return
        stored = self._store_template(name)
        if stored:
            QMessageBox.information(self, APP_NAME, f"已保存模板“{stored}”。可在下拉框中随时切换。")

    def _store_template(self, name: str) -> str:
        name = clean(name)
        if not name or name == "未选择模板":
            QMessageBox.information(self, APP_NAME, "请输入模板名称。")
            return ""
        self._freeze_elements_from_preview()
        snapshot = self._layout_snapshot()
        snapshot["name"] = name
        bucket = self._templates_for_type()
        for index, item in enumerate(bucket):
            if clean(item.get("name", "")) == name:
                bucket[index] = snapshot
                break
        else:
            bucket.append(snapshot)
        self.config_data.setdefault("active_template", {})[self._type_template_key()] = name
        self.config_data.setdefault("saved_layouts", {})[self._type_template_key()] = snapshot
        self._refresh_template_combo(name)
        self._save_config()
        self.status.setText(f"已保存模板：{name}")
        return name

    def delete_named_template(self):
        name = self.template_combo.currentText()
        if not name or name == "未选择模板":
            QMessageBox.information(self, APP_NAME, "请先选择要删除的命名模板。")
            return
        if QMessageBox.question(self, APP_NAME, f"删除模板“{name}”？此操作不可恢复。") != QMessageBox.StandardButton.Yes:
            return
        key = self._type_template_key()
        bucket = self._templates_for_type(key)
        self.config_data["layout_templates"][key] = [item for item in bucket if clean(item.get("name", "")) != name]
        active = self.config_data.setdefault("active_template", {})
        if active.get(key) == name:
            active[key] = ""
        self._refresh_template_combo("未选择模板")
        self._save_config()
        self.status.setText(f"已删除模板：{name}")

    def _apply_named_template(self, name: str, record_active: bool = True) -> bool:
        saved = self._find_template(name)
        if not saved:
            return False
        try:
            self._apply_layout_snapshot(saved)
        except Exception:
            return False
        if record_active:
            self.config_data.setdefault("active_template", {})[self._type_template_key()] = name
        return True

    def _apply_layout_snapshot(self, saved: dict):
        layout = saved.get("layout", saved)
        self.element_abs = self._parse_element_abs(layout.get("element_abs_mm", []))
        if "width_mm" in saved:
            self.width_spin.setValue(float(saved["width_mm"]))
        if "height_mm" in saved:
            self.height_spin.setValue(float(saved["height_mm"]))
        scales = saved.get("line_scales") or layout.get("line_scale_percent") or []
        xs = saved.get("line_x") or layout.get("line_offset_x_mm") or []
        ys = saved.get("line_y") or layout.get("line_offset_y_mm") or []
        for index in range(MAX_TEXT_LINES):
            self.line_scales[index] = int(scales[index]) if index < len(scales) else 100
            self.line_x[index] = float(xs[index]) if index < len(xs) else 0.0
            self.line_y[index] = float(ys[index]) if index < len(ys) else 0.0
        self.offset_x_step.setValue(float(layout.get("offset_x_mm", 0)))
        self.offset_y_step.setValue(float(layout.get("offset_y_mm", 0)))
        self.text_spacing_step.setValue(float(layout.get("text_spacing_mm", 0.2)))
        barcode_scale = float(layout.get("barcode_scale_percent", layout.get("barcode_width_percent", 100)))
        self.barcode_scale_step.setValue(max(60, min(125, barcode_scale)))
        self.sync_barcode_scale(self.barcode_scale_step.value())
        self.qr_size_step.setValue(float(layout.get("qr_size_mm", 9.5)))
        self.barcode_x_step.setValue(float(layout.get("barcode_offset_x_mm", 0)))
        self.barcode_y_step.setValue(float(layout.get("barcode_offset_y_mm", 0)))
        self.qr_x_step.setValue(float(layout.get("qr_offset_x_mm", 0)))
        self.qr_y_step.setValue(float(layout.get("qr_offset_y_mm", 0)))
        self.logo_size_step.setValue(float(layout.get("logo_width_mm", 10)))
        self.logo_x_step.setValue(float(layout.get("logo_offset_x_mm", 0)))
        self.logo_y_step.setValue(float(layout.get("logo_offset_y_mm", 0)))
        alignment_index = self.text_alignment_combo.findData(layout.get("text_alignment", "center"))
        self.text_alignment_combo.setCurrentIndex(alignment_index if alignment_index >= 0 else 1)
        if "show_logo" in saved:
            self.logo_check.blockSignals(True)
            self.logo_check.setChecked(bool(saved["show_logo"]))
            self.logo_check.blockSignals(False)
        if "show_barcode" in saved:
            self.barcode_check.blockSignals(True)
            self.barcode_check.setChecked(bool(saved["show_barcode"]))
            self.barcode_check.blockSignals(False)
        if "show_qr" in saved:
            self.qr_check.blockSignals(True)
            self.qr_check.setChecked(bool(saved["show_qr"]))
            self.qr_check.blockSignals(False)
        if "date_mode" in saved and self.date_mode.isEnabled():
            self.date_mode.setCurrentIndex(int(saved["date_mode"]))
        self._sync_code_controls()
        self.sync_preset_to_size()
        self.update_preview()

    def reset_label_layout(self):
        self.offset_x_step.setValue(0)
        self.offset_y_step.setValue(0)
        self.reset_content_layout()
        self._refresh_template_combo("未选择模板")
        self.status.setText("已恢复为当前纸张尺寸的出厂排版")

    def _factory_graphic_defaults(self) -> dict[str, float]:
        height = float(self.height_spin.value())
        if height <= 20:
            return {"qr_size_mm": 7.0, "barcode_scale": 80, "text_spacing_mm": 0.1, "logo_width_mm": 8.0}
        return {"qr_size_mm": 9.5, "barcode_scale": 100, "text_spacing_mm": 0.2, "logo_width_mm": 10.0}

    def reset_content_layout(self):
        """Restore responsive content defaults while preserving printer alignment offsets."""
        defaults = self._factory_graphic_defaults()
        self.element_abs = {}
        self.line_scales = [100] * MAX_TEXT_LINES
        self.line_x = [0.0] * MAX_TEXT_LINES
        self.line_y = [0.0] * MAX_TEXT_LINES
        self.text_scale_step.blockSignals(True)
        self.text_scale_step.setValue(100)
        self.text_scale_step.blockSignals(False)
        self.text_spacing_step.setValue(defaults["text_spacing_mm"])
        self.barcode_scale_step.setValue(defaults["barcode_scale"])
        self.sync_barcode_scale(defaults["barcode_scale"])
        self.qr_size_step.setValue(defaults["qr_size_mm"])
        self.logo_size_step.setValue(defaults["logo_width_mm"])
        self.text_alignment_combo.setCurrentIndex(1)
        for widget in (
            self.text_x_step, self.text_y_step, self.barcode_x_step,
            self.barcode_y_step, self.qr_x_step, self.qr_y_step,
            self.logo_x_step, self.logo_y_step,
        ):
            widget.setValue(0)
        self.update_preview()

    def _text_line_index(self, element: str | None) -> int | None:
        if element in {"text", "text_0"}:
            return 0
        if element and element.startswith("text_"):
            try:
                index = int(element.split("_", 1)[1])
            except ValueError:
                return None
            if 0 <= index < MAX_TEXT_LINES:
                return index
        return None

    def _refresh_preview_elements(self, regions: dict[str, tuple[int, int, int, int]], columns: list[tuple[str, str]]):
        current = self.preview_element_combo.currentData()
        self.preview_element_combo.blockSignals(True)
        self.preview_element_combo.clear()
        for index, (header, _value) in enumerate(columns):
            key = f"text_{index}"
            if key not in regions:
                continue
            title = "L / R" if header in {"左右手", "手性", "L/R"} else (header or f"文字{index + 1}")
            self.preview_element_combo.addItem(title, key)
        if "barcode" in regions:
            self.preview_element_combo.addItem("条形码", "barcode")
        if "qr" in regions:
            self.preview_element_combo.addItem("二维码", "qr")
        if "logo" in regions:
            self.preview_element_combo.addItem("Logo", "logo")
        target = current if self.preview_element_combo.findData(current) >= 0 else (
            current if current in regions else next(iter(regions), "text_0")
        )
        index = self.preview_element_combo.findData(target)
        self.preview_element_combo.setCurrentIndex(index if index >= 0 else 0)
        self.preview_element_combo.blockSignals(False)
        selected = self.preview_element_combo.currentData()
        if selected:
            self.preview.set_selected_element(selected)
        signature = tuple((header, f"text_{index}") for index, (header, _value) in enumerate(columns) if f"text_{index}" in regions)
        if signature != self._text_control_signature:
            self._text_control_signature = signature
            self._rebuild_text_item_controls(columns)
        else:
            self._sync_item_scale_steppers()
        self._sync_text_scale_stepper()

    def _field_title(self, header: str) -> str:
        if header in {"左右手", "手性", "L/R", "LR"}:
            return "L / R"
        return header or "文字"

    def _clear_box(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            child = item.layout()
            if child:
                self._clear_box(child)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _rebuild_text_item_controls(self, columns: list[tuple[str, str]]):
        self._clear_box(self.text_items_box)
        self.line_scale_steppers = []
        visible = [(index, header) for index, (header, _value) in enumerate(columns) if index < MAX_TEXT_LINES]
        if not visible:
            hint = QLabel("选择标签内容后，这里会单独列出每一项文字的大小，例如编号和 L/R。")
            hint.setObjectName("Hint")
            hint.setWordWrap(True)
            self.text_items_box.addWidget(hint)
            return
        for index, header in visible:
            row = QHBoxLayout()
            title = QLabel(f"{self._field_title(header)}大小")
            title.setMinimumWidth(92)
            stepper = NumberStepper(50, 220, 5, self.line_scales[index], 0, " %")
            stepper.setToolTip(f"只改变「{self._field_title(header)}」，不影响其他文字")
            stepper.valueChanged.connect(lambda value, item=index: self._on_item_scale(item, value))
            row.addWidget(title)
            row.addWidget(stepper, 1)
            self.text_items_box.addLayout(row)
            self.line_scale_steppers.append(stepper)

    def _sync_item_scale_steppers(self):
        for index, stepper in enumerate(self.line_scale_steppers):
            if int(stepper.value()) != int(self.line_scales[index]):
                stepper.blockSignals(True)
                stepper.setValue(self.line_scales[index])
                stepper.blockSignals(False)

    def _on_item_scale(self, index: int, value: float):
        self._freeze_elements_from_preview()
        self.line_scales[index] = int(value)
        if index == 0:
            self.text_scale_step.blockSignals(True)
            self.text_scale_step.setValue(value)
            self.text_scale_step.blockSignals(False)
        self.update_preview()

    def _sync_text_scale_stepper(self):
        index = self._text_line_index(self.preview_element_combo.currentData())
        if index is None:
            return
        self.text_scale_step.blockSignals(True)
        self.text_scale_step.setValue(self.line_scales[index])
        self.text_scale_step.blockSignals(False)

    def on_text_scale_changed(self, value: float):
        self._freeze_elements_from_preview()
        index = self._text_line_index(self.preview.selected_element)
        if index is None:
            index = self._text_line_index(self.preview_element_combo.currentData())
        if index is None:
            index = 0
        self.line_scales[index] = int(value)
        self._sync_item_scale_steppers()
        self.update_preview()

    def preview_element_changed(self, index: int):
        element = self.preview_element_combo.itemData(index)
        if element:
            self.preview.set_selected_element(element)
            self._sync_text_scale_stepper()

    def select_preview_element(self, element: str):
        index = self.preview_element_combo.findData(element)
        if index >= 0 and index != self.preview_element_combo.currentIndex():
            self.preview_element_combo.blockSignals(True)
            self.preview_element_combo.setCurrentIndex(index)
            self.preview_element_combo.blockSignals(False)
        self._sync_text_scale_stepper()

    def _element_position_steps(self, element: str) -> tuple[NumberStepper, NumberStepper] | None:
        element = "text_0" if element == "text" else element
        return {
            "barcode": (self.barcode_x_step, self.barcode_y_step),
            "qr": (self.qr_x_step, self.qr_y_step),
            "logo": (self.logo_x_step, self.logo_y_step),
        }.get(element)

    def _freeze_elements_from_preview(self):
        if not self.preview.source_regions:
            return
        dpm = self.label_settings().dots_per_mm
        frozen: dict[str, tuple[float, float]] = {}
        for name, (x1, y1, _x2, _y2) in self.preview.source_regions.items():
            if name == "text":
                continue
            frozen[name] = (round(x1 / dpm, 2), round(y1 / dpm, 2))
        if frozen:
            self.element_abs = frozen

    def move_preview_element(self, element: str, dx_ratio: float, dy_ratio: float):
        settings = self.label_settings()
        element = "text_0" if element == "text" else element
        self._freeze_elements_from_preview()
        dx_mm = dx_ratio * settings.width_mm
        dy_mm = dy_ratio * settings.height_mm
        region = self.preview.source_regions.get(element)
        if region and self.preview.source_pixmap:
            dpm = settings.dots_per_mm
            margin = max(round(settings.safe_margin_mm * dpm), 6)
            x1, y1, x2, y2 = region
            dx_mm = max((margin - x1) / dpm, min((self.preview.source_pixmap.width() - margin - x2) / dpm, dx_mm))
            dy_mm = max((margin - y1) / dpm, min((self.preview.source_pixmap.height() - margin - y2) / dpm, dy_mm))
        if element in self.element_abs:
            x_mm, y_mm = self.element_abs[element]
            self.element_abs[element] = (round(x_mm + dx_mm, 2), round(y_mm + dy_mm, 2))
            self.update_preview()
            return
        line_index = self._text_line_index(element)
        if line_index is not None:
            self.line_x[line_index] = round(self.line_x[line_index] + dx_mm, 1)
            self.line_y[line_index] = round(self.line_y[line_index] + dy_mm, 1)
            if line_index == 0:
                self.text_x_step.blockSignals(True)
                self.text_y_step.blockSignals(True)
                self.text_x_step.setValue(self.line_x[0])
                self.text_y_step.setValue(self.line_y[0])
                self.text_x_step.blockSignals(False)
                self.text_y_step.blockSignals(False)
            self.update_preview()
            return
        steps = self._element_position_steps(element)
        if not steps:
            return
        x_step, y_step = steps
        x_step.setValue(round(x_step.value() + dx_mm, 1))
        y_step.setValue(round(y_step.value() + dy_mm, 1))

    def resize_preview_element(self, element: str, dx_ratio: float, dy_ratio: float):
        settings = self.label_settings()
        element = "text_0" if element == "text" else element
        self._freeze_elements_from_preview()
        line_index = self._text_line_index(element)
        if line_index is not None:
            delta = (dx_ratio + dy_ratio) * 60
            next_scale = max(50, min(220, self.line_scales[line_index] + delta))
            self.line_scales[line_index] = int(next_scale)
            self.text_scale_step.setValue(next_scale)
            return
        if element == "barcode":
            dominant_delta = dx_ratio if abs(dx_ratio) >= abs(dy_ratio) else dy_ratio
            next_scale = self.barcode_scale_step.value() * max(0.7, min(1.3, 1.0 + dominant_delta * 2.0))
            self.barcode_scale_step.setValue(max(60, min(125, next_scale)))
        elif element == "qr":
            delta_mm = max(dx_ratio * settings.width_mm, dy_ratio * settings.height_mm)
            self.qr_size_step.setValue(max(QR_SIZE_MIN_MM, min(QR_SIZE_MAX_MM, self.qr_size_step.value() + delta_mm)))
        elif element == "logo":
            delta_mm = max(dx_ratio * settings.width_mm, dy_ratio * settings.height_mm)
            self.logo_size_step.setValue(max(LOGO_WIDTH_MIN_MM, min(LOGO_WIDTH_MAX_MM, self.logo_size_step.value() + delta_mm)))

    def sync_barcode_scale(self, value: float):
        """Use one user-facing scale to keep barcode width and height proportional."""
        scale = max(60, min(125, float(value)))
        self.barcode_width_step.setValue(scale)
        self.barcode_height_step.setValue(6.8 * scale / 100.0)
        self.update_preview()

    def apply_preset(self, text: str):
        values = {"30 × 20 mm": (30, 20), "40 × 30 mm": (40, 30), "50 × 30 mm": (50, 30), "60 × 40 mm": (60, 40), "15 × 8 mm": (15, 8), "10 × 20 mm": (10, 20)}
        if text in values:
            width, height = values[text]
            changed = (float(self.width_spin.value()), float(self.height_spin.value())) != (float(width), float(height))
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            if changed:
                self.reset_content_layout()
                self.status.setText(f"已切换到 {text}，内容已按新尺寸重新适配；整体校准偏移已保留。")
        self.update_preview()

    def sync_preset_to_size(self):
        width = round(float(self.width_spin.value()), 1)
        height = round(float(self.height_spin.value()), 1)
        values = {
            (30.0, 20.0): "30 × 20 mm", (40.0, 30.0): "40 × 30 mm",
            (50.0, 30.0): "50 × 30 mm", (60.0, 40.0): "60 × 40 mm",
            (15.0, 8.0): "15 × 8 mm", (10.0, 20.0): "10 × 20 mm",
        }
        target = values.get((width, height), "自定义")
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText(target)
        self.preset_combo.blockSignals(False)

    def select_all_rows(self):
        self.table.selectAll()

    def clear_selection(self):
        self.table.clearSelection()

    def refresh_printers(self):
        printers = list_printers()
        current = self.config_data.get("printer", self.printer_combo.currentText() if hasattr(self, "printer_combo") else "")
        self.printer_combo.clear()
        self.printer_combo.addItems(printers)
        zebra = zebra_printers(printers)
        niimbot = [p for p in printers if "b1 pro" in p.lower() or "b1pro" in p.lower()]
        exact = [name for name in zebra if "zd888" in name.lower() and "300" in name.lower()]
        supported_current = current if current in printers and (current in zebra or current in niimbot) else ""
        target = supported_current or (exact[0] if exact else zebra[0] if zebra else niimbot[0] if niimbot else "")
        if target:
            self.printer_combo.setCurrentText(target)
        if zebra:
            self.driver_chip.setText("斑马打印机已就绪")
            self.driver_chip.setObjectName("StatusChip")
            if exact:
                self.driver_status.setText(f"已匹配 ZD888TA 300 dpi：{'、'.join(exact)}。建议先打印 1 张并扫码确认。")
            else:
                self.driver_status.setText(f"检测到打印队列：{'、'.join(zebra)}。请确认驱动名称含 ZD888 和 300dpi。")
        else:
            self.driver_chip.setText("未检测到斑马打印机")
            self.driver_chip.setObjectName("WarningChip")
            self.driver_status.setText("未找到 ZD888TA 300 dpi 打印队列。点击下方按钮安装官方驱动，选择 ZD888 300dpi ZPL。")
        self.driver_chip.style().unpolish(self.driver_chip)
        self.driver_chip.style().polish(self.driver_chip)
        self.on_printer_changed(self.printer_combo.currentText())

    def on_printer_changed(self, name):
        compact = "niimbot" in name.lower() or "精臣" in name
        for index, combo in enumerate(self.column_combos):
            combo.setVisible(not compact or index == 0)
        self.niimbot_symbol.setVisible(compact)
        for control in (
            self.offset_x_step, self.offset_y_step, self.text_scale_step, self.text_spacing_step,
            self.text_alignment_combo, self.qr_size_step, self.barcode_scale_step,
            self.logo_check, self.barcode_check, self.qr_check, self.logo_size_step,
            self.preview_element_combo,
        ):
            control.setEnabled(not compact)
        self._sync_date_controls_visibility()
        if not compact:
            self._sync_code_controls()
        self.preview.setEnabled(not compact)
        if "niimbot" in name.lower() or "精臣" in name:
            self.print_method_combo.setCurrentIndex(1)
            self.print_method_combo.setEnabled(False)
            self.driver_chip.setText("精臣打印队列已检测到")
            if hasattr(self, "driver_status"):
                self.driver_status.setText("使用 Windows 驱动打印；B1 Pro 为热敏打印机。请通过 USB 连接并开机。")
        else:
            self.print_method_combo.setEnabled(True)
            if self._is_zebra_printer(name):
                self.driver_chip.setText("斑马打印机已选中")
                self.driver_chip.setObjectName("StatusChip")
            elif name:
                self.driver_chip.setText("当前不是标签打印机")
                self.driver_chip.setObjectName("WarningChip")
        self.calibrate_button.setEnabled(self._is_zebra_printer(name))
        self.driver_chip.style().unpolish(self.driver_chip)
        self.driver_chip.style().polish(self.driver_chip)
        self.update_preview()

    def _is_zebra_printer(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ("zebra", "zdesigner", "zd888", "gk888", "zt"))

    def repair_print_queue(self):
        printer = self.printer_combo.currentText()
        if not printer:
            QMessageBox.warning(self, APP_NAME, "当前没有选择打印机。")
            return
        try:
            jobs = print_queue_jobs(printer)
        except Exception as exc:
            self.handle_error(f"读取打印队列失败：{exc}")
            return
        if not jobs:
            QMessageBox.information(self, APP_NAME, "当前打印队列正常，没有等待任务。")
            return
        names = "、".join(clean(job.get("pDocument")) or f"任务 {job.get('JobId')}" for job in jobs[:4])
        if QMessageBox.question(
            self, APP_NAME,
            f"检测到 {len(jobs)} 个等待或卡住的任务：{names}\n\n是否取消这些任务并修复队列？",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            cancelled = cancel_print_jobs(printer)
            remaining = print_queue_jobs(printer)
            if remaining:
                self._restart_spooler_elevated()
                QMessageBox.information(
                    self, APP_NAME,
                    "任务已请求取消。系统将弹出管理员确认并重启打印服务；完成后请等待几秒再打印。",
                )
            else:
                QMessageBox.information(self, APP_NAME, f"已清理 {cancelled} 个任务，打印队列恢复正常。")
        except Exception as exc:
            self.handle_error(f"修复打印队列失败：{exc}")

    def _restart_spooler_elevated(self):
        import ctypes
        command = "Restart-Service -Name Spooler -Force"
        params = f'-NoProfile -ExecutionPolicy Bypass -Command "{command}"'
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", params, None, 0)
        if result <= 32:
            raise RuntimeError("未能启动打印服务修复，请允许管理员确认后重试。")

    def calibrate_zebra(self):
        printer = self.printer_combo.currentText()
        if not self._is_zebra_printer(printer):
            QMessageBox.warning(self, APP_NAME, "请先选择斑马 ZD888 打印机。")
            return
        try:
            queued_jobs = print_queue_jobs(printer)
        except Exception as exc:
            self.handle_error(f"读取打印队列失败：{exc}")
            return
        if queued_jobs:
            QMessageBox.warning(self, APP_NAME, "打印队列中仍有任务，请先点击“检查 / 修复队列”。")
            return
        sensing = self.media_sensing_combo.currentData() or "gap"
        sensing_text = self.media_sensing_combo.currentText()
        method = "thermal_transfer" if self.print_method_combo.currentIndex() == 0 else "direct_thermal"
        if QMessageBox.question(
            self, APP_NAME,
            f"将按“{sensing_text}”校准斑马打印机。\n\n"
            "请确认标签纸和碳带已装好、上盖已扣紧。校准时可能自动走出几张空白标签。\n\n是否开始？",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            send_raw(printer, [zebra_calibration_zpl(method, sensing)], "Crelabel - 校准纸张")
            self.status.setText(f"已向 {printer} 发送纸张校准指令")
            QMessageBox.information(self, APP_NAME, "校准指令已发送。请等待打印机停止走纸并恢复绿灯常亮。")
        except Exception as exc:
            self.handle_error(f"发送校准指令失败：{exc}")

    def is_niimbot(self):
        name = self.printer_combo.currentText().lower() if hasattr(self, "printer_combo") else ""
        return "niimbot" in name or "精臣" in name

    def install_niimbot_driver(self):
        roots = [Path(sys.executable).resolve().parent, Path(__file__).resolve().parent]
        for root in roots:
            installer = root / "drivers" / "NiimbotPrinterDriverInstaller-3.0.2.1.exe"
            if installer.exists():
                import ctypes
                result = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installer), None, str(installer.parent), 1)
                if result <= 32:
                    self.handle_error("精臣驱动安装程序未启动或管理员授权已取消。")
                return
        webbrowser.open("https://www.niimbot.com/us/downloadCenter")

    def _local_driver_installer(self) -> Path | None:
        roots = [Path(sys.executable).resolve().parent, Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))]
        for root in roots:
            driver_dir = root / "drivers"
            candidates = list(driver_dir.glob("Zebra*.exe")) if driver_dir.exists() else []
            if candidates:
                return candidates[0]
        return None

    def install_driver(self):
        text = (
            "Crelabel 将打开斑马官方打印机安装程序。\n\n"
            "安装前请先关闭打印机电源；向导提示后再连接 USB 并开机。"
            "向导中请选择 ZD888 / ZD888TA、300 dpi、ZPL。驱动许可协议由斑马提供并需要使用者确认。"
        )
        if QMessageBox.information(self, "安装斑马驱动", text, QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Ok:
            return
        local = self._local_driver_installer()
        if local:
            try:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "runas", str(local), None, str(local.parent), 1)
                return
            except Exception as exc:
                self.handle_error(str(exc))
                return
        webbrowser.open(ZEBRA_SETUP_URL)

    def build_jobs(self, records: list[LabelRecord]) -> tuple[list[bytes], int]:
        self.validate_print_records(records)
        jobs: list[bytes] = []
        copies = int(self.copies_spin.value())
        method = "thermal_transfer" if self.print_method_combo.currentIndex() == 0 else "direct_thermal"
        sensing = self.media_sensing_combo.currentData() or "gap"
        for record in records:
            image = render_label(record, self.selected_columns(record), self.label_settings(), self.printed_date(), self.label_layout(), self.barcode_value(record))
            jobs.extend([image_to_zpl(image, method, sensing)] * copies)
        return jobs, len(jobs)

    def export_zpl(self):
        records = self.selected_records(False)
        if not records:
            QMessageBox.information(self, APP_NAME, "请先选择要导出的记录。")
            return
        try:
            self.validate_print_records(records)
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        path, _filter = QFileDialog.getSaveFileName(self, "导出 ZPL", "Crelabel-labels.zpl", "ZPL (*.zpl)")
        if not path:
            return
        jobs, count = self.build_jobs(records)
        Path(path).write_bytes(b"".join(jobs))
        self.status.setText(f"已导出 {count} 张标签：{path}")

    def print_rows(self, all_rows: bool):
        records = self.selected_records(all_rows)
        try:
            self.validate_print_records(records)
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        printer = self.printer_combo.currentText()
        if not records:
            QMessageBox.information(self, APP_NAME, "没有可打印记录。")
            return
        if not printer:
            QMessageBox.warning(self, APP_NAME, "未检测到打印机。请先安装/配置斑马驱动，然后点击刷新。")
            return
        count = len(records) * int(self.copies_spin.value())
        method_text = self.print_method_combo.currentText()
        if self._is_zebra_printer(printer):
            try:
                blocked = problematic_print_jobs(printer)
            except Exception as exc:
                QMessageBox.warning(self, APP_NAME, f"无法检查打印队列，暂未发送标签：\n{exc}")
                return
            if blocked:
                QMessageBox.warning(
                    self, APP_NAME,
                    f"检测到 {len(blocked)} 个异常打印任务，暂未发送新标签。\n请先点击“检查 / 修复队列”。",
                )
                return
        if QMessageBox.question(self, APP_NAME, f"确认向 {printer} 发送 {count} 张标签？\n打印方式：{method_text}\n建议首次只打印 1 张进行扫码检查。") != QMessageBox.StandardButton.Yes:
            return
        try:
            if "niimbot" in printer.lower() or "精臣" in printer:
                from windows_print import print_images
                images = [render_label(r, self.selected_columns(r), self.label_settings(), self.printed_date(), self.label_layout(), self.barcode_value(r)) for r in records]
                print_images(printer, images, self.width_spin.value(), self.height_spin.value(), int(self.copies_spin.value()))
            else:
                jobs, count = self.build_jobs(records)
                send_raw(printer, jobs)
            self.status.setText(f"已向 {printer} 发送 {count} 张标签")
            QMessageBox.information(self, APP_NAME, "打印任务已发送。请检查首张标签的边距和扫码结果。")
        except Exception as exc:
            self.handle_error(str(exc))

    def start_auth(self):
        self.status.setText("正在准备飞书登录环境…")
        self.run_worker(
            configure_and_begin_auth,
            on_finished=self.auth_started,
            on_progress=self.handle_auth_progress,
            with_progress=True,
        )

    def handle_auth_progress(self, message: str):
        if message.startswith(CONFIG_URL_PROGRESS):
            url = message[len(CONFIG_URL_PROGRESS):]
            if self.setup_dialog:
                self.setup_dialog.accept()
            self.setup_dialog = SetupDialog(url, self)
            self.setup_dialog.show()
            self.status.setText("请扫码完成首次飞书应用配置")
            return
        self.status.setText(message)

    def auth_started(self, payload: dict):
        if self.setup_dialog:
            self.setup_dialog.accept()
            self.setup_dialog = None
        self.auth_dialog = AuthDialog(payload, self)
        self.auth_dialog.complete_requested.connect(self.complete_auth)
        self.auth_dialog.show()
        self.status.setText("请使用飞书扫码授权")

    def complete_auth(self, device_code: str):
        if not device_code:
            self.handle_error("授权请求缺少 device_code，请重新发起授权。")
            return
        self.status.setText("正在确认飞书授权…")
        if self.auth_dialog:
            self.auth_dialog.set_waiting(True)
        self.run_worker(complete_user_auth, device_code, on_finished=self.auth_completed, on_error=self.auth_failed)

    def auth_failed(self, message: str):
        if self.auth_dialog:
            self.auth_dialog.set_waiting(False)
        if "二维码已失效" in message:
            if self.auth_dialog:
                self.auth_dialog.accept()
            self.status.setText("授权二维码已失效，正在重新生成…")
            QMessageBox.information(self, APP_NAME, "授权二维码已失效，将为你重新生成一个新二维码。")
            self.start_auth()
            return
        self.handle_error(message)

    def auth_completed(self, _payload: dict):
        if self.auth_dialog:
            self.auth_dialog.accept()
        self.status.setText("飞书授权完成，可以连接多维表格")
        QMessageBox.information(self, APP_NAME, "飞书授权及读取权限检查均已完成。")

    def check_environment(self):
        self.status.setText("正在检查飞书环境…")
        self.run_worker(environment_status, on_finished=self.environment_checked)

    def environment_checked(self, payload: dict):
        config_source = "Crelabel 独立配置"
        if not payload.get("configured"):
            self.status.setText("内置飞书环境正常，等待首次扫码配置")
            QMessageBox.information(
                self,
                APP_NAME,
                "飞书运行环境正常。\n应用状态：尚未配置\n\n点击“飞书扫码授权”，按软件提示完成配置和登录即可。",
            )
            return
        auth = payload.get("auth", {})
        user_identity = (auth.get("identities") or {}).get("user", {})
        identity = auth.get("identity", {}) if isinstance(auth.get("identity"), dict) else auth
        name = user_identity.get("userName") or identity.get("userName") or auth.get("userName") or "未登录"
        if payload.get("authorized") and payload.get("scope_ready"):
            self.status.setText(f"飞书环境正常：{name}")
            message = f"飞书连接环境正常。\n配置来源：{config_source}\n当前用户：{name}\nBase / Wiki 读取权限：正常"
        elif payload.get("authorized"):
            missing = "、".join(payload.get("missing_scopes") or [])
            self.status.setText("飞书账号已登录，需要重新扫码补充权限")
            message = (
                f"当前用户：{name}\n检测到授权范围不完整。\n缺少：{missing}\n\n"
                "请点击“飞书扫码授权”，软件会自动申请所需权限。"
            )
        else:
            self.status.setText("飞书环境已配置，等待用户扫码授权")
            message = f"飞书运行环境和应用配置正常。\n配置来源：{config_source}\n用户状态：尚未登录或授权已失效\n\n点击“飞书扫码授权”即可继续。"
        QMessageBox.information(self, APP_NAME, message)

    def closeEvent(self, event):
        try:
            self._save_config()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    if "--self-test" in sys.argv:
        from openpyxl import Workbook
        test_record = LabelRecord(source_row=2, code="TEST-100", name="Crelabel 自检", link="https://example.com/test")
        test_record.raw_fields = {"零件": test_record.name, "料号": test_record.code}
        test_image, test_regions = render_label_with_regions(
            test_record, [("零件", test_record.name), ("料号", test_record.code)],
            LabelSettings(), layout=LabelLayout(text_offset_x_mm=0.5, qr_offset_y_mm=-0.5),
        )
        assert test_image.size == LabelSettings().pixel_size
        assert {"text", "barcode", "qr"}.issubset(test_regions)
        assert Workbook().active is not None
        return
    app = QApplication(sys.argv)
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 10))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(create_app_icon())
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = CrelabelWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
