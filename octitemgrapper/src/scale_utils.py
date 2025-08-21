from __future__ import annotations

from typing import Tuple

from PyQt5 import QtGui


def get_pixel_scale() -> Tuple[float, float]:
    screen = QtGui.QGuiApplication.primaryScreen()
    if screen is None:
        return 1.0, 1.0
    try:
        sx = float(screen.physicalDotsPerInchX()) / float(screen.logicalDotsPerInchX())
        sy = float(screen.physicalDotsPerInchY()) / float(screen.logicalDotsPerInchY())
    except Exception:
        dpr = float(screen.devicePixelRatio()) if screen.devicePixelRatio() else 1.0
        sx = dpr
        sy = dpr
    if not (0.5 <= sx <= 4.0):
        sx = 1.0
    if not (0.5 <= sy <= 4.0):
        sy = 1.0
    return sx, sy 