"""One text item and at most one machine-readable symbol, at native dots."""
import barcode
import qrcode
from PIL import Image, ImageDraw


def render_compact(record, columns, settings, mode, barcode_payload):
    from label_core import get_font, clean, to_thermal_bitmap
    w, h = settings.pixel_size
    margin = max(3, round(settings.dots_per_mm * 0.4))
    gap = max(3, round(settings.dots_per_mm * 0.3))
    cw, ch = w - margin * 2, h - margin * 2
    image = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(image)
    text = clean(columns[0][1]) if columns else ""
    regions = {}
    tx, ty, tw, th = margin, margin, cw, ch
    symbol = None
    sx = sy = 0
    if mode == "qr":
        payload = record.link or barcode_payload or record.code or record.sn
        if not payload:
            raise ValueError("二维码没有内容，请检查记录链接或料号。")
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=1)
        qr.add_data(payload)
        qr.make(fit=True)
        symbol = qr.make_image().convert("1")
        # Reserve a readable line below on portrait labels; landscape uses
        # side-by-side only when it leaves enough room for text.
        if w > h and cw - ch - gap >= 35:
            target = ch
            tx, tw = margin, cw - target - gap
            sx, sy = margin + tw + gap, margin
        else:
            th = min(24, max(12, ch // 4)) if text else 0
            target = min(cw, ch - th - (gap if text else 0))
            sx, sy = (w - target) // 2, margin + th + (gap if text else 0)
        scale = target // symbol.width
        if scale < 2:
            raise ValueError("当前纸张放不下可读二维码；请改用较大标签或条形码。飞书长链接需要更大的二维码。")
        symbol = symbol.resize((symbol.width * scale, symbol.height * scale), Image.Resampling.NEAREST)
        sx += (target - symbol.width) // 2
    elif mode == "barcode":
        payload = barcode_payload or record.code or record.sn
        if not payload:
            raise ValueError("条形码没有料号，请选择有料号的记录。")
        bits = barcode.get("code128", payload).build()[0]
        module = cw // (len(bits) + 20)
        if module < 1:
            raise ValueError("料号太长，当前标签宽度放不下条形码，请使用更宽的纸张或二维码。")
        th = min(24, max(12, ch // 3)) if text else 0
        bh = ch - th - (gap if text else 0)
        if bh < 24:
            raise ValueError("纸张高度不足，请使用更高的标签。")
        symbol = Image.new("1", ((len(bits) + 20) * module, bh), 1)
        bars = ImageDraw.Draw(symbol)
        for i, bit in enumerate(bits):
            if bit == "1":
                x = (i + 10) * module
                bars.rectangle((x, 0, x + module - 1, bh - 1), fill=0)
        sx, sy = (w - symbol.width) // 2, margin + th + (gap if text else 0)
    if text:
        for size in range(min(36, th), 7, -1):
            font = get_font(size, text=text)
            box = draw.textbbox((0, 0), text, font=font)
            bw, bh = box[2] - box[0], box[3] - box[1]
            if bw <= tw and bh <= th:
                break
        else:
            raise ValueError("文字过长，请减少自定义文字或选择较短的字段。")
        x, y = tx + (tw - bw) // 2, ty + (th - bh) // 2
        draw.text((x - box[0], y - box[1]), text, font=font, fill=0)
        regions["text"] = (x, y, x + bw, y + bh)
    if symbol is not None:
        image.paste(symbol.convert("L"), (sx, sy))
        regions["qr" if mode == "qr" else "barcode"] = (sx, sy, sx + symbol.width, sy + symbol.height)
    return to_thermal_bitmap(image), regions
