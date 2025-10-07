# gui/main.py

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt

from widgets.simulation_controls import SimulationControlsWidget
from api_client import APIClient

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniSec: Cyber Conflict Simulation")
        self.setGeometry(100, 100, 1600, 900)
        self.api_client = APIClient()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        network_graph_placeholder = self._create_placeholder("Network Graph Canvas", "#3498db")
        main_layout.addWidget(network_graph_placeholder, stretch=3)
        sidebar_layout = QVBoxLayout()
        inspector_panel_placeholder = self._create_placeholder("Node Inspector / Team Status", "#2ecc71")
        event_feed_placeholder = self._create_placeholder("Event Feed", "#f1c40f")
        self.simulation_controls = SimulationControlsWidget()
        sidebar_layout.addWidget(inspector_panel_placeholder, stretch=2)
        sidebar_layout.addWidget(event_feed_placeholder, stretch=3)
        sidebar_layout.addWidget(self.simulation_controls, stretch=1)
        main_layout.addLayout(sidebar_layout, stretch=1)
        
        # --- CONNECT SIGNALS TO HANDLERS ---
        # We now connect the signals to new handler methods within this class.
        self.simulation_controls.start_clicked.connect(self.handle_start_click)
        self.simulation_controls.pause_clicked.connect(self.api_client.pause_simulation)
        self.simulation_controls.reset_clicked.connect(self.api_client.reset_simulation)
        self.simulation_controls.speed_changed.connect(self.api_client.set_simulation_speed)

    # --- TRACER HANDLER ---
    def handle_start_click(self):
        print("[2] MainWindow: Received start_clicked signal from controls widget.")
        print("[3] MainWindow: Calling self.api_client.start_simulation().")
        self.api_client.start_simulation()

    def _create_placeholder(self, text: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        frame.setStyleSheet(f"background-color: #2c3e50; border: 2px solid {color}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(label)
        return frame

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())