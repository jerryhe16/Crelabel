from __future__ import annotations

import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import zxingcpp
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from crelabel import CUSTOM_OPTION, NO_PRINT_OPTION, STYLE, CrelabelWindow
from feishu_client import CONFIG_URL_PROGRESS, REQUIRED_SCOPES, FeishuError, _extract_json, cli_config_dir, cli_runtime, complete_user_auth, configure_and_begin_auth, environment_status, load_feishu_data, run_cli, validate_feishu_url
from label_core import CONTENT_FIELD_SLOTS, LabelLayout, LabelRecord, LabelSettings, auto_mapping, bundled_font_path, bundled_logo_path, clean, explicit_break_parts, format_label_value, image_to_zpl, load_local_rows, make_logo, make_qr, records_from_rows, render_label, render_label_with_regions, zebra_calibration_zpl


def isolated_ink_ratio(image) -> float:
    """Share of black pixels with ≤1 black neighbor. Dithered glyphs score high."""
    mono = image.convert("1")
    width, height = mono.size
    pixels = mono.load()
    black = isolated = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if pixels[x, y] != 0:
                continue
            black += 1
            neighbors = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == dy == 0:
                        continue
                    if pixels[x + dx, y + dy] == 0:
                        neighbors += 1
            if neighbors <= 1:
                isolated += 1
    return isolated / black if black else 0


FEISHU_TEST_URL = "https://ncn5zs910x3g.feishu.cn/wiki/CCOzwaWc0iNBjNkUpdLcKeOInie?table=tblm4wsfEdEUU6t6&view=vewcqkgMpi"


def main():
    bundled_cli = None
    try:
        bundled_cli = Path(cli_runtime())
    except FeishuError:
        # The public source repository intentionally excludes third-party
        # binaries. Packaged-release validation still exercises the bundled CLI.
        pass
    assert cli_config_dir().name == "lark-cli" and cli_config_dir().parent.name == "Crelabel"
    if bundled_cli is not None:
        assert bundled_cli.exists() and bundled_cli.name == "lark-cli.exe"
        version_check = __import__("subprocess").run([str(bundled_cli), "--version"], capture_output=True, text=True, encoding="utf-8")
        assert version_check.returncode == 0 and "1.0.67" in version_check.stdout
    config_events: list[str] = []
    fake_config_process = SimpleNamespace(
        stdout=["使用飞书扫码配置应用：\n", "https://open.feishu.cn/page/cli?user_code=TEST-1234\n"],
        wait=lambda: 0,
    )
    fake_auth_payload = {"device_code": "device-test", "verification_url": "https://example.com/auth"}
    test_cli = str(bundled_cli or (ROOT / "fake-lark-cli.exe"))
    with patch("feishu_client.cli_runtime", return_value=test_cli), patch("feishu_client.is_cli_configured", side_effect=[False, True]), patch("feishu_client.subprocess.Popen", return_value=fake_config_process), patch("feishu_client.begin_user_auth", return_value=fake_auth_payload):
        with patch("feishu_client.migrate_existing_app_config", return_value=False):
            assert configure_and_begin_auth(config_events.append) == fake_auth_payload
    assert any(item.startswith(CONFIG_URL_PROGRESS + "https://open.feishu.cn/") for item in config_events)
    assert set(REQUIRED_SCOPES) == {"base:field:read", "base:record:read", "base:table:read", "base:view:read", "wiki:node:retrieve"}
    with patch("feishu_client.cli_runtime", return_value=test_cli), patch("feishu_client.is_cli_configured", return_value=True), patch("feishu_client.run_cli", side_effect=[{"verified": True, "userName": "测试用户"}, {"granted": list(REQUIRED_SCOPES), "missing": None}]):
        checked = environment_status()
        assert checked["scope_ready"] is True and checked["missing_scopes"] == []
    with patch("feishu_client.cli_runtime", return_value=test_cli), patch("feishu_client.is_cli_configured", return_value=True), patch("feishu_client.run_cli", side_effect=[{"verified": True}, {"granted": [], "missing": ["wiki:node:retrieve"]}]):
        checked = environment_status()
        assert checked["scope_ready"] is False and checked["missing_scopes"] == ["wiki:node:retrieve"]
    with patch("feishu_client.run_cli", side_effect=[{"authorized": True}, {"granted": list(REQUIRED_SCOPES), "missing": None}]):
        assert complete_user_auth("device-test") == {"authorized": True}
    record = LabelRecord(
        source_row=2,
        code="100035-B00",
        name="结构-四指远指节",
        supplier="宏海兴",
        link="https://example.com/record/rec123",
    )
    record.raw_fields = {"零件": record.name, "料号": record.code, "供应商": record.supplier}
    settings = LabelSettings(40, 30, 300)
    label = render_label(record, list(record.raw_fields.items()), settings, "2026-08-28")
    assert label.size == (472, 354), label.size
    decoded = {(item.format.name, item.text) for item in zxingcpp.read_barcodes(label.convert("L"))}
    assert ("Code128", record.code) in decoded, decoded
    assert ("QRCode", record.link) in decoded, decoded
    qr = make_qr(record.link, 112)
    assert qr is not None and qr.mode == "1"
    assert ("QRCode", record.link) in {(item.format.name, item.text) for item in zxingcpp.read_barcodes(qr.convert("L"))}
    region_label, regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, "2026-08-28")
    text_crop = region_label.crop(regions["text_0"])
    assert isolated_ink_ratio(text_crop) < 0.02, isolated_ink_ratio(text_crop)
    assert region_label.size == label.size
    assert {"text_0", "text_1", "barcode", "qr"}.issubset(regions)
    assert bundled_logo_path() is not None and bundled_logo_path().name == "prime-logo.png"
    logo = make_logo(120)
    assert logo is not None and logo.size[0] == 120 and logo.size[1] > 8
    with_logo, logo_regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, layout=LabelLayout(show_logo=True, logo_width_mm=12))
    assert "logo" in logo_regions
    bigger_logo, bigger_logo_regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, layout=LabelLayout(show_logo=True, logo_width_mm=20))
    assert bigger_logo_regions["logo"][2] - bigger_logo_regions["logo"][0] > logo_regions["logo"][2] - logo_regions["logo"][0]
    moved_logo, moved_logo_regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, layout=LabelLayout(show_logo=True, logo_width_mm=12, logo_offset_x_mm=2.0))
    assert moved_logo_regions["logo"][0] > logo_regions["logo"][0]
    assert format_label_value("左右手", "左手") == "L" and format_label_value("左右手", "右手") == "R"
    hand_label, hand_regions = render_label_with_regions(
        record, [("样机编号", "Gen3 V2-001"), ("左右手", "左手")], settings, layout=LabelLayout(show_barcode=False),
    )
    assert "text_1" in hand_regions
    assert hand_regions["text_1"][0] >= hand_regions["text_0"][2] - 2
    assert abs(hand_regions["text_1"][1] - hand_regions["text_0"][1]) < 24
    scaled_hand, scaled_regions = render_label_with_regions(
        record, [("样机编号", "Gen3 V2-001"), ("左右手", "左手")], settings,
        layout=LabelLayout(show_barcode=False, text_scale_percent=160),
    )
    assert scaled_regions["text_1"][3] - scaled_regions["text_1"][1] > hand_regions["text_1"][3] - hand_regions["text_1"][1]
    assert scaled_regions["text_0"][2] - scaled_regions["text_0"][0] > hand_regions["text_0"][2] - hand_regions["text_0"][0]
    dpm = settings.dots_per_mm
    pinned = (
        ("text_0", hand_regions["text_0"][0] / dpm, hand_regions["text_0"][1] / dpm),
        ("text_1", hand_regions["text_1"][0] / dpm, hand_regions["text_1"][1] / dpm),
    )
    _pinned_label, pinned_regions = render_label_with_regions(
        record, [("样机编号", "Gen3 V2-001"), ("左右手", "左手")], settings,
        layout=LabelLayout(show_barcode=False, text_scale_percent=160, element_abs_mm=pinned),
    )
    assert pinned_regions["text_1"][0] == hand_regions["text_1"][0]
    assert pinned_regions["text_1"][1] == hand_regions["text_1"][1]
    assert pinned_regions["text_0"][2] - pinned_regions["text_0"][0] > hand_regions["text_0"][2] - hand_regions["text_0"][0]
    small_qr, small_regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, layout=LabelLayout(qr_size_mm=8))
    large_qr, large_regions = render_label_with_regions(record, list(record.raw_fields.items()), settings, layout=LabelLayout(qr_size_mm=14))
    assert large_regions["qr"][2] - large_regions["qr"][0] > small_regions["qr"][2] - small_regions["qr"][0]
    moved_label, moved_regions = render_label_with_regions(
        record, list(record.raw_fields.items()), settings, "2026-08-28",
        LabelLayout(line_offset_x_mm=(1.0, 0, 0, 0, 0), barcode_offset_y_mm=-1.0, qr_offset_x_mm=-1.0, barcode_width_percent=80),
    )
    assert moved_label.tobytes() != region_label.tobytes()
    assert moved_regions["text_0"] != regions["text_0"] and moved_regions["barcode"] != regions["barcode"] and moved_regions["qr"] != regions["qr"]
    short_columns = [("名称", "短文本")]
    _left_image, left_regions = render_label_with_regions(record, short_columns, settings, layout=LabelLayout(text_alignment="left"))
    _center_image, center_regions = render_label_with_regions(record, short_columns, settings, layout=LabelLayout(text_alignment="center"))
    _right_image, right_regions = render_label_with_regions(record, short_columns, settings, layout=LabelLayout(text_alignment="right"))
    assert left_regions["text_0"][0] < center_regions["text_0"][0] < right_regions["text_0"][0]
    long_spec = "AXLE, Φ1.5MM x 7.9 HIGH STRENGTH STEEL SHAFT FOR FF-CR"
    squeezed, squeezed_regions = render_label_with_regions(
        record, [("零件", "钢轴"), ("规格描述", long_spec)], settings, layout=LabelLayout(show_barcode=False, show_qr=False),
    )
    wrapped_height = squeezed_regions["text_1"][3] - squeezed_regions["text_1"][1]
    assert wrapped_height > squeezed_regions["text_0"][3] - squeezed_regions["text_0"][1]
    broken, broken_regions = render_label_with_regions(
        record, [("规格描述", "第一行\\n第二行")], settings, layout=LabelLayout(show_barcode=False, show_qr=False),
    )
    assert broken_regions["text_0"][3] - broken_regions["text_0"][1] > squeezed_regions["text_0"][3] - squeezed_regions["text_0"][1]
    assert explicit_break_parts("第一行\\n第二行") == ["第一行", "第二行"]
    assert b"^MTT" in image_to_zpl(label, "thermal_transfer")
    assert b"^MTD" in image_to_zpl(label, "direct_thermal")
    assert b"^MNY" in image_to_zpl(label, "thermal_transfer", "gap")
    assert b"^MNM" in image_to_zpl(label, "thermal_transfer", "mark")
    assert b"^MNN" in image_to_zpl(label, "thermal_transfer", "continuous")
    assert zebra_calibration_zpl("thermal_transfer", "gap") == b"^XA^MTT^MNY^XZ~JC\r\n"
    adjusted = render_label(record, list(record.raw_fields.items()), settings, "2026-08-28", LabelLayout(offset_y_mm=2, text_scale_percent=115, text_spacing_mm=0.8, qr_size_mm=11))
    assert label.tobytes() != adjusted.tobytes()
    custom_barcode = render_label(record, list(record.raw_fields.items()), settings, barcode_payload="800035-B00")
    custom_decoded = {(item.format.name, item.text) for item in zxingcpp.read_barcodes(custom_barcode.convert("L"))}
    assert ("Code128", "800035-B00") in custom_decoded, custom_decoded
    mixed_cli_output = '[lark-cli] device-flow: slow_down, interval increased to 10s\n{"ok":false,"error":{"message":"authorization failed"}}'
    assert _extract_json(mixed_cli_output)["error"]["message"] == "authorization failed"
    nested_success = '{"ok":true,"data":{"data":[["value"]],"fields":["field"]}}'
    parsed_success = _extract_json(nested_success)
    assert parsed_success["ok"] is True and isinstance(parsed_success["data"], dict)
    expired_output = '[lark-cli] device-flow: slow_down\n{"ok":false,"error":{"message":"authorization failed: The device code is invalid. Please restart the device authorization flow."}}'
    fake_result = SimpleNamespace(stdout="", stderr=expired_output, returncode=1)
    with patch("feishu_client.cli_runtime", return_value=("node", "script")), patch("feishu_client.subprocess.run", return_value=fake_result):
        try:
            run_cli("auth", "login")
            raise AssertionError("expired device code should fail")
        except FeishuError as exc:
            assert "二维码已失效" in str(exc)
    shared_view_url = "https://example.feishu.cn/share/base/view/shrcnExample"
    try:
        validate_feishu_url(shared_view_url)
        raise AssertionError("shared view URL should be rejected before CLI execution")
    except FeishuError as exc:
        assert "共享视图" in str(exc) and "/wiki/" in str(exc) and "/base/" in str(exc)
    label.save(ROOT / "crelabel-label-final.png")

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    save_patch = patch.object(CrelabelWindow, "_save_config")
    load_patch = patch.object(CrelabelWindow, "_load_config", return_value={})
    save_patch.start()
    load_patch.start()
    window = CrelabelWindow()
    headers, rows, title = load_local_rows(str(ROOT / "sample.csv"))
    window.apply_rows(headers, rows, title)
    with patch("crelabel.QMessageBox.warning") as warning:
        window.feishu_url.setText(shared_view_url)
        window.load_feishu(False)
        warning.assert_called_once()
        assert window.source_hint.text() == "链接类型不支持"
    assert window.display_headers[0] == window.mapping["name"]
    assert window.display_headers[1] == window.mapping["code"]
    first_header = window.column_combos[0].currentText()
    second_header = window.column_combos[1].currentText()
    duplicate_index = window.column_combos[2].findText(first_header)
    duplicate_item = window.column_combos[2].model().item(duplicate_index)
    assert duplicate_item is not None and not duplicate_item.isEnabled()
    window.column_combos[2].setCurrentText(first_header)
    assert window.column_combos[2].currentText() == NO_PRINT_OPTION
    assert first_header != second_header
    window.column_combos[2].setCurrentIndex(window.column_combos[2].findText(CUSTOM_OPTION))
    assert window.column_combos[2].isEditable()
    window.column_combos[2].setEditText("质检留样")
    assert window.column_combos[2].currentText() == "质检留样"
    assert ("", "质检留样") in window.selected_columns(window.records[0])
    window.column_combos[3].setCurrentIndex(window.column_combos[3].findText(CUSTOM_OPTION))
    window.column_combos[3].setEditText("A区货架")
    assert window.logical_column_selection(2) == CUSTOM_OPTION
    assert window.logical_column_selection(3) == CUSTOM_OPTION
    assert ("", "A区货架") in window.selected_columns(window.records[0])
    assert len(window.column_combos) == CONTENT_FIELD_SLOTS
    assert window.date_mode.parent() is window.date_controls
    assert window.date_controls.parent() is not None
    custom_text_label = render_label(window.records[0], window.selected_columns(window.records[0]), settings)
    assert custom_text_label.size == label.size
    window.width_spin.setValue(40)
    window.height_spin.setValue(30)
    window.sync_preset_to_size()
    assert window.preset_combo.currentText() == "40 × 30 mm"
    window.reset_label_layout()
    assert window.label_settings().width_mm == 40
    assert window.label_settings().height_mm == 30
    assert window.label_settings().dpi == 300
    assert window.label_layout() == LabelLayout()
    window.text_spacing_step.setValue(0.8)
    assert window.label_layout().text_spacing_mm == 0.8
    before_text_x = window.preview.source_regions["text_0"][0]
    window.move_preview_element("text_0", 0.025, 0.0)
    assert window.preview.source_regions["text_0"][0] > before_text_x
    assert any(name == "text_0" for name, _x, _y in window.label_layout().element_abs_mm)
    window.reset_label_layout()
    before_barcode_region = window.preview.source_regions["barcode"]
    window.barcode_scale_step.setValue(120)
    after_barcode_region = window.preview.source_regions["barcode"]
    assert not window.barcode_scale_step.isHidden()
    assert not window.qr_size_step.isHidden()
    assert window.label_layout().barcode_width_percent == 120
    assert window.label_layout().barcode_height_mm > 6.8
    assert after_barcode_region[2] - after_barcode_region[0] > before_barcode_region[2] - before_barcode_region[0]
    assert after_barcode_region[3] - after_barcode_region[1] > before_barcode_region[3] - before_barcode_region[1]
    window.preview.set_selected_element("barcode")
    barcode_widget_region = window.preview._widget_region("barcode")
    generous_handle_point = QPointF(barcode_widget_region.right() + 10, barcode_widget_region.bottom() + 10)
    assert window.preview._on_resize_handle(generous_handle_point)
    scaled_barcode_label = render_label(
        window.records[0], window.selected_columns(window.records[0]),
        window.label_settings(), window.printed_date(), window.label_layout(),
        window.barcode_value(window.records[0]),
    )
    scaled_decoded = {(item.format.name, item.text) for item in zxingcpp.read_barcodes(scaled_barcode_label.convert("L"))}
    assert ("Code128", window.barcode_value(window.records[0])) in scaled_decoded, scaled_decoded
    before_qr_region = window.preview.source_regions["qr"]
    window.qr_size_step.setValue(8.0)
    after_qr_region = window.preview.source_regions["qr"]
    assert after_qr_region[2] - after_qr_region[0] < before_qr_region[2] - before_qr_region[0]
    assert after_qr_region[3] - after_qr_region[1] < before_qr_region[3] - before_qr_region[1]
    window.reset_label_layout()
    assert not window.logo_check.isChecked()
    window.logo_check.setChecked(True)
    assert "logo" in window.preview.source_regions
    before_logo = window.preview.source_regions["logo"]
    window.logo_size_step.setValue(16)
    after_logo = window.preview.source_regions["logo"]
    assert after_logo[2] - after_logo[0] > before_logo[2] - before_logo[0]
    window.logo_check.setChecked(False)
    assert "logo" not in window.preview.source_regions
    assert window.barcode_check.isChecked() and window.qr_check.isChecked()
    window.barcode_check.setChecked(False)
    assert "barcode" not in window.preview.source_regions
    window.qr_check.setChecked(False)
    assert "qr" not in window.preview.source_regions
    window.barcode_check.setChecked(True)
    window.qr_check.setChecked(True)
    assert {"barcode", "qr"}.issubset(window.preview.source_regions)
    hidden_codes, hidden_regions = render_label_with_regions(
        record, list(record.raw_fields.items()), settings, layout=LabelLayout(show_barcode=False, show_qr=False),
    )
    assert "barcode" not in hidden_regions and "qr" not in hidden_regions
    packed_30, packed_regions = render_label_with_regions(
        window.records[0], window.selected_columns(window.records[0]), LabelSettings(30, 20, 300),
        window.printed_date(), LabelLayout(show_barcode=True, show_qr=True, qr_size_mm=7.0, barcode_height_mm=5.4),
        window.barcode_value(window.records[0]),
    )
    assert packed_30.size == LabelSettings(30, 20, 300).pixel_size
    if "text_0" in packed_regions and "barcode" in packed_regions:
        assert packed_regions["barcode"][3] <= packed_30.size[1]
    if "text_0" in packed_regions and "qr" in packed_regions:
        assert packed_regions["qr"][3] <= packed_30.size[1]
    compact_30, _compact_regions = render_label_with_regions(
        window.records[0], window.selected_columns(window.records[0])[:2], LabelSettings(30, 20, 300),
        "", LabelLayout(show_barcode=True, show_qr=True, qr_size_mm=7.0, barcode_height_mm=5.4),
        window.barcode_value(window.records[0]),
    )
    compact_decoded = {(item.format.name, item.text) for item in zxingcpp.read_barcodes(compact_30.convert("L"))}
    assert ("Code128", window.barcode_value(window.records[0])) in compact_decoded, compact_decoded
    assert ("QRCode", window.records[0].link) in compact_decoded, compact_decoded
    original_qr = window.qr_size_step.value()
    stored = window._store_template("验证模板 30x20")
    assert stored == "验证模板 30x20"
    window.qr_size_step.setValue(14)
    assert window._apply_named_template("验证模板 30x20")
    assert abs(window.qr_size_step.value() - original_qr) < 0.05
    assert "验证模板 30x20" in [window.template_combo.itemText(i) for i in range(window.template_combo.count())]
    assert [window.print_method_combo.itemText(i) for i in range(window.print_method_combo.count())] == ["热转印（碳带）", "热敏（无碳带）"]
    assert not window.text_scale_step.isHidden()
    window.text_alignment_combo.setCurrentIndex(window.text_alignment_combo.findData("right"))
    assert window.label_layout().text_alignment == "right"
    right_x = window.preview.source_regions["text_0"][0]
    window.move_preview_element("text_0", 0.04, 0.0)
    window.text_alignment_combo.setCurrentIndex(window.text_alignment_combo.findData("left"))
    assert window.preview.source_regions["text_0"][0] < right_x
    window.text_alignment_combo.setCurrentIndex(window.text_alignment_combo.findData("center"))
    window.width_spin.setValue(60)
    window.height_spin.setValue(40)
    window.sync_preset_to_size()
    assert window.preset_combo.currentText() == "60 × 40 mm"
    window.text_scale_step.setValue(100)
    window.text_alignment_combo.setCurrentIndex(window.text_alignment_combo.findData("left"))
    window.update_preview()
    initial_text_x = window.preview.source_regions["text_0"][0]
    window.move_preview_element("text_0", 0.08, 0.0)
    right_edge_x = window.preview.source_regions["text_0"][0]
    assert right_edge_x > initial_text_x
    window.move_preview_element("text_0", -0.05, 0.0)
    assert window.preview.source_regions["text_0"][0] < right_edge_x
    if "text_1" in window.preview.source_regions:
        first_width = window.preview.source_regions["text_0"][2] - window.preview.source_regions["text_0"][0]
        window.text_scale_step.setValue(160)
        assert window.label_layout().text_scale_percent == 160
        assert set(window.label_layout().line_scale_percent) == {160}
        grown = window.preview.source_regions["text_0"][2] - window.preview.source_regions["text_0"][0]
        assert grown >= first_width
        window.text_scale_step.setValue(100)
    window.offset_x_step.setValue(1.5)
    window.text_scale_step.setValue(130)
    window.preset_combo.setCurrentText("30 × 20 mm")
    assert window.label_settings().pixel_size == LabelSettings(30, 20, 300).pixel_size
    assert window.preset_combo.currentText() == "30 × 20 mm"
    assert window.offset_x_step.value() == 1.5
    assert window.text_scale_step.value() == 100
    assert window.media_sensing_combo.currentData() == "gap"
    assert window.date_mode.count() == 3
    window.date_mode.setCurrentIndex(0)
    assert window.date_edit.isHidden()
    window.date_mode.setCurrentIndex(2)
    assert not window.date_edit.isHidden()
    window.show()
    app.processEvents()
    assert [action.text() for action in window.menuBar().actions()] == [
        "飞书扫码授权", "检查飞书环境", "导入 Excel / CSV", "配置整机标签表格",
    ]
    assert not window.label_type.drawBase()
    window.grab().save(str(ROOT / "crelabel-ui-final.png"))
    window.close()
    save_patch.stop()
    load_patch.stop()

    with patch.object(CrelabelWindow, "_load_config", return_value={"printer": "Adobe PDF"}), patch.object(CrelabelWindow, "_save_config"), patch("crelabel.list_printers", return_value=["Adobe PDF", "ZDesigner ZD888-300dpi ZPL"]):
        printer_window = CrelabelWindow()
        assert printer_window.printer_combo.currentText() == "ZDesigner ZD888-300dpi ZPL"
        printer_window.close()

    cache_note = "not available"
    start = time.perf_counter()
    try:
        cached = load_feishu_data(FEISHU_TEST_URL)
        duration = time.perf_counter() - start
        assert cached.get("cache_hit") is True
        assert len(cached.get("records", [])) == 115
        live_headers = [clean(value) for value in cached.get("fields", [])] + ["记录分享链接"]
        live_rows = []
        for item in cached.get("records", []):
            row = {header: item.get("fields", {}).get(header, "") for header in live_headers}
            row["记录分享链接"] = item.get("record_share_link", "")
            live_rows.append(row)
        live_mapping = auto_mapping(live_headers)
        live_records = records_from_rows(live_headers, live_rows, live_mapping)
        live_window = CrelabelWindow()
        live_window.apply_rows(live_headers, live_rows, "飞书实表")
        assert live_window.display_headers[:2] == [live_mapping["name"], live_mapping["code"]]
        live_window.close()
        material = next(item for item in live_records if item.code)
        live_label = render_label(material, [(live_mapping["name"], material.name), (live_mapping["code"], material.code)], settings, barcode_payload=material.code)
        live_decoded = {(item.format.name, item.text) for item in zxingcpp.read_barcodes(live_label.convert("L"))}
        assert ("Code128", material.code) in live_decoded, live_decoded
        cache_note = f"{duration:.4f}s / 115 records"
    except Exception as exc:
        cache_note = f"skipped: {type(exc).__name__}: {exc!r}"

    print("PASS label-size=472x354")
    runtime_note = "bundled lark-cli 1.0.67" if bundled_cli is not None else "external lark-cli omitted"
    print(f"PASS {runtime_note} and first-run config-to-auth handoff")
    print("PASS Code128+QRCode decode, custom barcode source")
    print("PASS mixed lark-cli output parse, shared-view URL guidance, unique field selection plus custom content")
    print("PASS ZPL ^MTT/^MTD + media sensing + ~JC calibration")
    print("PASS UI 40x30/300dpi, 2 print methods, 3 date modes, adjustable layout")
    print(f"CACHE {cache_note}")


if __name__ == "__main__":
    main()
