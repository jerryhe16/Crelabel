"""Raster printing through installed Windows drivers (no raw ZPL)."""
from PIL import ImageWin
import win32con
import win32gui
import win32print
import win32ui


def create_label_dc(printer, width_mm, height_mm):
    handle = win32print.OpenPrinter(printer)
    try:
        mode = win32print.GetPrinter(handle, 2)["pDevMode"]
        mode.PaperSize = 256
        mode.PaperWidth = round(width_mm * 10)
        mode.PaperLength = round(height_mm * 10)
        mode.Orientation = 1
        mode.Copies = 1
        mode.Fields |= win32con.DM_PAPERSIZE | win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH | win32con.DM_ORIENTATION | win32con.DM_COPIES
        raw = win32gui.CreateDC("WINSPOOL", printer, mode)
        return win32ui.CreateDCFromHandle(raw)
    finally:
        win32print.ClosePrinter(handle)


def print_images(printer, images, width_mm, height_mm, copies=1):
    dc = create_label_dc(printer, width_mm, height_mm)
    started = False
    try:
        width = round(width_mm * dc.GetDeviceCaps(win32con.LOGPIXELSX) / 25.4)
        height = round(height_mm * dc.GetDeviceCaps(win32con.LOGPIXELSY) / 25.4)
        if abs(dc.GetDeviceCaps(win32con.PHYSICALWIDTH) - width) > 4 or abs(dc.GetDeviceCaps(win32con.PHYSICALHEIGHT) - height) > 4:
            raise ValueError("打印驱动未接受标签尺寸，请在打印机首选项中设置相同纸张尺寸后重试。")
        x = -dc.GetDeviceCaps(win32con.PHYSICALOFFSETX)
        y = -dc.GetDeviceCaps(win32con.PHYSICALOFFSETY)
        dc.StartDoc("Crelabel")
        started = True
        for image in images:
            for _ in range(copies):
                dc.StartPage()
                ImageWin.Dib(image.convert("RGB")).draw(dc.GetHandleOutput(), (x, y, x + width, y + height))
                dc.EndPage()
        dc.EndDoc()
        started = False
    finally:
        if started:
            dc.AbortDoc()
        dc.DeleteDC()
