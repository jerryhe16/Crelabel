import os
import sys
import json
import importlib.util
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import zxingcpp
from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFontDatabase, QFont
from crelabel import CrelabelWindow, STYLE, machine_code_header
from label_core import auto_mapping, records_from_rows, render_label, clean

app = QApplication.instance() or QApplication([])
font_id = QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0],10))
app.setStyle('Fusion')
app.setStyleSheet(STYLE.replace('Microsoft YaHei UI', QFontDatabase.applicationFontFamilies(font_id)[0]))
data = json.loads((ROOT / 'outputs/machine-live.json').read_text(encoding='utf-8'))
out = ROOT / 'outputs/v0.8.3-validation'
out.mkdir(exist_ok=True)
with patch.object(CrelabelWindow, '_load_config', return_value={}), patch.object(CrelabelWindow, '_save_config'), patch.object(CrelabelWindow, 'load_feishu'):
    w = CrelabelWindow()
    w.label_type.setCurrentIndex(1)
    w.feishu_loaded(data)
    w.show()
    app.processEvents()
    assert w.logo_check.isChecked()
    assert 'logo' in w.preview.source_regions
    assert len(w.records) == 6
    results = []
    for i, (record, source) in enumerate(zip(w.records, data['records'])):
        assert record.code == clean(source['fields']['样机编号'])
        assert record.link == source['record_share_link']
        if not w.machine_side(record) or not record.code.strip(' -'):
            try:
                w.build_jobs([record])
                raise AssertionError('incomplete identifier accepted')
            except ValueError:
                pass
            continue
        columns = w.selected_columns(record)
        assert columns[0] == ('样机编号', record.code)
        assert columns[1] == ('左右手', clean(source['fields']['左右手']))
        assert all(not combo.isHidden() for combo in w.column_combos)
        for width, height in [(40,30), (30,20)]:
            w.width_spin.setValue(width)
            w.height_spin.setValue(height)
            img = render_label(record, w.selected_columns(record), w.label_settings(), w.printed_date(), w.label_layout(), w.barcode_value(record))
            decoded = {(r.format.name, r.text) for r in zxingcpp.read_barcodes(img.convert('L'))}
            assert ('QRCode', record.link) in decoded, (record.code, decoded)
            assert not any(fmt == 'Code128' for fmt, _ in decoded), decoded
            img.save(out / f'label-{i}-{width}x{height}.png')
        results.append({'number':record.code, 'record_id':source['record_id'], 'qr':record.link})
    assert [action.text() for action in w.menuBar().actions()] == ['飞书扫码授权', '检查飞书环境', '导入 Excel / CSV', '配置整机标签表格']
    assert not w.label_type.drawBase()
    assert not any(button.text() == '设置' for button in w.findChildren(QPushButton))
    w.table.clearSelection()
    assert not w.selected_records() and not w.print_selected_button.isEnabled()
    w.table.selectRow(0)
    w.set_busy(True)
    assert not w.print_selected_button.isEnabled()
    w.set_busy(False)
    geometry = []
    for width,height in [(1440,900),(1120,720)]:
        w.resize(width,height)
        app.processEvents()
        p = w.print_selected_button.mapTo(w, QPoint(0,0))
        assert p.y() < 100 and p.x() + w.print_selected_button.width() <= width
        w.grab().save(str(out / f'ui-{width}x{height}.png'))
        geometry.append([width,height,p.x(),p.y()])
    # Ablation: remove explicit machine mapping, using the original generic mapper.
    assert machine_code_header(w.headers) == '样机编号'
    baseline_records = records_from_rows(w.headers,w.raw_rows,auto_mapping(w.headers))
    generic_correct = sum(a.code == b.code for a,b in zip(baseline_records,w.records) if w.machine_side(b))
    assert generic_correct == 5
    spec = importlib.util.spec_from_file_location('baseline_crelabel', ROOT / 'outputs/v0.8.2-baseline/crelabel.py')
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    with patch.object(baseline.CrelabelWindow,'_load_config',return_value={}), patch.object(baseline.CrelabelWindow,'_save_config'):
        old = baseline.CrelabelWindow()
        old.apply_rows(w.headers,w.raw_rows,'baseline')
        old.show()
        app.processEvents()
        old.table.clearSelection()
        assert len(old.selected_records()) == 1
        old_print = next(b for b in old.findChildren(QPushButton) if b.text() == '打印选中行')
        scroll = old.findChild(QScrollArea)
        baseline_visible = scroll.viewport().rect().contains(old_print.mapTo(scroll.viewport(),QPoint(0,0)))
        old.grab().save(str(out / 'baseline.png'))
        old.close()
    (out/'results.json').write_text(json.dumps({'decoded':results,'sizes':['40x30','30x20'],'top_button_positions':geometry,'ablation':{'generic_mapping_correct':generic_correct,'explicit_mapping_correct':5,'baseline_print_visible':baseline_visible,'new_print_visible':True,'baseline_empty_selection_records':1,'new_empty_selection_records':0},'physical_print':'not tested'},ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        w.apply_rows(["左右手", "记录分享链接"], [{"左右手": "左手", "记录分享链接": "https://example.com/r"}], "missing")
        raise AssertionError("missing 样机编号 accepted")
    except ValueError as exc:
        assert "样机编号" in str(exc)
    w.apply_rows(
        ["自动编号", "左右手", "记录分享链接"],
        [{"自动编号": "OLD-001", "左右手": "左手", "记录分享链接": "https://example.com/r1"}],
        "legacy",
    )
    assert w.mapping["code"] == "自动编号" and w.records[0].code == "OLD-001"
    w.apply_rows(
        ["样机编号", "自动编号", "左右手", "记录分享链接"],
        [{"样机编号": "NEW-001-L", "自动编号": "OLD-001", "左右手": "左手", "记录分享链接": "https://example.com/r2"}],
        "both",
    )
    assert w.mapping["code"] == "样机编号" and w.records[0].code == "NEW-001-L"
    w.close()
print('PASS: 5 live numbers x 2 sizes, QR only + L/R; incomplete number blocked; empty selection; busy state; 2 UI sizes; 3 ablations; 样机编号 mapping')
