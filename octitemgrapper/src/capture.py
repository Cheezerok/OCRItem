from __future__ import annotations

from typing import Optional, List, Tuple

import numpy as np
from mss import mss

from roi_selector import Rect
from scale_utils import get_pixel_scale

# Optional window capture on Windows
try:
    import win32gui
    import win32ui
    import win32con
    import win32api
except Exception:  # pragma: no cover
    win32gui = None
    win32ui = None
    win32con = None
    win32api = None


class ScreenCapturer:
    def __init__(self) -> None:
        self._sct: Optional[mss] = None

    def __enter__(self) -> "ScreenCapturer":
        self._sct = mss()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None

    def open(self) -> None:
        if self._sct is None:
            self._sct = mss()

    def close(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None

    # Monitors enumeration
    def list_monitors(self) -> List[Rect]:
        self.open()
        assert self._sct is not None
        monitors: List[Rect] = []
        for mon in self._sct.monitors[1:]:  # [0] is virtual full bounding
            monitors.append(Rect(x=mon["left"], y=mon["top"], width=mon["width"], height=mon["height"]))
        return monitors

    def grab_bgr(self, rect: Rect) -> np.ndarray:
        if self._sct is None:
            self.open()
        assert self._sct is not None
        sx, sy = get_pixel_scale()
        bbox = {
            "left": int(round(rect.x * sx)),
            "top": int(round(rect.y * sy)),
            "width": int(round(rect.width * sx)),
            "height": int(round(rect.height * sy)),
        }
        shot = self._sct.grab(bbox)
        img = np.frombuffer(shot.bgra, dtype=np.uint8)
        img = img.reshape((shot.height, shot.width, 4))
        bgr = img[:, :, :3].copy()
        return bgr

    # Window capture (Windows-only)
    def list_windows(self) -> List[Tuple[int, str]]:
        result: List[Tuple[int, str]] = []
        if win32gui is None:
            return result

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    result.append((hwnd, title))
        win32gui.EnumWindows(enum_handler, None)
        return result

    def grab_window_bgr(self, hwnd: int) -> Optional[np.ndarray]:
        if win32gui is None or win32ui is None:
            return None
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            # Convert to screen coords
            pt = win32gui.ClientToScreen(hwnd, (left, top))
            left, top = pt
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            hwin = win32gui.GetDesktopWindow()
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)

            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
            bgr = img[:, :, :3].copy()
            # Cleanup
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            return bgr
        except Exception:
            return None 