"""Offline source/selection and geometry regression checks; never print."""
from __future__ import annotations

import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import zxingcpp
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from crelabel import CrelabelWindow, NO_PRINT_OPTION, STYLE
from feishu_client import FeishuError, discover_feishu_source, load_feishu_data, table_url
from label_core import LabelLayout, LabelRecord, LabelSettings, render_label, render_label_with_regions

SOURCE = "https://example.feishu.cn/base/BaseTest"
TABLES = [{"id": "tblOne", "name": "物料"}, {"table_id": "tblTwo", "name": "库存"}]


class SourceTests(unittest.TestCase):
    def discover(self, url, resolved=None, tables=None):
        with patch("feishu_client.run_cli", side_effect=[
            resolved or {"base_token": "BaseTest", "title": "测试表"},
            {"tables": tables if tables is not None else TABLES},
        ]):
            return discover_feishu_source(url)

    def test_root_requires_selection_and_single_table_auto_selects(self):
        self.assertEqual(self.discover(SOURCE)["table_id"], "")
        self.assertEqual(self.discover(SOURCE, tables=TABLES[:1])["table_id"], "tblOne")

    def test_view_and_wiki_coordinates(self):
        url = SOURCE + "?table=tblTwo&view=vewFiltered"
        self.assertEqual(self.discover(url)["source_url"], url)
        self.assertEqual(self.discover(url)["table_id"], "tblTwo")
        wiki = "https://example.feishu.cn/wiki/WikiTest"
        self.assertEqual(self.discover(wiki, {"base_token": "BaseTest", "table_id": "tblTwo"})["table_id"], "tblTwo")
        with self.assertRaises(FeishuError):
            self.discover(SOURCE + "?table=tblDeleted")
        with self.assertRaises(FeishuError):
            self.discover(wiki, {"obj_type": "docx"})
        with self.assertRaises(FeishuError):
            self.discover(SOURCE, tables=[])

    def test_switch_table_drops_foreign_view_and_record(self):
        url = table_url(SOURCE + "?table=tblOne&view=vewOld&record=recOld", "tblTwo")
        self.assertEqual(parse_qs(urlparse(url).query), {"table": ["tblTwo"]})

    def test_stale_metadata_keeps_view_for_root_but_not_table_switch(self):
        for suffix, expected_view in [("", "vewOld"), ("?table=tblTwo", None)]:
            seen = []
            def cli(*args):
                seen.append(args)
                if args[1] == "+field-list":
                    return {"fields": [{"name": "名称", "type": "text"}]}
                if args[1] == "+record-list":
                    return {"fields": ["名称"], "record_id_list": [], "data": [], "has_more": False}
                raise AssertionError(args)
            previous = {"base_token": "BaseTest", "table_id": "tblOne", "view_id": "vewOld"}
            with patch("feishu_client.run_cli", side_effect=cli), patch("feishu_client._read_stale_cache", return_value=previous), patch("feishu_client._write_cache"):
                data = load_feishu_data(SOURCE + suffix, force_refresh=True)
            args = next(a for a in seen if a[1] == "+record-list")
            self.assertEqual(data["records"], [])
            self.assertEqual(args[args.index("--view-id") + 1] if "--view-id" in args else None, expected_view)

    def test_bad_pagination_does_not_silently_return_partial_records(self):
        for page in [
            {"record_id_list": ["rec1"], "data": [], "has_more": False},
            {"record_id_list": ["rec1"], "data": [["too", "many"]], "has_more": False},
            {"record_id_list": [], "data": [], "has_more": True},
            {"record_id_list": ["rec1", "rec1"], "data": [["a"], ["b"]], "has_more": False},
        ]:
            with patch("feishu_client.run_cli", side_effect=[{"base_token": "BaseTest"}, {"fields": [{"name": "名称"}]}, page]), patch("feishu_client._read_stale_cache", return_value=None), patch("feishu_client._write_cache") as write:
                with self.assertRaises(FeishuError):
                    load_feishu_data(SOURCE + "?table=tblOne", force_refresh=True)
                write.assert_not_called()

    def test_paginated_view_records_and_links(self):
        seen = []
        def cli(*args):
            seen.append(args)
            command = args[1]
            if command == "+url-resolve":
                return {"base_token": "BaseTest", "table_id": "tblTwo", "view_id": "vewFiltered"}
            if command == "+field-list":
                return {"fields": [{"name": "名称", "type": "text"}, {"name": "数量", "type": "number"}]}
            if command == "+record-list":
                self.assertEqual(args[args.index("--view-id") + 1], "vewFiltered")
                offset = int(args[args.index("--offset") + 1])
                return {"fields": ["名称", "数量"], "record_id_list": [f"rec{offset}"],
                        "data": [[f"零件{offset}", offset]], "has_more": offset == 0}
            if command == "+record-share-link-create":
                self.assertIn("--record-id", args)
                self.assertNotIn("--record-ids", args)
                return {"record_share_links": {f"rec{i}": f"https://example.feishu.cn/r/{i}" for i in range(2)}}
            raise AssertionError(args)
        with patch("feishu_client.run_cli", side_effect=cli), patch("feishu_client._read_stale_cache", return_value=None), patch("feishu_client._write_cache"):
            data = load_feishu_data(SOURCE, force_refresh=True)
        self.assertEqual([r["fields"]["数量"] for r in data["records"]], [0, 1])
        self.assertTrue(all(r["record_share_link"] for r in data["records"]))
        self.assertEqual(len([args for args in seen if args[1] == "+record-list"]), 2)


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font_id = QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
        families = QFontDatabase.applicationFontFamilies(font_id)
        family = families[0] if families else "Microsoft YaHei UI"
        cls.app.setFont(QFont(family, 10))
        cls.app.setStyleSheet(STYLE.replace("Microsoft YaHei UI", family))

    def setUp(self):
        self.patches = [patch.object(CrelabelWindow, "_save_config"),
                        patch.object(CrelabelWindow, "_load_config", return_value={}),
                        patch("crelabel.list_printers", return_value=[])]
        for item in self.patches:
            item.start()
        self.window = CrelabelWindow()
        self.window.apply_rows(["名称", "料号", "记录分享链接"], [
            {"名称": f"物料{i}", "料号": f"PN{i}", "记录分享链接": f"https://example.com/{i}"}
            for i in range(3)], "测试数据")
        self.window.date_mode.setCurrentIndex(0)

    def tearDown(self):
        self.window.close()
        for item in reversed(self.patches):
            item.stop()

    def test_drag_keeps_siblings_and_code_sizes(self):
        w = self.window
        for selected in ("text_0", "text_1", "qr", "barcode"):
            w.reset_label_layout()
            before = dict(w.preview.source_regions)
            for _ in range(5):
                w.move_preview_element(selected, 0.006, 0.006)
                after = w.preview.source_regions
                for name, bound in before.items():
                    new = after[name]
                    self.assertEqual((new[2] - new[0], new[3] - new[1]),
                                     (bound[2] - bound[0], bound[3] - bound[1]), (selected, name))
                    if name not in (selected, "text"):
                        self.assertEqual(bound, new, (selected, name))
            self.assertNotEqual(before[selected][:2], after[selected][:2])
            # Actual print rendering must use exactly the preview geometry.
            record = w.records[0]
            _, printed = render_label_with_regions(record, w.selected_columns(record), w.label_settings(),
                w.printed_date(), w.label_layout(), w.barcode_value(record))
            self.assertEqual(printed, after)

    def test_wrapped_text_does_not_drift_on_zero_move(self):
        w = self.window
        w.apply_rows(["名称"], [{"名称": "短\n这是一行更长的文字"}], "换行测试")
        w.barcode_check.setChecked(False)
        w.qr_check.setChecked(False)
        before = dict(w.preview.source_regions)
        for _ in range(5):
            w.move_preview_element("text_0", 0, 0)
            self.assertEqual(w.preview.source_regions, before)

    def test_machine_group_pins_without_resizing_qr(self):
        record = LabelRecord(1, code="TEST-L-01", link="https://example.com/1")
        settings = LabelSettings()
        layout = LabelLayout(show_barcode=False, show_logo=True)
        columns = [("样机编号", record.code), ("左右手", "L")]
        image, regions = render_label_with_regions(record, columns, settings, layout=layout)
        pinned = tuple((name, b[0] / settings.dots_per_mm, b[1] / settings.dots_per_mm)
                       for name, b in regions.items() if name != "text")
        frozen, after = render_label_with_regions(record, columns, settings, layout=replace(layout, element_abs_mm=pinned))
        self.assertEqual(after, regions)
        self.assertEqual(image.tobytes(), frozen.tobytes())
        self.assertIn(record.link, [r.text for r in zxingcpp.read_barcodes(frozen.convert("L"))])

    def test_field_and_nonconsecutive_row_selection_drive_print_jobs(self):
        w = self.window
        for combo in w.column_combos:
            combo.setCurrentText(NO_PRINT_OPTION)
        w.column_combos[0].setCurrentText("名称")
        w.clear_selection()
        model = w.table.selectionModel()
        for row in (0, 2):
            model.select(w.table.model().index(row, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        self.assertEqual([r.code for r in w.selected_records()], ["PN0", "PN2"])
        with patch("crelabel.render_label", wraps=render_label) as render:
            jobs, count = w.build_jobs(w.selected_records())
        self.assertEqual(count, 2)
        self.assertEqual(len(jobs), 2)
        self.assertEqual([call.args[1] for call in render.call_args_list], [[("名称", "物料0")], [("名称", "物料2")]])
        w.clear_selection()
        self.assertFalse(w.selected_records())
        self.assertFalse(w.print_selected_button.isEnabled())

    def test_connect_root_and_switch_table_flow(self):
        w = self.window
        w.feishu_url.setText(SOURCE)
        with patch.object(w, "run_worker") as worker:
            w.connect_source()
            self.assertEqual(worker.call_args.args[:2], (discover_feishu_source, SOURCE))
        info = {"source_url": SOURCE, "title": "测试表", "table_id": "", "tables": [{"id": "tblOne", "name": "物料"}, {"id": "tblTwo", "name": "库存"}]}
        w.source_discovered(info)
        self.assertFalse(w.records)
        self.assertFalse(w.print_selected_button.isEnabled())
        self.assertFalse(w.source_table_combo.isHidden())
        with patch.object(w, "load_feishu") as load:
            w.select_source_table(2)
            self.assertIn("table=tblTwo", w.feishu_url.text())
            load.assert_called_once_with(True)
        self.assertFalse(w.records)

    def test_connection_failure_cannot_print_old_source(self):
        w = self.window
        self.assertTrue(w.records)
        w.feishu_url.setText(SOURCE)
        with patch.object(w, "run_worker"):
            w.connect_source()
        with patch("crelabel.QMessageBox.critical"):
            w.handle_error("没有访问权限")
        self.assertFalse(w.records)
        self.assertFalse(w.print_selected_button.isEnabled())
        self.assertFalse(w.print_all_button.isEnabled())

    def test_original_view_preserved_and_ui_geometry(self):
        w = self.window
        url = SOURCE + "?table=tblOne&view=vewOriginal"
        w.feishu_url.setText(url)
        info = {"source_url": url, "title": "测试表", "table_id": "tblOne", "tables": [{"id": "tblOne", "name": "物料"}]}
        with patch.object(w, "load_feishu") as load:
            w.source_discovered(info)
            load.assert_called_once_with(True)
        self.assertEqual(w.feishu_url.text(), url)
        w.feishu_loaded({"title": "示例物料", "fields": ["名称", "料号"], "records": [
            {"fields": {"名称": "连接器", "料号": "PN-001"}, "record_share_link": "https://example.com/1"},
            {"fields": {"名称": "传感器", "料号": "PN-002"}, "record_share_link": "https://example.com/2"}]})
        out = ROOT / "outputs/source-layout-validation"
        out.mkdir(parents=True, exist_ok=True)
        for width, height in [(1440, 900), (1120, 720)]:
            w.resize(width, height)
            w.show()
            self.app.processEvents()
            self.assertTrue(w.feishu_url.isVisible())
            self.assertGreater(w.feishu_url.width(), 150)
            self.assertTrue(w.grab().save(str(out / f"ui-{width}x{height}.png")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
