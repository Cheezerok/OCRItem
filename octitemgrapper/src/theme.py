from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


def apply_dark_theme(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")
    dark_palette = QtGui.QPalette()

    base_color = QtGui.QColor(45, 45, 45)
    alt_base = QtGui.QColor(55, 55, 55)
    text_color = QtGui.QColor(220, 220, 220)
    disabled_text = QtGui.QColor(127, 127, 127)
    button_color = QtGui.QColor(53, 53, 53)
    highlight = QtGui.QColor(42, 130, 218)

    dark_palette.setColor(QtGui.QPalette.Window, base_color)
    dark_palette.setColor(QtGui.QPalette.WindowText, text_color)
    dark_palette.setColor(QtGui.QPalette.Base, alt_base)
    dark_palette.setColor(QtGui.QPalette.AlternateBase, base_color)
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, text_color)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, text_color)
    dark_palette.setColor(QtGui.QPalette.Text, text_color)
    dark_palette.setColor(QtGui.QPalette.Button, button_color)
    dark_palette.setColor(QtGui.QPalette.ButtonText, text_color)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)

    dark_palette.setColor(QtGui.QPalette.Highlight, highlight)
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)

    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabled_text)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabled_text)

    app.setPalette(dark_palette)

    app.setStyleSheet(
        """
        QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
        QListWidget, QTreeWidget, QTableWidget { background-color: #2f2f2f; }
        QPushButton { padding: 5px 10px; }
        QGroupBox { border: 1px solid #3c3c3c; margin-top: 6px; }
        QGroupBox::title { subcontrol-origin: margin; left: 7px; padding: 0 3px 0 3px; }
        QMenuBar { background-color: #2d2d2d; }
        QMenuBar::item:selected { background: #3d3d3d; }
        QMenu { background-color: #2d2d2d; }
        QMenu::item:selected { background: #3d3d3d; }
        """
    ) 