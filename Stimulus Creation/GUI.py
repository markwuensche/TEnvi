# tunnel_gui.py (with corrected video export to match batch_exporter)
import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QFileDialog, QFormLayout, QVBoxLayout, QSizePolicy,
    QSpinBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
import cv2
import numpy as np
from tunnel_module import (
    create_renderer,
    default_params,
    compute_render_resolution,
    export_video,
)

class TunnelGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tunnel Stimulus Control Panel")
        self.params = default_params()
        # GUI-specific parameters
        self.params['show_camera_marker'] = True
        self.params['paused'] = False
        self.params['motion_blur'] = False
        self.params['blur_samples'] = 5

        # Initialize renderer and camera position
        self.renderer = create_renderer(self.params)
        self.cam_z = 0.0
        self.playback_offset = 0.0
        self.playback_start_time = time.perf_counter()
        self.last_update_time = self.playback_start_time
        self._smoothed_dt = None

        # Setup UI and timer
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(int(1000 / self.params['fps']))

    def initUI(self):
        layout = QHBoxLayout(self)

        # Preview area
        self.preview_label = QLabel(self)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.update_preview_size()
        self.preview_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.preview_label)

        # Control widgets
        controls = self.create_controls()
        layout.addLayout(controls)
        layout.addStretch()

    def resizeEvent(self, event):
        self.update_preview_size()
        super().resizeEvent(event)

    def create_controls(self):
        layout = QFormLayout()

        preset_resolutions = {
            "3840 x 2160 (4K)": (3840, 2160),
            "2560 x 1440 (QHD)": (2560, 1440),
            "1920 x 1080 (FHD)": (1920, 1080),
            "1280 x 720 (HD)": (1280, 720),
            "960 x 960 (Square)": (960, 960),
            "Custom": None,
        }

        def add_float_spin(label, key, minv, maxv, step):
            spin = QDoubleSpinBox()
            spin.setRange(minv, maxv)
            spin.setSingleStep(step)
            spin.setKeyboardTracking(False)
            spin.setDecimals(3)
            spin.setValue(self.params[key])
            spin.valueChanged.connect(lambda val: self.update_param(key, val, spin))
            layout.addRow(QLabel(label), spin)

        def add_dropdown(label, key, options):
            combo = QComboBox()
            combo.addItems(options)
            combo.setCurrentText(str(self.params[key]))
            combo.currentTextChanged.connect(lambda val: self.update_param(key, val))
            layout.addRow(QLabel(label), combo)

        def add_int_spin(label, key, minv, maxv, step=1):
            spin = QSpinBox()
            spin.setRange(minv, maxv)
            spin.setSingleStep(step)
            spin.setValue(int(self.params[key]))
            spin.valueChanged.connect(lambda val: self.update_param(key, int(val), spin))
            layout.addRow(QLabel(label), spin)

        def add_checkbox(label, key):
            box = QCheckBox(label)
            box.setChecked(self.params[key])
            box.stateChanged.connect(lambda val: self.update_param(key, bool(val)))
            layout.addRow(box)

        def add_resolution_selector():
            container = QWidget()
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)

            combo = QComboBox()
            combo.addItems(list(preset_resolutions.keys()))

            width_spin = QSpinBox()
            width_spin.setRange(320, 8192)
            width_spin.setSingleStep(8)
            width_spin.setValue(int(self.params['resolution'][0]))

            height_spin = QSpinBox()
            height_spin.setRange(320, 8192)
            height_spin.setSingleStep(8)
            height_spin.setValue(int(self.params['resolution'][1]))

            def apply_preset(name):
                target = preset_resolutions.get(name)
                if target is None:
                    width_spin.setEnabled(True)
                    height_spin.setEnabled(True)
                    self.update_param('resolution', (width_spin.value(), height_spin.value()))
                else:
                    width_spin.setEnabled(False)
                    height_spin.setEnabled(False)
                    width_spin.blockSignals(True)
                    height_spin.blockSignals(True)
                    width_spin.setValue(target[0])
                    height_spin.setValue(target[1])
                    width_spin.blockSignals(False)
                    height_spin.blockSignals(False)
                    self.update_param('resolution', target)
                self.update_preview_size()

            def on_spin_change():
                if combo.currentText() != 'Custom':
                    combo.blockSignals(True)
                    combo.setCurrentText('Custom')
                    combo.blockSignals(False)
                self.update_param('resolution', (width_spin.value(), height_spin.value()))
                self.update_preview_size()

            combo.currentTextChanged.connect(apply_preset)
            width_spin.valueChanged.connect(lambda _v: on_spin_change())
            height_spin.valueChanged.connect(lambda _v: on_spin_change())

            # Initialize preset selection based on current params
            current_resolution = tuple(self.params.get('resolution', (1920, 1080)))
            for name, res in preset_resolutions.items():
                if res == current_resolution:
                    combo.setCurrentText(name)
                    break
            apply_preset(combo.currentText())

            row.addWidget(combo)
            row.addWidget(width_spin)
            row.addWidget(height_spin)
            container.setLayout(row)
            layout.addRow(QLabel("Video Resolution"), container)
        # Numeric parameters
        add_resolution_selector()
        add_float_spin("Tunnel Width", 'tunnel_width', 0.1, 100.0, 0.1)
        add_float_spin("Tunnel Height", 'tunnel_height', 0.1, 100.0, 0.1)
        add_float_spin("Segment Length", 'segment_length', 0.1, 100.0, 0.5)
        add_float_spin("Duration (s)", 'duration', 0.1, 600.0, 1.0)
        add_float_spin("Speed", 'speed', 0.1, 100.0, 0.5)
        add_float_spin("FPS", 'fps', 10, 240, 1)
        add_float_spin("FOV Y (deg)", 'fovy', 5.0, 120.0, 1.0)
        add_float_spin("Tunnel Depth", 'tunnel_depth', 1.0, 10000.0, 10.0)
        add_float_spin("Back Plane Color", 'back_plane_color', 0.0, 1.0, 0.05)
        add_checkbox("Auto Back Color", 'auto_back_plane_color')
        add_float_spin("Contrast", 'brightness_contrast', 0.0, 5.0, 0.1)

        # Dropdown parameters
        add_dropdown("Depth Markers", 'depth_markers', ['none', 'wireframe', 'shaded', 'both'])
        add_dropdown("Color Mode", 'color_mode', ['color', 'bw'])
        add_dropdown("Brightness Mode", 'segment_brightness', ['alternating', 'random', 'monotonous'])
        add_dropdown("Color Palette", 'color_palette', ['orange', 'cyan', 'lime', 'pink', 'white', 'red', 'blue', 'yellow', 'teal', 'peach'])
        add_dropdown("Renderer Backend", 'renderer_backend', ['software', 'moderngl'])

        # Checkbox parameters
        add_checkbox("Recycle Loop", 'recycle_loop')
        add_checkbox("Show Camera Marker", 'show_camera_marker')
        add_checkbox("Enable Motion Blur", 'motion_blur')
        add_float_spin("Blur Samples", 'blur_samples', 1, 20, 1)
        add_checkbox("Square Format", 'square')
        add_checkbox("Fade to Back", 'fade_to_back')
        add_float_spin("Fade Start Distance", 'fade_to_back_start', 0.0, 5000.0, 1.0)
        add_float_spin("Fade End Distance", 'fade_to_back_end', 0.1, 5000.0, 1.0)
        add_int_spin("Temporal Oversample", 'temporal_oversample', 1, 16)

        # Action buttons
        export_btn = QPushButton("Export Current Frame")
        export_btn.clicked.connect(self.export_frame)
        layout.addRow(export_btn)

        video_btn = QPushButton("Export MP4 Video")
        video_btn.clicked.connect(self.export_video)
        layout.addRow(video_btn)

        pause_btn = QPushButton("Pause / Resume Preview")
        pause_btn.clicked.connect(self.toggle_pause)
        layout.addRow(pause_btn)

        return layout

    def update_preview_size(self):
        """Adjust preview label based on screen size and render aspect."""
        width, height = compute_render_resolution(self.params)
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        max_height = int(screen_geo.height() * 0.8)
        max_width = int(screen_geo.width() * 0.6)
        aspect = width / height
        display_width = min(max_width, int(max_height * aspect))
        display_height = int(display_width / aspect)
        self.preview_label.setFixedSize(display_width, display_height)

    def update_param(self, key, value, spin_widget=None):
        previous_value = self.params.get(key)
        self.params[key] = value
        if key == 'fps':
            self.timer.start(int(1000 / self.params['fps']))
        if key in {'square', 'resolution'}:
            self.update_preview_size()
        if key == 'color_palette':
            palette_rgb = {
                'orange': (1.0, 0.4, 0.2),
                'cyan': (0.0, 1.0, 1.0),
                'lime': (0.7, 1.0, 0.0),
                'pink': (1.0, 0.4, 0.7),
                'white': (1.0, 1.0, 1.0),
                'red': (1.0, 0.1, 0.1),
                'blue': (0.2, 0.2, 1.0),
                'yellow': (1.0, 1.0, 0.0),
                'teal': (0.0, 0.7, 0.6),
                'peach': (1.0, 0.8, 0.6),
            }
            self.params['color_rgb'] = palette_rgb[value]
        try:
            if key == 'renderer_backend':
                self.recreate_renderer()
            else:
                self.renderer.reinitialize(self.params)
        except ValueError as exc:
            print(f"Parameter error: {exc}")
            # Revert to previous value when validation fails
            self.params[key] = previous_value
            if spin_widget is not None and previous_value is not None:
                spin_widget.blockSignals(True)
                spin_widget.setValue(previous_value)
                spin_widget.blockSignals(False)
            return
        self.reset_playback()

    def update_frame(self):
        now = time.perf_counter()
        raw_dt = now - self.last_update_time
        self.last_update_time = now

        if self.params.get('paused'):
            self._smoothed_dt = None
            return

        if raw_dt <= 0:
            return

        if self.playback_start_time is None:
            self.playback_start_time = now

        elapsed = now - self.playback_start_time
        self.cam_z = self.playback_offset + self.params['speed'] * elapsed

        if self._smoothed_dt is None:
            self._smoothed_dt = raw_dt
        else:
            self._smoothed_dt = (0.9 * self._smoothed_dt) + (0.1 * raw_dt)

        max_dt = 0.25
        dt = min(self._smoothed_dt, max_dt)
        try:
            self.renderer.params.update(self.params)
            # Motion blur averaging
            if self.params.get('motion_blur'):
                samples = int(self.params.get('blur_samples', 5))
                samples = max(1, samples)
                distance_per_sample = (self.params['speed'] * dt) / samples
                frames = []
                for i in range(samples):
                    offset = (samples - 1 - i) * distance_per_sample
                    frames.append(self.renderer.render_frame(self.cam_z - offset).astype(np.float32))
                frame = np.clip(np.mean(frames, axis=0), 0, 255).astype(np.uint8)
            else:
                frame = self.renderer.render_frame(self.cam_z).copy()

            # Draw camera marker
            if self.params.get('show_camera_marker'):
                center = (frame.shape[1] // 2, frame.shape[0] // 2)
                cv2.line(frame, (center[0] - 10, center[1]), (center[0] + 10, center[1]), (0, 0, 255), 2)
                cv2.line(frame, (center[0], center[1] - 10), (center[0], center[1] + 10), (0, 0, 255), 2)

            # Convert BGR frame returned by the renderer to RGB for Qt
            bgr = frame
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(
                rgb.data,
                rgb.shape[1], rgb.shape[0],
                rgb.shape[1] * rgb.shape[2],
                QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimg).scaled(
                self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            print("Render failed:", e)

    def export_frame(self):
        """Save the current frame to disk with correct color conversion."""
        try:
            frame_bgr = self.renderer.render_frame(self.cam_z).copy()
            path, _ = QFileDialog.getSaveFileName(self, "Save Frame", "frame.png", "Images (*.png *.jpg)")
            if not path:
                return
            if not (path.lower().endswith(".png") or path.lower().endswith(".jpg")):
                path += ".png"

            ext = '.png' if path.lower().endswith('.png') else '.jpg'
            result, encoded = cv2.imencode(ext, frame_bgr)
            if result:
                with open(path, 'wb') as f:
                    f.write(encoded.tobytes())
                print(f"✅ Frame successfully saved to {path}")
            else:
                print("❌ Failed to encode image.")
        except Exception as e:
            print("Export failed:", e)

    def export_video(self):
        """Export a full MP4 video using the shared GUI pipeline."""
        try:
            final_filename, _ = export_video(self.params)
        except FileNotFoundError as exc:
            print(f"❌ {exc}")
            return
        except Exception as exc:
            print(f"❌ Failed to export video: {exc}")
            return

        # Recreate the preview renderer to restore a valid OpenGL context after export
        self.recreate_renderer()
        self.reset_playback()

        print(f"✅ Saved final MP4 (near-lossless H.264 + silent audio) to {final_filename}")

    def toggle_pause(self):
        """Toggle preview pause/resume."""
        self.params['paused'] = not self.params['paused']
        if self.params['paused']:
            self.playback_offset = self.cam_z
            self.playback_start_time = None
        else:
            self.playback_start_time = time.perf_counter()
            self.last_update_time = self.playback_start_time
            self._smoothed_dt = None
        print("Paused" if self.params['paused'] else "Resumed")

    def recreate_renderer(self):
        if getattr(self, 'renderer', None) is not None:
            try:
                self.renderer.release()
            except Exception:
                pass
        self.renderer = create_renderer(self.params)

    def reset_playback(self):
        self.cam_z = 0.0
        self.playback_offset = 0.0
        self.playback_start_time = time.perf_counter()
        self.last_update_time = self.playback_start_time
        self._smoothed_dt = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TunnelGUI()
    window.resize(1200, 900)
    window.show()
    sys.exit(app.exec_())
    