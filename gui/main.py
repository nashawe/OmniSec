# gui/main.py

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSlider, QLabel, QFrame, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

from widgets.network_graph_canvas import NetworkGraphCanvas
from widgets.event_feed import EventFeedWidget
from api_client import APIClient


# ---------------------------------------------------------------------------
# Reusable styled button
# ---------------------------------------------------------------------------
class TacticalButton(QPushButton):
    def __init__(self, text, color="#00d4ff", parent=None):
        super().__init__(text, parent)
        self._color = color
        self.setFont(QFont("Courier New", 10, QFont.Bold))
        self.setFixedHeight(34)
        self.setMinimumWidth(80)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(pressed=False)

    def _apply_style(self, pressed=False):
        bg = "#0a1f2e" if not pressed else "#0d2a3e"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {self._color};
                border: 1px solid {self._color};
                border-radius: 3px;
                padding: 4px 14px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: #0d2a3e;
                border: 1px solid {self._color};
            }}
            QPushButton:pressed {{
                background-color: #112233;
            }}
            QPushButton:disabled {{
                color: #1a3a50;
                border-color: #1a3a50;
            }}
        """)


# ---------------------------------------------------------------------------
# Sim time display
# ---------------------------------------------------------------------------
class SimClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        header = QLabel("SIM TIME")
        header.setFont(QFont("Courier New", 8))
        header.setStyleSheet("color: #2a6080; border: none; background: transparent;")

        self._time_label = QLabel("00:00:00")
        self._time_label.setFont(QFont("Courier New", 18, QFont.Bold))
        self._time_label.setStyleSheet("color: #00d4ff; border: none; background: transparent;")

        self._status_label = QLabel("● PAUSED")
        self._status_label.setFont(QFont("Courier New", 8, QFont.Bold))
        self._status_label.setStyleSheet("color: #555577; border: none; background: transparent;")

        layout.addWidget(header)
        layout.addWidget(self._time_label)
        layout.addWidget(self._status_label)

    def update(self, sim_time: float, is_running: bool):
        # Convert sim_time (minutes) to HH:MM:SS display
        total_seconds = int(sim_time * 60)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        self._time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

        if is_running:
            self._status_label.setText("● RUNNING")
            self._status_label.setStyleSheet(
                "color: #00ff88; border: none; background: transparent;"
            )
        else:
            self._status_label.setText("● PAUSED")
            self._status_label.setStyleSheet(
                "color: #555577; border: none; background: transparent;"
            )


# ---------------------------------------------------------------------------
# Resource bar (red or blue team)
# ---------------------------------------------------------------------------
class ResourceBar(QWidget):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        header_row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(QFont("Courier New", 8, QFont.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")

        self._value_label = QLabel("100")
        self._value_label.setFont(QFont("Courier New", 8))
        self._value_label.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        self._value_label.setAlignment(Qt.AlignRight)

        header_row.addWidget(lbl)
        header_row.addStretch()
        header_row.addWidget(self._value_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(100)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #060d18;
                border: 1px solid #0d2a42;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)

        layout.addLayout(header_row)
        layout.addWidget(self._bar)

    def update_value(self, value: float):
        clamped = max(0, min(100, int(value)))
        self._bar.setValue(clamped)
        self._value_label.setText(str(int(value)))


# ---------------------------------------------------------------------------
# Bottom control bar
# ---------------------------------------------------------------------------
class ControlBar(QWidget):
    def __init__(self, api_client: APIClient, parent=None):
        super().__init__(parent)
        self._api = api_client
        self.setFixedHeight(90)
        self.setStyleSheet("""
            QWidget {
                background-color: #060d18;
                border-top: 1px solid #0d2a42;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(20)

        # --- Sim clock ---
        self._clock = SimClockWidget()
        self._clock.setStyleSheet("background: transparent;")

        # --- Divider ---
        def divider():
            d = QFrame()
            d.setFrameShape(QFrame.VLine)
            d.setStyleSheet("color: #0d2a42; background: #0d2a42;")
            d.setFixedWidth(1)
            return d

        # --- Control buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._start_btn  = TacticalButton("▶  START",  color="#00ff88")
        self._pause_btn  = TacticalButton("⏸  PAUSE",  color="#ffaa00")
        self._reset_btn  = TacticalButton("↺  RESET",  color="#ff4444")

        self._start_btn.clicked.connect(self._api.start_simulation)
        self._pause_btn.clicked.connect(self._api.pause_simulation)
        self._reset_btn.clicked.connect(self._api.reset_simulation)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._pause_btn)
        btn_layout.addWidget(self._reset_btn)

        # --- Speed slider ---
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(4)

        speed_header = QLabel("SPEED")
        speed_header.setFont(QFont("Courier New", 8))
        speed_header.setStyleSheet("color: #2a6080; border: none; background: transparent;")

        slider_row = QHBoxLayout()
        self._speed_label = QLabel("1×")
        self._speed_label.setFont(QFont("Courier New", 9, QFont.Bold))
        self._speed_label.setStyleSheet("color: #00d4ff; border: none; background: transparent;")
        self._speed_label.setFixedWidth(28)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(4)
        self._slider.setValue(1)
        self._slider.setFixedWidth(120)
        self._slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #0d2a42;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00d4ff;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #00d4ff;
                border-radius: 2px;
            }
        """)
        self._slider.valueChanged.connect(self._on_speed_change)

        slider_row.addWidget(self._speed_label)
        slider_row.addWidget(self._slider)

        speed_layout.addWidget(speed_header)
        speed_layout.addLayout(slider_row)

        # --- Resource bars ---
        resource_layout = QVBoxLayout()
        resource_layout.setSpacing(6)

        self._red_bar  = ResourceBar("RED TEAM", "#ff4444")
        self._blue_bar = ResourceBar("BLUE TEAM", "#4499ff")

        resource_layout.addWidget(self._red_bar)
        resource_layout.addWidget(self._blue_bar)

        # --- Assemble ---
        layout.addWidget(self._clock)
        layout.addWidget(divider())
        layout.addLayout(btn_layout)
        layout.addWidget(divider())
        layout.addLayout(speed_layout)
        layout.addWidget(divider())
        layout.addLayout(resource_layout)
        layout.addStretch()

    def _on_speed_change(self, value):
        speed_map = {0: 0.5, 1: 1, 2: 2, 3: 5, 4: 10}
        speed = speed_map.get(value, 1)
        self._speed_label.setText(f"{speed}×")
        self._api.set_simulation_speed(speed)

    def on_state_updated(self, snapshot: dict):
        self._clock.update(
            snapshot.get("sim_time", 0.0),
            snapshot.get("is_running", False)
        )
        self._red_bar.update_value(snapshot.get("red_resources", 100))
        self._blue_bar.update_value(snapshot.get("blue_resources", 100))


# ---------------------------------------------------------------------------
# Top header bar
# ---------------------------------------------------------------------------
class HeaderBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QWidget {
                background-color: #040810;
                border-bottom: 1px solid #0d2a42;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("OMNISEC")
        title.setFont(QFont("Courier New", 14, QFont.Bold))
        title.setStyleSheet("color: #00d4ff; letter-spacing: 4px; border: none; background: transparent;")

        subtitle = QLabel("CYBER CONFLICT SIMULATION")
        subtitle.setFont(QFont("Courier New", 8))
        subtitle.setStyleSheet("color: #1a4060; border: none; background: transparent;")

        self._scenario_label = QLabel("SCENARIO: small_business")
        self._scenario_label.setFont(QFont("Courier New", 8))
        self._scenario_label.setStyleSheet("color: #2a6080; border: none; background: transparent;")
        self._scenario_label.setAlignment(Qt.AlignRight)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self._scenario_label)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniSec: Cyber Conflict Simulation")
        self.setGeometry(100, 100, 1600, 960)
        self.setStyleSheet("background-color: #04080f;")

        # --- API client ---
        self.api_client = APIClient()

        # --- Central widget ---
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Header ---
        self._header = HeaderBar()

        # --- Main content area ---
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Network graph canvas (takes most of the space)
        self._canvas = NetworkGraphCanvas()

        # Right sidebar — event feed
        sidebar = QFrame()
        sidebar.setFixedWidth(340)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #04080f;
                border-left: 1px solid #0d2a42;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self._event_feed = EventFeedWidget()
        sidebar_layout.addWidget(self._event_feed)

        content_layout.addWidget(self._canvas, stretch=1)
        content_layout.addWidget(sidebar)

        # --- Bottom control bar ---
        self._control_bar = ControlBar(self.api_client)

        # --- Stack everything ---
        root.addWidget(self._header)
        root.addWidget(content, stretch=1)
        root.addWidget(self._control_bar)

        # --- Wire up WebSocket signal to all components ---
        self.api_client.state_updated.connect(self._canvas.on_state_updated)
        self.api_client.state_updated.connect(self._event_feed.on_state_updated)
        self.api_client.state_updated.connect(self._control_bar.on_state_updated)

        # --- Start WebSocket listener ---
        self.api_client.start_websocket_listener()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())