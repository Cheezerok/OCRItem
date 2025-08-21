from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int


class ROISelectorDialog(QtWidgets.QDialog):
    selection_made = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Dialog
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setModal(True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Fullscreen on the current screen
        desktop = QtWidgets.QApplication.desktop()
        self.setGeometry(desktop.screenGeometry())

        self._origin: Optional[QtCore.QPoint] = None
        self._current: Optional[QtCore.QPoint] = None
        self._selecting: bool = False

        self._overlay_color = QtGui.QColor(0, 0, 0, 80)
        self._selection_pen = QtGui.QPen(QtGui.QColor(0, 200, 255, 255), 2)
        self._selection_brush = QtGui.QBrush(QtGui.QColor(0, 200, 255, 60))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._selecting = True
            self.update()
        elif event.button() == QtCore.Qt.RightButton:
            self.reject()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._selecting:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self._selecting and self._origin and self._current:
            rect = QtCore.QRect(self._origin, self._current).normalized()
            if rect.width() > 4 and rect.height() > 4:
                self.selection_made.emit(Rect(rect.x(), rect.y(), rect.width(), rect.height()))
                self.accept()
            else:
                self.reject()
            self._selecting = False
            self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Q):
            self.reject()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._overlay_color)

        if self._origin and self._current and self._selecting:
            rect = QtCore.QRect(self._origin, self._current).normalized()
            painter.setPen(self._selection_pen)
            painter.setBrush(self._selection_brush)
            painter.drawRect(rect)


def select_roi(parent: Optional[QtWidgets.QWidget] = None) -> Optional[Rect]:
    dlg = ROISelectorDialog(parent)
    result: Optional[Rect] = None

    def _on_sel(r: Rect) -> None:
        nonlocal result
        result = r

    dlg.selection_made.connect(_on_sel)
    dlg.exec_()
    return result 