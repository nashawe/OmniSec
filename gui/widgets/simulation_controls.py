# gui/widgets/simulation_controls.py

from PySide6.QtWidgets import (
    QWidget, QPushButton, QSlider, QLabel, QHBoxLayout, QVBoxLayout, QGroupBox
)
from PySide6.QtCore import Qt, Signal

class SimulationControlsWidget(QWidget):
    start_clicked = Signal()
    pause_clicked = Signal()
    reset_clicked = Signal()
    speed_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        group_box = QGroupBox("Simulation Controls")
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.reset_button = QPushButton("Reset")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(4)
        self.speed_slider.setValue(1)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        self.speed_label = QLabel("Speed: 1x")
        self.speed_label.setAlignment(Qt.AlignCenter)
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Slow"))
        slider_layout.addWidget(self.speed_slider)
        slider_layout.addWidget(QLabel("Fast"))
        main_layout.addLayout(button_layout)
        main_layout.addLayout(slider_layout)
        main_layout.addWidget(self.speed_label)
        group_box.setLayout(main_layout)
        final_layout = QVBoxLayout()
        final_layout.addWidget(group_box)
        self.setLayout(final_layout)
        
        self.start_button.clicked.connect(self.on_start)
        self.pause_button.clicked.connect(self.on_pause)
        self.reset_button.clicked.connect(self.on_reset)
        self.speed_slider.valueChanged.connect(self.on_speed_change)

    def on_start(self):
        # --- TRACER ---
        print("[1] SimulationControlsWidget: 'Start' button clicked. Emitting start_clicked signal.")
        self.start_clicked.emit()

    def on_pause(self):
        print("[1] SimulationControlsWidget: 'Pause' button clicked. Emitting pause_clicked signal.")
        self.pause_clicked.emit()

    def on_reset(self):
        print("[1] SimulationControlsWidget: 'Reset' button clicked. Emitting reset_clicked signal.")
        self.reset_clicked.emit()

    def on_speed_change(self, value):
        speed_map = {0: 0.5, 1: 1, 2: 2, 3: 5, 4: 10}
        speed_value = speed_map.get(value, 1)
        self.speed_label.setText(f"Speed: {speed_value}x")
        print(f"[1] SimulationControlsWidget: Speed changed. Emitting speed_changed signal with value {speed_value}.")
        self.speed_changed.emit(speed_value)