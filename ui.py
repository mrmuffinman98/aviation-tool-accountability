# ui.py
# PyQt6 touchscreen UI for the Aviation Tool Accountability System.
#
# Run:  python ui.py
#
# Tab 1 — Capture: day-to-day tool scanning workflow
# Tab 2 — Setup:  tunable parameters, calibration, ArUco marker generation

import importlib
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, QByteArray, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget,
)

import compose
import config
import export
import process
import vectorize

_STEP_LABELS = ["Raw Photo", "Undistorted", "Thresholded", "Vectorized"]
_PLACEHOLDER_BG = "#1e1e1e"
_BTN_HEIGHT = 72


# ---------------------------------------------------------------------------
# Image conversion helpers
# ---------------------------------------------------------------------------

def _cv2_to_pixmap(image: np.ndarray, w: int, h: int) -> QPixmap:
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
    ih, iw, ch = rgb.shape
    qimg = QImage(rgb.tobytes(), iw, ih, ch * iw, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _svg_to_pixmap(svg_content: str, w: int, h: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_content.encode()))
    qimg = QImage(w, h, QImage.Format.Format_ARGB32)
    qimg.fill(Qt.GlobalColor.white)
    painter = QPainter(qimg)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(qimg)


# ---------------------------------------------------------------------------
# Background pipeline worker
# ---------------------------------------------------------------------------

class PipelineWorker(QThread):
    """Runs the capture → process → vectorize → session pipeline off the UI thread."""

    step_update = pyqtSignal(int, object)  # (step_index 0-3, np.ndarray or svg str)
    tool_saved  = pyqtSignal(int)          # total tools in session after save
    error       = pyqtSignal(str)

    def __init__(self, image_path: str | None = None, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def run(self) -> None:
        try:
            # Step 0 — Capture
            if self.image_path is None:
                from capture import capture_image
                self.image_path = capture_image()

            raw = cv2.imread(self.image_path)
            if raw is None:
                raise FileNotFoundError(f"Could not load image: {self.image_path}")
            self.step_update.emit(0, raw.copy())

            # Step 1 — Undistort + crop
            undistorted = process.undistort(raw)
            undistorted = process.crop(undistorted)
            self.step_update.emit(1, undistorted.copy())

            # Step 2 — Silhouette extraction
            binary_mask, _, pixels_per_mm = process.extract_silhouette(undistorted)
            self.step_update.emit(2, binary_mask.copy())

            # Step 3 — Vectorize
            svg_content = vectorize.bitmap_to_svg_string(binary_mask)
            self.step_update.emit(3, svg_content)

            # Save to session
            export.svg_to_session(svg_content, pixels_per_mm)

            session_dir = Path(config.SESSION_PATH)
            count = len(list(session_dir.glob("tool_*.json")))
            self.tool_saved.emit(count)

        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Preview panel — 2×2 grid of labeled image slots
# ---------------------------------------------------------------------------

class PreviewPanel(QWidget):

    _PREVIEW_W = 420
    _PREVIEW_H = 290

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QGridLayout
        grid = QGridLayout(self)
        grid.setSpacing(10)

        self._slots: list[QLabel] = []
        for i, title in enumerate(_STEP_LABELS):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setSpacing(3)
            vbox.setContentsMargins(0, 0, 0, 0)

            header = QLabel(f"Step {i + 1}: {title}")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setFont(QFont("monospace", 9))
            vbox.addWidget(header)

            slot = QLabel()
            slot.setFixedSize(self._PREVIEW_W, self._PREVIEW_H)
            slot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.setStyleSheet(
                f"background: {_PLACEHOLDER_BG}; border-radius: 6px; color: #555;"
            )
            slot.setText("—")
            vbox.addWidget(slot)

            self._slots.append(slot)
            grid.addWidget(container, i // 2, i % 2)

    def update_step(self, step_index: int, data: object) -> None:
        slot = self._slots[step_index]
        w, h = self._PREVIEW_W, self._PREVIEW_H
        if isinstance(data, np.ndarray):
            px = _cv2_to_pixmap(data, w, h)
        else:
            px = _svg_to_pixmap(data, w, h)
        slot.setPixmap(px)

    def clear(self) -> None:
        for slot in self._slots:
            slot.clear()
            slot.setText("—")
            slot.setStyleSheet(
                f"background: {_PLACEHOLDER_BG}; border-radius: 6px; color: #555;"
            )


# ---------------------------------------------------------------------------
# Capture tab
# ---------------------------------------------------------------------------

class CaptureTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: PipelineWorker | None = None
        self._build_ui()
        self._refresh_session()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Preview grid
        self.preview = PreviewPanel()
        layout.addWidget(self.preview)

        # Session list
        session_box = QGroupBox("Current Session")
        session_vbox = QVBoxLayout(session_box)
        self.session_list = QListWidget()
        self.session_list.setMaximumHeight(80)
        self.session_list.setFlow(QListWidget.Flow.LeftToRight)
        self.session_list.setWrapping(False)
        self.session_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        session_vbox.addWidget(self.session_list)
        layout.addWidget(session_box)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_capture  = self._btn("Capture",          "#2e7d32", self._on_capture)
        self.btn_recapture = self._btn("Recapture",       "#e65100", self._on_recapture)
        self.btn_complete = self._btn("Complete Session",  "#1565c0", self._on_complete)
        self.btn_new      = self._btn("New Session",       "#4a148c", self._on_new)
        for b in [self.btn_capture, self.btn_recapture, self.btn_complete, self.btn_new]:
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        # Status
        self.status = QLabel("Ready — place a tool under the camera and press Capture.")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("sans-serif", 10))
        layout.addWidget(self.status)

    @staticmethod
    def _btn(label: str, color: str, slot) -> QPushButton:
        b = QPushButton(label)
        b.setMinimumHeight(_BTN_HEIGHT)
        b.setFont(QFont("sans-serif", 13, QFont.Weight.Bold))
        b.setStyleSheet(
            f"QPushButton {{ background:{color}; color:white; border-radius:6px; }}"
            "QPushButton:disabled { background:#444; color:#777; }"
        )
        b.clicked.connect(slot)
        return b

    def _set_all_enabled(self, enabled: bool) -> None:
        for b in [self.btn_capture, self.btn_recapture, self.btn_complete, self.btn_new]:
            b.setEnabled(enabled)

    def _refresh_session(self) -> None:
        self.session_list.clear()
        session_dir = Path(config.SESSION_PATH)
        files = sorted(session_dir.glob("tool_*.json")) if session_dir.exists() else []
        for f in files:
            with open(f) as fh:
                d = json.load(fh)
            item = QListWidgetItem(
                f"  Tool {d['index']}  \n  {d['width_mm']:.0f}×{d['height_mm']:.0f} mm  "
            )
            self.session_list.addItem(item)
        has = bool(files)
        self.btn_recapture.setEnabled(has)
        self.btn_complete.setEnabled(has)

    def _start_worker(self, image_path: str | None = None) -> None:
        self._set_all_enabled(False)
        self.preview.clear()
        self.status.setText("Processing…")
        self._worker = PipelineWorker(image_path=image_path)
        self._worker.step_update.connect(self._on_step)
        self._worker.tool_saved.connect(self._on_saved)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # --- Button handlers ---

    def _on_capture(self) -> None:
        self._start_worker()

    def _on_recapture(self) -> None:
        session_dir = Path(config.SESSION_PATH)
        files = sorted(session_dir.glob("tool_*.json"))
        if files:
            files[-1].unlink()
        self._start_worker()

    def _on_complete(self) -> None:
        try:
            svg_path = compose.compose_shadowboard()
            QMessageBox.information(
                self, "Session Complete",
                f"Shadowboard SVG saved:\n\n{svg_path}\n\nOpen it in Inkscape to arrange and prepare for cutting."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _on_new(self) -> None:
        reply = QMessageBox.question(
            self, "New Session",
            "Clear the current session and start over?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            session_dir = Path(config.SESSION_PATH)
            if session_dir.exists():
                shutil.rmtree(session_dir)
            self.preview.clear()
            self._refresh_session()
            self.status.setText("Session cleared — ready for a new drawer.")

    # --- Worker signal handlers ---

    def _on_step(self, step_index: int, data: object) -> None:
        self.preview.update_step(step_index, data)
        self.status.setText(f"Step {step_index + 1} / 4 — {_STEP_LABELS[step_index]}…")

    def _on_saved(self, count: int) -> None:
        self._refresh_session()
        self._set_all_enabled(True)
        self.status.setText(
            f"Tool {count} captured successfully.  "
            f"Session total: {count}.  Place next tool and press Capture."
        )

    def _on_error(self, message: str) -> None:
        self._set_all_enabled(True)
        self._refresh_session()
        self.status.setText("Error — see dialog.")
        QMessageBox.critical(self, "Pipeline Error", message)


# ---------------------------------------------------------------------------
# Setup tab
# ---------------------------------------------------------------------------

class SetupTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)

        # --- Image capture ---
        cap_box = QGroupBox("Image Capture")
        cap_form = QFormLayout(cap_box)

        self.lens_spin = QDoubleSpinBox()
        self.lens_spin.setRange(0.0, 20.0)
        self.lens_spin.setSingleStep(0.5)
        self.lens_spin.setToolTip("0 = infinity focus. ~8 suits a ~20 cm working distance.")
        cap_form.addRow("Lens Position:", self.lens_spin)

        self.crop_x = QSpinBox(); self.crop_x.setRange(0, 9999)
        self.crop_y = QSpinBox(); self.crop_y.setRange(0, 9999)
        self.crop_w = QSpinBox(); self.crop_w.setRange(1, 9999)
        self.crop_h = QSpinBox(); self.crop_h.setRange(1, 9999)
        crop_row = QHBoxLayout()
        for lbl, spin in [("x:", self.crop_x), ("y:", self.crop_y),
                           ("w:", self.crop_w), ("h:", self.crop_h)]:
            crop_row.addWidget(QLabel(lbl))
            crop_row.addWidget(spin)
        cap_form.addRow("Crop Bounds (px):", crop_row)

        layout.addWidget(cap_box)

        # --- ArUco ---
        aruco_box = QGroupBox("ArUco Scale Marker")
        aruco_form = QFormLayout(aruco_box)

        self.aruco_dict = QComboBox()
        self.aruco_dict.addItems([
            "DICT_4X4_50", "DICT_4X4_100", "DICT_5X5_50",
            "DICT_5X5_100", "DICT_6X6_50", "DICT_ARUCO_ORIGINAL",
        ])
        aruco_form.addRow("Dictionary:", self.aruco_dict)

        self.aruco_id = QSpinBox()
        self.aruco_id.setRange(0, 249)
        aruco_form.addRow("Marker ID:", self.aruco_id)

        self.aruco_size = QDoubleSpinBox()
        self.aruco_size.setRange(1.0, 500.0)
        self.aruco_size.setSuffix(" mm")
        self.aruco_size.setToolTip("Physical side length of your printed ArUco marker.")
        aruco_form.addRow("Marker Size:", self.aruco_size)

        btn_aruco = QPushButton("Generate ArUco Marker")
        btn_aruco.setMinimumHeight(50)
        btn_aruco.clicked.connect(self._on_gen_aruco)
        aruco_form.addRow(btn_aruco)

        layout.addWidget(aruco_box)

        # --- Silhouette detection ---
        sil_box = QGroupBox("Silhouette Detection")
        sil_form = QFormLayout(sil_box)

        self.threshold = QSpinBox()
        self.threshold.setRange(0, 255)
        self.threshold.setToolTip(
            "Pixels darker than this are treated as tool. "
            "Raise if background bleeds in; lower if tool is missed."
        )
        sil_form.addRow("Threshold Value (0–255):", self.threshold)

        self.min_area = QSpinBox()
        self.min_area.setRange(0, 999999)
        self.min_area.setSingleStep(500)
        self.min_area.setToolTip("Contours smaller than this (px²) are ignored as noise.")
        sil_form.addRow("Min Contour Area (px²):", self.min_area)

        layout.addWidget(sil_box)

        # --- Camera calibration ---
        cal_box = QGroupBox("Camera Calibration")
        cal_vbox = QVBoxLayout(cal_box)
        cal_vbox.addWidget(QLabel(
            "Run once using a printed checkerboard pattern.\n"
            "Calibration results are written directly into config.py."
        ))
        btn_cal = QPushButton("Run Camera Calibration")
        btn_cal.setMinimumHeight(50)
        btn_cal.clicked.connect(self._on_calibrate)
        cal_vbox.addWidget(btn_cal)
        layout.addWidget(cal_box)

        # --- Output paths ---
        out_box = QGroupBox("Output Paths")
        out_form = QFormLayout(out_box)
        self.svg_out = QLineEdit()
        self.session_path = QLineEdit()
        out_form.addRow("SVG Output Folder:", self.svg_out)
        out_form.addRow("Session Folder:", self.session_path)
        layout.addWidget(out_box)

        # --- Save ---
        self.save_note = QLabel("")
        self.save_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.save_note)

        btn_save = QPushButton("Save Settings")
        btn_save.setMinimumHeight(60)
        btn_save.setFont(QFont("sans-serif", 12, QFont.Weight.Bold))
        btn_save.setStyleSheet(
            "QPushButton { background:#1565c0; color:white; border-radius:6px; }"
        )
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)

        layout.addStretch()

    def _load_settings(self) -> None:
        s = config.load_settings()
        self.lens_spin.setValue(s["lens_position"])
        cb = s["crop_bounds"]
        self.crop_x.setValue(cb[0]); self.crop_y.setValue(cb[1])
        self.crop_w.setValue(cb[2]); self.crop_h.setValue(cb[3])
        idx = self.aruco_dict.findText(s["aruco_dict_name"])
        if idx >= 0:
            self.aruco_dict.setCurrentIndex(idx)
        self.aruco_id.setValue(s["aruco_marker_id"])
        self.aruco_size.setValue(s["aruco_marker_size_mm"])
        self.threshold.setValue(s["threshold_value"])
        self.min_area.setValue(s["contour_min_area"])
        self.svg_out.setText(s["svg_output_path"])
        self.session_path.setText(s["session_path"])

    def _on_save(self) -> None:
        config.save_settings({
            "lens_position":       self.lens_spin.value(),
            "crop_bounds":         [
                self.crop_x.value(), self.crop_y.value(),
                self.crop_w.value(), self.crop_h.value(),
            ],
            "aruco_dict_name":     self.aruco_dict.currentText(),
            "aruco_marker_id":     self.aruco_id.value(),
            "aruco_marker_size_mm": self.aruco_size.value(),
            "threshold_value":     self.threshold.value(),
            "contour_min_area":    self.min_area.value(),
            "svg_output_path":     self.svg_out.text(),
            "session_path":        self.session_path.text(),
        })
        # Reload config so changes take effect on the next capture.
        importlib.reload(config)
        self.save_note.setText("Settings saved — changes take effect on the next capture.")
        self.save_note.setStyleSheet("color: #2e7d32; font-weight: bold;")

    def _on_gen_aruco(self) -> None:
        import subprocess
        try:
            subprocess.Popen([sys.executable, "generate_aruco_marker.py"])
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _on_calibrate(self) -> None:
        import subprocess
        try:
            subprocess.Popen([sys.executable, "camera_calibration.py"])
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aviation Tool Accountability System")
        self.setMinimumSize(960, 860)

        tabs = QTabWidget()
        tabs.setFont(QFont("sans-serif", 11))
        self.capture_tab = CaptureTab()
        tabs.addTab(self.capture_tab, "  Capture  ")
        tabs.addTab(SetupTab(),       "  Setup    ")
        self.setCentralWidget(tabs)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
