# gui/widgets/simulation_controls.py

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QSlider,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox
)
from PySide6.QtCore import Qt

class SimulationControlsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Use a QGroupBox to give this section a visible title and border
        group_box = QGroupBox("Simulation Controls")
        
        # --- Create Widgets ---
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.reset_button = QPushButton("Reset")
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(4) # e.g., 0=0.5x, 1=1x, 2=2x, 3=5x, 4=10x
        self.speed_slider.setValue(1) # Default to 1x speed
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)

        self.speed_label = QLabel("Speed: 1x")
        self.speed_label.setAlignment(Qt.AlignCenter)

        # --- Layouts ---
        # Main layout for the group box will be vertical
        main_layout = QVBoxLayout()

        # Horizontal layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)

        # Horizontal layout for the slider and its label
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Slow"))
        slider_layout.addWidget(self.speed_slider)
        slider_layout.addWidget(QLabel("Fast"))

        # Add the button and slider layouts to the main vertical layout
        main_layout.addLayout(button_layout)
        main_layout.addLayout(slider_layout)
        main_layout.addWidget(self.speed_label)

        # Set the group box's layout
        group_box.setLayout(main_layout)

        # The final layout for the whole widget contains just the group box
        final_layout = QVBoxLayout()
        final_layout.addWidget(group_box)
        self.setLayout(final_layout)
        
        # --- Connect Signals to Slots (Functions) ---
        self.start_button.clicked.connect(self.on_start)
        self.pause_button.clicked.connect(self.on_pause)
        self.reset_button.clicked.connect(self.on_reset)
        self.speed_slider.valueChanged.connect(self.on_speed_change)

    # These are the "slot" methods that are called when a signal is emitted.
    def on_start(self):
        print("ACTION: Start button clicked.")
        # In the future, this will call the backend API.

    def on_pause(self):
        print("ACTION: Pause button clicked.")
        # In the future, this will call the backend API.

    def on_reset(self):
        print("ACTION: Reset button clicked.")
        # In the future, this will call the backend API.

    def on_speed_change(self, value):
        speed_map = {0: 0.5, 1: 1, 2: 2, 3: 5, 4: 10}
        speed_value = speed_map.get(value, 1)
        self.speed_label.setText(f"Speed: {speed_value}x")
        print(f"ACTION: Speed changed to {speed_value}x (slider value: {value}).")
        # In the future, this will call the backend API.