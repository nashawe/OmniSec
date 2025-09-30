# gui/main.py

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame
)
from PySide6.QtCore import Qt

# Import our new custom widget
from widgets.simulation_controls import SimulationControlsWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.setWindowTitle("OmniSec: Cyber Conflict Simulation")
        self.setGeometry(100, 100, 1600, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --- Main Layout (Horizontal) ---
        main_layout = QHBoxLayout(central_widget)

        # --- Left Side: Network Graph Placeholder ---
        network_graph_placeholder = self._create_placeholder("Network Graph Canvas", "#3498db")
        main_layout.addWidget(network_graph_placeholder, stretch=3)

        # --- Right Side: Sidebar Layout (Vertical) ---
        sidebar_layout = QVBoxLayout()
        
        # --- Sidebar Components ---
        inspector_panel_placeholder = self._create_placeholder("Node Inspector / Team Status", "#2ecc71")
        event_feed_placeholder = self._create_placeholder("Event Feed", "#f1c40f")
        
        # <<< CHANGE IS HERE >>>
        # Create an instance of our new SimulationControlsWidget
        self.simulation_controls = SimulationControlsWidget()

        # Add the sidebar components to the vertical sidebar_layout
        sidebar_layout.addWidget(inspector_panel_placeholder, stretch=2)
        sidebar_layout.addWidget(event_feed_placeholder, stretch=3)
        # Add our new widget instead of the placeholder
        sidebar_layout.addWidget(self.simulation_controls, stretch=1)

        # Add the complete sidebar layout to the main horizontal layout
        main_layout.addLayout(sidebar_layout, stretch=1)

    def _create_placeholder(self, text: str, color: str) -> QFrame:
        """A helper function to create a styled QFrame as a placeholder."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #2c3e50;
                border: 2px solid {color};
                border-radius: 5px;
            }}
            QLabel {{
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                background-color: transparent;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return frame


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())