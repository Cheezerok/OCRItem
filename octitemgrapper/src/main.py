from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5  # new: for locating plugins folder

from roi_selector import select_roi, Rect
from capture import ScreenCapturer
from templates_loader import load_templates
from recognizer import ORBItemRecognizer
from output_writer import OutputWriter
from profile import Profile
from theme import apply_dark_theme


@dataclass
class ROIEntry:
    rect: Rect
    label: str = ""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Item OCR (PyQt5)")
        self.resize(1100, 620)

        self.templates_dir: Optional[Path] = None
        self.rois: List[ROIEntry] = []

        self.capturer = ScreenCapturer()
        self.output = OutputWriter(Path.cwd() / "output")
        self.recognizer: Optional[ORBItemRecognizer] = None

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        # Controls row
        controls = QtWidgets.QGridLayout()
        self.btn_load_templates = QtWidgets.QPushButton("Выбрать папку шаблонов…")
        self.lbl_templates = QtWidgets.QLabel("Не выбрано")
        self.btn_add_roi = QtWidgets.QPushButton("Добавить ROI")
        self.btn_remove_roi = QtWidgets.QPushButton("Удалить выбранный")
        self.btn_start = QtWidgets.QPushButton("Старт")
        self.btn_stop = QtWidgets.QPushButton("Стоп")
        self.btn_stop.setEnabled(False)

        # Source selection
        self.combo_source = QtWidgets.QComboBox()
        self.combo_source.addItems(["ROI (ручной выбор)", "Монитор", "Окно"])
        self.combo_detail = QtWidgets.QComboBox()  # will be filled based on source
        self.btn_refresh_sources = QtWidgets.QPushButton("Обновить источники")
        self.btn_overlay = QtWidgets.QPushButton("Разметить окно…")

        controls.addWidget(QtWidgets.QLabel("Шаблоны:"), 0, 0)
        controls.addWidget(self.btn_load_templates, 0, 1)
        controls.addWidget(self.lbl_templates, 0, 2, 1, 3)

        controls.addWidget(QtWidgets.QLabel("Источник:"), 1, 0)
        controls.addWidget(self.combo_source, 1, 1)
        controls.addWidget(self.combo_detail, 1, 2)
        controls.addWidget(self.btn_refresh_sources, 1, 3)
        controls.addWidget(self.btn_overlay, 1, 4)

        controls.addWidget(self.btn_add_roi, 2, 0)
        controls.addWidget(self.btn_remove_roi, 2, 1)
        controls.addWidget(self.btn_start, 2, 2)
        controls.addWidget(self.btn_stop, 2, 3)

        left_layout.addLayout(controls)

        # ROI list
        self.list_rois = QtWidgets.QListWidget()
        left_layout.addWidget(self.list_rois, 1)

        main_layout.addWidget(left, 2)

        # Right panel (preview and thresholds)
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        group_thresh = QtWidgets.QGroupBox("Пороговые значения")
        form = QtWidgets.QFormLayout(group_thresh)
        self.spin_orb = QtWidgets.QSpinBox()
        self.spin_orb.setRange(0, 200)
        self.spin_orb.setValue(8)
        self.dspin_corr = QtWidgets.QDoubleSpinBox()
        self.dspin_corr.setRange(0.0, 1.0)
        self.dspin_corr.setSingleStep(0.05)
        self.dspin_corr.setValue(0.5)
        form.addRow("ORB (good matches):", self.spin_orb)
        form.addRow("Correlation (0-1):", self.dspin_corr)
        right_layout.addWidget(group_thresh)

        self.list_preview = QtWidgets.QListWidget()
        right_layout.addWidget(QtWidgets.QLabel("Последние распознавания:"))
        right_layout.addWidget(self.list_preview, 1)

        # Preview label
        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setFrameShape(QtWidgets.QFrame.Box)
        right_layout.addWidget(QtWidgets.QLabel("Превью источника:"))
        right_layout.addWidget(self.preview_label)

        main_layout.addWidget(right, 1)

        # Status bar
        self.status = self.statusBar()

        # Menu
        file_menu = self.menuBar().addMenu("Файл")
        act_save = file_menu.addAction("Сохранить профиль…")
        act_load = file_menu.addAction("Загрузить профиль…")
        act_overlay = file_menu.addAction("Разметить окно…")

        # Connections
        self.btn_load_templates.clicked.connect(self.on_choose_templates)
        self.btn_add_roi.clicked.connect(self.on_add_roi)
        self.btn_remove_roi.clicked.connect(self.on_remove_roi)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        act_save.triggered.connect(self.on_save_profile)
        act_load.triggered.connect(self.on_load_profile)
        act_overlay.triggered.connect(self.on_open_overlay)
        self.btn_overlay.clicked.connect(self.on_open_overlay)
        self.btn_refresh_sources.clicked.connect(self.refresh_sources)
        self.combo_source.currentIndexChanged.connect(self.refresh_sources)
        self.combo_detail.currentIndexChanged.connect(self.update_preview)

        # Timer for recognition loop
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.on_tick)

        # Populate sources
        self.refresh_sources()
        # Initial preview update
        self.update_preview()

    def refresh_sources(self) -> None:
        self.combo_detail.clear()
        mode = self.combo_source.currentText()
        if mode == "Монитор":
            mons = self.capturer.list_monitors()
            for i, r in enumerate(mons):
                self.combo_detail.addItem(f"Монитор {i+1} ({r.width}x{r.height} @ {r.x},{r.y})", ("monitor", i))
        elif mode == "Окно":
            wins = self.capturer.list_windows()
            for hwnd, title in wins:
                self.combo_detail.addItem(title, ("window", hwnd))
        else:
            self.combo_detail.addItem("Выделяем вручную ROIs", ("roi", None))
        self.update_preview()

    def _grab_selected_source(self) -> Optional[QtGui.QImage]:
        mode_data = self.combo_detail.currentData()
        if not mode_data:
            return None
        mode, val = mode_data
        frame_bgr = None
        if mode == "monitor":
            mons = self.capturer.list_monitors()
            if 0 <= val < len(mons):
                frame_bgr = self.capturer.grab_bgr(mons[val])
        elif mode == "window":
            frame_bgr = self.capturer.grab_window_bgr(val)
        # Convert to QImage
        if frame_bgr is None:
            return None
        h, w, _ = frame_bgr.shape
        rgb = frame_bgr[..., ::-1].copy()
        qimg = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        return qimg.copy()

    def update_preview(self) -> None:
        qimg = self._grab_selected_source()
        if qimg is None:
            self.preview_label.setText("Нет данных для превью")
            return
        pix = QtGui.QPixmap.fromImage(qimg)
        self.preview_label.setPixmap(pix.scaled(self.preview_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update_preview()

    def on_choose_templates(self) -> None:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку с шаблонами", str(Path.cwd() / "templates"))
        if dir_path:
            self.templates_dir = Path(dir_path)
            self.lbl_templates.setText(str(self.templates_dir))
            templates = load_templates(self.templates_dir)
            if not templates:
                QtWidgets.QMessageBox.warning(self, "Пустая папка", "В папке нет изображений шаблонов")
                return
            self.recognizer = ORBItemRecognizer(templates)
            self.status.showMessage("Шаблоны загружены", 3000)

    def on_add_roi(self) -> None:
        if self.combo_source.currentText() != "ROI (ручной выбор)":
            QtWidgets.QMessageBox.information(self, "Источник", "Переключите источник на 'ROI (ручной выбор)' для выделения областей")
            return
        roi = select_roi(self)
        if roi is None:
            return
        entry = ROIEntry(rect=roi, label=f"ROI {len(self.rois)+1}")
        self.rois.append(entry)
        self.refresh_roi_list()

    def on_remove_roi(self) -> None:
        idx = self.list_rois.currentRow()
        if 0 <= idx < len(self.rois):
            del self.rois[idx]
            self.refresh_roi_list()

    def on_start(self) -> None:
        if not self.templates_dir or self.recognizer is None:
            QtWidgets.QMessageBox.warning(self, "Нет шаблонов", "Сначала выберите папку с шаблонами")
            return
        if self.combo_source.currentText() == "ROI (ручной выбор)" and not self.rois:
            QtWidgets.QMessageBox.warning(self, "Нет ROIs", "Добавьте хотя бы один ROI")
            return
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.timer.start()
        self.status.showMessage("Запущено", 2000)

    def on_stop(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if self.timer.isActive():
            self.timer.stop()
        self.status.showMessage("Остановлено", 2000)

    def refresh_roi_list(self) -> None:
        self.list_rois.clear()
        for i, entry in enumerate(self.rois, start=1):
            r = entry.rect
            item_text = f"{i}. {entry.label}  [x={r.x}, y={r.y}, w={r.width}, h={r.height}]"
            self.list_rois.addItem(item_text)

    def on_tick(self) -> None:
        if self.recognizer is None:
            return
        mode = self.combo_source.currentText()
        items: List[str] = []
        self.list_preview.clear()
        try:
            if mode == "ROI (ручной выбор)":
                for entry in self.rois:
                    frame = self.capturer.grab_bgr(entry.rect)
                    detected = self.recognizer.recognize(frame)
                    name = self._apply_thresholds(detected.score, detected.method, detected.name)
                    items.append(name)
                    self.list_preview.addItem(
                        f"{entry.label}: {name} (method={detected.method}, score={detected.score:.2f})"
                    )
            else:
                # Full-frame recognition yields best-matching item name for the whole source
                qimg = self._grab_selected_source()
                if qimg is not None:
                    frame = self._qimage_to_bgr(qimg)
                    detected = self.recognizer.recognize(frame)
                    name = self._apply_thresholds(detected.score, detected.method, detected.name)
                    items.append(name)
                    self.list_preview.addItem(
                        f"Источник: {name} (method={detected.method}, score={detected.score:.2f})"
                    )
            self.output.write(items)
            self.status.showMessage("Обновлено: " + ", ".join(items), 500)
        except Exception as e:
            self.status.showMessage(f"Ошибка: {e}", 2000)
        self.update_preview()

    def _qimage_to_bgr(self, img: QtGui.QImage) -> QtGui.QImage:
        img = img.convertToFormat(QtGui.QImage.Format_RGB888)
        w = img.width()
        h = img.height()
        ptr = img.bits()
        ptr.setsize(h * w * 3)
        arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 3))
        return arr[:, :, ::-1].copy()

    def _apply_thresholds(self, score: float, method: str, name: str) -> str:
        if method == "orb":
            if score < float(self.spin_orb.value()):
                return "Unknown"
        else:
            if score < float(self.dspin_corr.value()):
                return "Unknown"
        return name

    def on_save_profile(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить профиль", str(Path.cwd() / "profile.json"), "JSON (*.json)")
        if not path_str:
            return
        prof = Profile(templates_dir=str(self.templates_dir or ""), rois=[e.rect for e in self.rois])
        prof.to_file(Path(path_str))
        self.status.showMessage("Профиль сохранён", 3000)

    def on_load_profile(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Загрузить профиль", str(Path.cwd()), "JSON (*.json)")
        if not path_str:
            return
        prof = Profile.from_file(Path(path_str))
        self.templates_dir = Path(prof.templates_dir) if prof.templates_dir else None
        if self.templates_dir and self.templates_dir.exists():
            self.lbl_templates.setText(str(self.templates_dir))
            templates = load_templates(self.templates_dir)
            if templates:
                self.recognizer = ORBItemRecognizer(templates)
        self.rois = [ROIEntry(rect=r, label=f"ROI {i+1}") for i, r in enumerate(prof.rois)]
        self.refresh_roi_list()
        self.status.showMessage("Профиль загружен", 3000)

    def on_open_overlay(self) -> None:
        if self.recognizer is None:
            QtWidgets.QMessageBox.warning(self, "Нет шаблонов", "Сначала выберите папку с шаблонами")
            return
        wins = self.capturer.list_windows()
        if not wins:
            QtWidgets.QMessageBox.information(self, "Окна", "Окна не найдены")
            return
        items = [f"{title} (hwnd={hwnd})" for hwnd, title in wins]
        item, ok = QtWidgets.QInputDialog.getItem(self, "Выберите окно", "Окно:", items, 0, False)
        if not ok or not item:
            return
        idx = items.index(item)
        hwnd = wins[idx][0]
        # Use default MLBB-like 10-zone template
        from window_overlay import WindowZonesOverlay
        from zone_template import mlbb_scoreboard_10
        frame = self.capturer.grab_window_bgr(hwnd)
        if frame is None:
            QtWidgets.QMessageBox.warning(self, "Захват окна", "Не удалось захватить окно")
            return
        _h, _w, _ = frame.shape
        zones = mlbb_scoreboard_10()
        dlg = WindowZonesOverlay(hwnd, zones, self.capturer, self.recognizer, self.output, self)
        dlg.resize(900, 500)
        dlg.exec_()


def _set_qt_plugin_env() -> None:
    try:
        base = Path(PyQt5.__file__).parent
        candidates = [base / "Qt5" / "plugins", base / "Qt" / "plugins"]
        for c in candidates:
            if c.exists():
                os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(c))
                os.environ.setdefault("QT_PLUGIN_PATH", str(c))
                break
    except Exception:
        pass
    try:
        plugins_path = QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath)
        if plugins_path and Path(plugins_path).exists():
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugins_path))
            os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_path))
    except Exception:
        pass


def main() -> None:
    _set_qt_plugin_env()
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_theme(app)
    try:
        for env_key in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_PLUGIN_PATH"):
            p = os.environ.get(env_key)
            if p and Path(p).exists():
                QtWidgets.QApplication.addLibraryPath(str(p))
    except Exception:
        pass

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 