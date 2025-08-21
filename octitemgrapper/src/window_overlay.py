from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from capture import ScreenCapturer
from recognizer import ORBItemRecognizer
from output_writer import OutputWriter
from roi_selector import Rect
from zone_template import NRect, to_abs


class WindowZonesOverlay(QtWidgets.QDialog):
    def __init__(self, hwnd: int, zones: List[NRect], capturer: ScreenCapturer, recognizer: ORBItemRecognizer, output: OutputWriter, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Разметка окна — кликните по зоне для распознавания")
        self.setModal(True)
        self.hwnd = hwnd
        self.zones = zones
        self.capturer = capturer
        self.recognizer = recognizer
        self.output = output

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update)
        self.timer.start()

        self.setMinimumSize(640, 360)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        qp.fillRect(self.rect(), QtGui.QColor(20, 20, 20))

        frame = self.capturer.grab_window_bgr(self.hwnd)
        if frame is None:
            qp.setPen(QtGui.QPen(QtGui.QColor(220, 80, 80)))
            qp.drawText(self.rect(), QtCore.Qt.AlignCenter, "Не удалось захватить окно")
            return

        h, w, _ = frame.shape
        rgb = frame[:, :, ::-1]
        qimg = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)

        # Fit to dialog
        target = self.rect()
        scaled = pix.scaled(target.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        qp.drawPixmap(x, y, scaled)

        # Draw zones over the scaled image
        scale = scaled.width() / w if w else 1.0
        # use same scale for height due to KeepAspectRatio
        ox = x
        oy = y
        pen = QtGui.QPen(QtGui.QColor(42, 130, 218))
        pen.setWidth(2)
        qp.setPen(pen)
        brush = QtGui.QBrush(QtGui.QColor(42, 130, 218, 60))
        qp.setBrush(brush)

        for idx, nr in enumerate(self.zones, start=1):
            ar = to_abs(nr, w, h)
            rx = int(ox + ar.x * scale)
            ry = int(oy + ar.y * scale)
            rw = int(ar.width * scale)
            rh = int(ar.height * scale)
            qp.drawRect(rx, ry, rw, rh)
            qp.drawText(QtCore.QRect(rx, ry, rw, rh), QtCore.Qt.AlignCenter, str(idx))

        qp.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.LeftButton:
            return
        # Determine which zone was clicked
        frame = self.capturer.grab_window_bgr(self.hwnd)
        if frame is None:
            return
        h, w, _ = frame.shape

        # Reverse transform from widget coords to image coords
        target = self.rect()
        pix_w = target.width()
        pix_h = int(w * (target.width() / w)) if w else target.height()

        scaled_w = min(target.width(), int((target.height() * w) / h)) if h else target.width()
        scaled_h = min(target.height(), int((target.width() * h) / w)) if w else target.height()
        x = (target.width() - scaled_w) // 2
        y = (target.height() - scaled_h) // 2

        click = event.pos()
        if not (x <= click.x() <= x + scaled_w and y <= click.y() <= y + scaled_h):
            return
        scale = scaled_w / w if w else 1.0
        ix = int((click.x() - x) / scale)
        iy = int((click.y() - y) / scale)

		# Find zone index
		for idx, nr in enumerate(self.zones):
			ar = to_abs(nr, w, h)
			if ar.x <= ix <= ar.x + ar.width and ar.y <= iy <= ar.y + ar.height:
				# Split into 6 equal horizontal slots inside the zone with small padding
				pad = int(0.04 * min(ar.width, ar.height))
				slot_w = max(1, (ar.width - 2 * pad) // 6)
				items: List[str] = []
				for s in range(6):
					sx = ar.x + pad + s * slot_w
					sy = ar.y + pad
					ew = slot_w
					eh = max(1, ar.height - 2 * pad)
					roi = frame[sy : sy + eh, sx : sx + ew]
					detected = self.recognizer.recognize(roi)
					items.append(detected.name)
				# Write results for this zone
				self.output.write_for_zone(idx + 1, items)
				QtWidgets.QToolTip.showText(self.mapToGlobal(event.pos()), f"Зона {idx+1}: {', '.join(items)}")
				break 