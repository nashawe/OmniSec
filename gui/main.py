# gui/main.py

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSlider, QLabel, QFrame, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor, QFontDatabase

from widgets.network_graph_canvas import NetworkGraphCanvas
from widgets.event_feed import EventFeedWidget
from api_client import APIClient
from theme import ThemeManager


def format_sim_time(sim_time):
    total_s = int(sim_time * 60)
    return f"{total_s // 60:02d}:{total_s % 60:02d}"

# ---------------------------------------------------------------------------
# Node Popup Widget
# ---------------------------------------------------------------------------
class NodePopupWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Act as a floating child widget, not an OS-level window
        self.setFixedWidth(380)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)
        
        header_layout = QHBoxLayout()
        self.name_label = QLabel("NODE")
        self.name_label.setFont(font(16, bold=True))
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        self.type_status_label = QLabel("")
        self.type_status_label.setFont(font(13, bold=True))
        
        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.type_status_label)
        
        # Security profile
        sec_group = QVBoxLayout()
        sec_group.setSpacing(6)
        sec_header = QLabel("SECURITY PROFILE")
        sec_header.setFont(font(12, bold=True))
        sec_group.addWidget(sec_header)
        
        self.posture_bar = QProgressBar()
        self.posture_bar.setRange(0, 100)
        self.posture_bar.setFixedHeight(8)
        self.posture_bar.setTextVisible(False)
        sec_group.addWidget(QLabel("Security Posture:"))
        sec_group.addWidget(self.posture_bar)
        
        self.profile_details = QLabel()
        self.profile_details.setFont(font(12))
        sec_group.addWidget(self.profile_details)
        
        self.main_layout.addLayout(sec_group)
        
        # Services
        srv_header = QLabel("SERVICES")
        srv_header.setFont(font(12, bold=True))
        self.main_layout.addWidget(srv_header)
        self.services_label = QLabel()
        self.services_label.setFont(font(12))
        self.main_layout.addWidget(self.services_label)
        
        # Vulnerabilities
        vuln_header = QLabel("VULNERABILITIES")
        vuln_header.setFont(font(12, bold=True))
        self.main_layout.addWidget(vuln_header)
        self.vulns_label = QLabel()
        self.vulns_label.setFont(font(12))
        self.main_layout.addWidget(self.vulns_label)
        
        # Timeline
        tl_header = QLabel("KILL CHAIN HISTORY")
        tl_header.setFont(font(12, bold=True))
        self.main_layout.addWidget(tl_header)
        self.timeline_label = QLabel()
        self.timeline_label.setFont(font(12))
        self.timeline_label.setWordWrap(True)
        self.main_layout.addWidget(self.timeline_label)
        
        # Plain English string
        self.main_layout.addStretch()
        self.desc_label = QLabel()
        self.desc_label.setFont(font(14, bold=True))
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)
        
        self._current_node_id = None
        self._last_snapshot = None
        
        self.apply_theme()

    def set_data(self, node_id, snapshot):
        self._current_node_id = node_id
        self._last_snapshot = snapshot
        if not snapshot:
            return
            
        network = snapshot.get("network", {})
        nodes = network.get("nodes", [])
        node = next((n for n in nodes if n["id"] == node_id), None)
        if not node:
            return
            
        kc_log = snapshot.get("kill_chain_log", [])
        kc_prog = snapshot.get("kill_chain_progress", {}).get(node_id, [])
        is_fingerprinted = "FINGERPRINTED" in kc_prog
        
        t = ThemeManager.instance()
        status = node.get("current_status", "OPERATIONAL")
        status_style = t.status_style(status)
        
        self.name_label.setText(node.get("name", node_id))
        self.type_status_label.setText(f"{node.get('node_type', 'System')} • {status}")
        self.type_status_label.setStyleSheet(f"color: {status_style['text']}; border: none;")
        
        posture = int(node.get("security_posture_score", 0) * 100)
        self.posture_bar.setValue(posture)
        if posture < 33:
            p_color = t.colors()["red_team"]
        elif posture < 66:
            p_color = t.colors()["yellow"]
        else:
            p_color = t.colors()["green"]
            
        self.posture_bar.setStyleSheet(f"QProgressBar {{ background-color: {t.colors()['bar_track']}; border: none; border-radius: 3px; }} QProgressBar::chunk {{ background-color: {p_color}; border-radius: 3px; }}")
        
        val = node.get("value", 1.0)
        exp = "Yes" if node.get("exposed_to_internet") else "No"
        rdp = "Yes" if node.get("rdp_enabled") else "No"
        adm = "Yes" if node.get("has_admin_users") else "No"
        self.profile_details.setText(f"Value Score: {val}<br>Exposed to Internet: {exp}<br>RDP Enabled: {rdp}<br>Has Admin Users: {adm}")
        
        srvs = node.get("services_running", [])
        if srvs:
            s_text = "<br>".join([f"• {s.get('service_id', 'Unknown')} ({s.get('protocol', 'TCP')})" for s in srvs])
        else:
            s_text = "No services running"
        self.services_label.setText(s_text)
        
        vulns = node.get("vulnerabilities", [])
        if not vulns:
            self.vulns_label.setText("No vulnerabilities present")
            self.vulns_label.setStyleSheet(f"color: {t.colors()['text_secondary']};")
        else:
            if is_fingerprinted:
                v_text = "<br>".join([f"• <span style='color: {t.colors()['red_team']};'>{v.get('cve_id', 'CVE-XXXX')}</span> <span style='color: {t.colors()['red_team']}; font-size: 10px; font-weight: bold;'>  KNOWN TO RED</span>" for v in vulns])
                self.vulns_label.setText(v_text)
            else:
                v_text = "<br>".join([f"• {v.get('cve_id', 'CVE-XXXX')} <span style='color: {t.colors()['text_muted']};'>(— undiscovered —)</span>" for v in vulns])
                self.vulns_label.setText(v_text)
        
        tl_events = [e for e in kc_log if e.get("node_id") == node_id]
        if not tl_events:
            self.timeline_label.setText("No activity yet")
            self.timeline_label.setStyleSheet(f"color: {t.colors()['text_muted']};")
        else:
            lines = []
            for ev in tl_events:
                # Engine doesn't add sim_time by default, so we gracefully hide if missing
                st = ev.get("sim_time")
                time_str = f"[{format_sim_time(st)}] " if st is not None else ""
                lines.append(f"• {time_str}{ev.get('tactic', 'Tactic')} - {ev.get('technique', 'Technique')}")
            self.timeline_label.setText("<br>".join(lines))
            self.timeline_label.setStyleSheet(f"color: {t.colors()['text']};")
            
        STATUS_DESC = {
            "OPERATIONAL": "This node has not been touched by the Red Team",
            "PORT_SCANNED": "Red Team has identified open ports on this node but has not gained access",
            "SERVICE_FINGERPRINTED": "Red Team knows exactly what software is running and is looking for vulnerabilities",
            "INITIAL_ACCESS_GAINED": "Red Team has broken into this node for the first time",
            "PRIVILEGED_ACCESS": "Red Team has full admin control of this node",
            "CREDENTIALS_DUMPED": "Red Team has stolen password hashes from this node",
            "LATERAL_ACCESS": "Red Team reached this node by pivoting from another compromised machine",
            "EVASION_ACTIVE": "Red Team has cleared logs and disabled antivirus — Blue Team visibility is reduced",
            "C2_ESTABLISHED": "Red Team has planted a persistent backdoor beacon on this node",
            "DATA_STAGED": "Red Team has copied sensitive data and is preparing to send it out",
            "DATA_EXFILTRATED": "Red Team has successfully stolen data from this node",
            "ISOLATED_QUARANTINED": "Blue Team has cut this node off from the network"
        }
        self.desc_label.setText(STATUS_DESC.get(status, f"Status: {status}"))
        self.desc_label.setStyleSheet(f"color: {t.colors()['text']};")

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            NodePopupWidget {{
                background-color: {t['bg_alt']};
                border: 2px solid {t['border']};
                border-radius: 6px;
            }}
        """)
        self.name_label.setStyleSheet(f"color: {t['text']}; border: none; background: transparent;")
        self.close_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {t['text_muted']}; border: none; font-size: 16px; }} QPushButton:hover {{ color: {t['text']}; }}")
        self.profile_details.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")
        self.services_label.setStyleSheet(f"color: {t['text']}; border: none; background: transparent;")
        self.type_status_label.setStyleSheet(f"border: none; background: transparent; color: {t['accent']};")
        self.vulns_label.setStyleSheet(f"border: none; background: transparent;")
        self.timeline_label.setStyleSheet(f"border: none; background: transparent;")
        self.desc_label.setStyleSheet(f"border: none; background: transparent;")
        
        if self._current_node_id and self._last_snapshot:
            self.set_data(self._current_node_id, self._last_snapshot)


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"

def font(size=13, bold=False):
    w = QFont.Bold if bold else QFont.Normal
    return QFont(FONT_FAMILY, size, w)


# ---------------------------------------------------------------------------
# Reusable styled button
# ---------------------------------------------------------------------------
class TacticalButton(QPushButton):
    def __init__(self, text, color="#5b9cf5", parent=None):
        super().__init__(text, parent)
        self._color = color
        self.setFont(font(13, bold=True))
        self.setFixedHeight(40)
        self.setMinimumWidth(100)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['surface']};
                color: {self._color};
                border: 1px solid {self._color};
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['surface_hover']};
                border: 2px solid {self._color};
            }}
            QPushButton:pressed {{
                background-color: {t['bg']};
            }}
            QPushButton:disabled {{
                color: {t['text_muted']};
                border-color: {t['border']};
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

        self._header = QLabel("SIM TIME")
        self._header.setFont(font(11))

        self._time_label = QLabel("00:00:00")
        self._time_label.setFont(font(22, bold=True))

        self._status_label = QLabel("● PAUSED")
        self._status_label.setFont(font(11, bold=True))

        layout.addWidget(self._header)
        layout.addWidget(self._time_label)
        layout.addWidget(self._status_label)

        self._is_running = False
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self._header.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")
        self._time_label.setStyleSheet(f"color: {t['accent']}; border: none; background: transparent;")
        self._update_status_style()

    def _update_status_style(self):
        t = ThemeManager.instance().colors()
        if self._is_running:
            self._status_label.setStyleSheet(f"color: {t['green']}; border: none; background: transparent;")
        else:
            self._status_label.setStyleSheet(f"color: {t['text_muted']}; border: none; background: transparent;")

    def update_display(self, sim_time: float, is_running: bool):
        total_seconds = int(sim_time * 60)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        self._time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
        self._is_running = is_running

        if is_running:
            self._status_label.setText("● RUNNING")
        else:
            self._status_label.setText("● PAUSED")
        self._update_status_style()

    def reset(self):
        """Fix 5: Reset clock to initial state."""
        self._time_label.setText("00:00:00")
        self._is_running = False
        self._status_label.setText("● PAUSED")
        self._update_status_style()


# ---------------------------------------------------------------------------
# Resource bar (red or blue team)
# ---------------------------------------------------------------------------
class ResourceBar(QWidget):
    def __init__(self, label: str, color_key: str, parent=None):
        super().__init__(parent)
        self._color_key = color_key
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        self._lbl = QLabel(label)
        self._lbl.setFont(font(12, bold=True))

        self._value_label = QLabel("100")
        self._value_label.setFont(font(12, bold=True))
        self._value_label.setAlignment(Qt.AlignRight)

        header_row.addWidget(self._lbl)
        header_row.addStretch()
        header_row.addWidget(self._value_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(100)
        self._bar.setFixedHeight(8)
        self._bar.setTextVisible(False)

        layout.addLayout(header_row)
        layout.addWidget(self._bar)
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        team_color = t[self._color_key]
        self._lbl.setStyleSheet(f"color: {team_color}; border: none; background: transparent;")
        self._value_label.setStyleSheet(f"color: {team_color}; border: none; background: transparent;")
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t['bar_track']};
                border: 1px solid {t['bar_track_border']};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {team_color};
                border-radius: 3px;
            }}
        """)

    def update_value(self, value: float):
        clamped = max(0, min(100, int(value)))
        self._bar.setValue(clamped)
        self._value_label.setText(str(int(value)))

    def reset(self):
        """Fix 5: Reset to full."""
        self._bar.setValue(100)
        self._value_label.setText("100")


# ---------------------------------------------------------------------------
# Bottom control bar (includes zoom controls — Fix 3)
# ---------------------------------------------------------------------------
class ControlBar(QWidget):
    def __init__(self, api_client: APIClient, canvas: NetworkGraphCanvas, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._canvas = canvas
        self.setFixedHeight(100)
        self._setup_ui()
        self.apply_theme()

        # Wire canvas zoom_changed signal to keep slider in sync
        self._canvas.zoom_changed.connect(self._on_canvas_zoom_changed)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(24)

        # --- Sim clock ---
        self._clock = SimClockWidget()
        self._clock.setStyleSheet("background: transparent;")

        # --- Control buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        t = ThemeManager.instance().colors()
        self._start_btn  = TacticalButton("▶  START",  color=t['green'])
        self._pause_btn  = TacticalButton("⏸  PAUSE",  color=t['yellow'])
        self._reset_btn  = TacticalButton("↺  RESET",  color=t['red_team'])

        self._start_btn.clicked.connect(self._api.start_simulation)
        self._pause_btn.clicked.connect(self._api.pause_simulation)
        # Fix 5: reset_btn wired to _on_reset, not directly to API
        self._reset_btn.clicked.connect(self._on_reset)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._pause_btn)
        btn_layout.addWidget(self._reset_btn)

        # --- Speed slider ---
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(4)

        self._speed_header = QLabel("SPEED")
        self._speed_header.setFont(font(11, bold=True))

        slider_row = QHBoxLayout()
        self._speed_label = QLabel("1×")
        self._speed_label.setFont(font(12, bold=True))
        self._speed_label.setFixedWidth(36)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(4)
        self._slider.setValue(1)
        self._slider.setFixedWidth(120)
        self._slider.valueChanged.connect(self._on_speed_change)

        slider_row.addWidget(self._speed_label)
        slider_row.addWidget(self._slider)

        speed_layout.addWidget(self._speed_header)
        speed_layout.addLayout(slider_row)

        # --- Resource bars ---
        resource_layout = QVBoxLayout()
        resource_layout.setSpacing(8)

        self._red_bar  = ResourceBar("RED TEAM", "red_team")
        self._blue_bar = ResourceBar("BLUE TEAM", "blue_team")

        resource_layout.addWidget(self._red_bar)
        resource_layout.addWidget(self._blue_bar)

        # --- Fix 3: Zoom controls in control bar ---
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(4)

        self._zoom_header = QLabel("ZOOM")
        self._zoom_header.setFont(font(11, bold=True))

        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(6)

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedSize(30, 28)
        self._zoom_out_btn.setCursor(Qt.PointingHandCursor)
        self._zoom_out_btn.clicked.connect(self._canvas.zoom_out)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setMinimum(10)
        self._zoom_slider.setMaximum(500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(30, 28)
        self._zoom_in_btn.setCursor(Qt.PointingHandCursor)
        self._zoom_in_btn.clicked.connect(self._canvas.zoom_in)

        self._zoom_fit_btn = QPushButton("⤧")
        self._zoom_fit_btn.setFixedSize(30, 28)
        self._zoom_fit_btn.setCursor(Qt.PointingHandCursor)
        self._zoom_fit_btn.clicked.connect(self._canvas.reset_view)

        self._zoom_buttons = [
            self._zoom_out_btn, self._zoom_in_btn, self._zoom_fit_btn
        ]

        zoom_row.addWidget(self._zoom_out_btn)
        zoom_row.addWidget(self._zoom_slider)
        zoom_row.addWidget(self._zoom_in_btn)
        zoom_row.addWidget(self._zoom_fit_btn)

        zoom_layout.addWidget(self._zoom_header)
        zoom_layout.addLayout(zoom_row)

        # --- Divider helper ---
        def divider():
            d = QFrame()
            d.setFrameShape(QFrame.VLine)
            d.setFixedWidth(1)
            return d

        self._dividers = []
        for _ in range(4):
            d = divider()
            self._dividers.append(d)

        # --- Assemble ---
        layout.addWidget(self._clock)
        layout.addWidget(self._dividers[0])
        layout.addLayout(btn_layout)
        layout.addWidget(self._dividers[1])
        layout.addLayout(speed_layout)
        layout.addWidget(self._dividers[2])
        layout.addLayout(resource_layout)
        layout.addWidget(self._dividers[3])
        layout.addLayout(zoom_layout)
        layout.addStretch()

    def _on_zoom_slider(self, value):
        self._canvas.set_zoom_level(value / 100.0)

    def _on_canvas_zoom_changed(self, scale):
        """Keep our slider in sync when canvas zooms via trackpad/buttons."""
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(int(scale * 100))
        self._zoom_slider.blockSignals(False)

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            ControlBar {{
                background-color: {t['surface']};
                border-top: 1px solid {t['border']};
            }}
        """)
        self._speed_header.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")
        self._speed_label.setStyleSheet(f"color: {t['accent']}; border: none; background: transparent;")

        slider_style = f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {t['border']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {t['accent']};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {t['accent']};
                border-radius: 2px;
            }}
        """
        self._slider.setStyleSheet(slider_style)
        self._zoom_slider.setStyleSheet(slider_style)

        for d in self._dividers:
            d.setStyleSheet(f"color: {t['border']}; background: {t['border']};")

        self._clock.apply_theme()
        self._red_bar.apply_theme()
        self._blue_bar.apply_theme()
        self._start_btn._color = t['green']
        self._start_btn.apply_theme()
        self._pause_btn._color = t['yellow']
        self._pause_btn.apply_theme()
        self._reset_btn._color = t['red_team']
        self._reset_btn.apply_theme()

        # Zoom section
        self._zoom_header.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")
        zoom_btn_style = f"""
            QPushButton {{
                background: {t['bg']};
                color: {t['accent']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {t['surface_hover']};
                border-color: {t['accent']};
            }}
        """
        for btn in self._zoom_buttons:
            btn.setStyleSheet(zoom_btn_style)

    def _on_speed_change(self, value):
        speed_map = {0: 0.5, 1: 1, 2: 2, 3: 5, 4: 10}
        speed = speed_map.get(value, 1)
        self._speed_label.setText(f"{speed}×")
        self._api.set_simulation_speed(speed)

    def _on_reset(self):
        """Fix 5: Reset the backend AND clear all UI state."""
        self._api.reset_simulation()
        self._clock.reset()
        self._red_bar.reset()
        self._blue_bar.reset()
        # Canvas and event feed are cleared via MainWindow._on_reset

    def on_state_updated(self, snapshot: dict):
        self._clock.update_display(
            snapshot.get("sim_time", 0.0),
            snapshot.get("is_running", False)
        )
        self._red_bar.update_value(snapshot.get("red_resources", 100))
        self._blue_bar.update_value(snapshot.get("blue_resources", 100))


# ---------------------------------------------------------------------------
# Top header bar
# ---------------------------------------------------------------------------
class HeaderBar(QWidget):
    theme_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        self._title = QLabel("OMNISEC")
        self._title.setFont(font(16, bold=True))

        self._subtitle = QLabel("CYBER CONFLICT SIMULATION")
        self._subtitle.setFont(font(10))

        self._scenario_label = QLabel("SCENARIO: corporate_network")
        self._scenario_label.setFont(font(10))
        self._scenario_label.setAlignment(Qt.AlignRight)

        layout.addWidget(self._title)
        layout.addSpacing(14)
        layout.addWidget(self._subtitle)
        layout.addStretch()
        layout.addWidget(self._scenario_label)
        layout.addSpacing(12)

        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            HeaderBar {{
                background-color: {t['bg_alt']};
                border-bottom: 1px solid {t['border']};
            }}
        """)
        self._title.setStyleSheet(f"color: {t['accent']}; letter-spacing: 3px; border: none; background: transparent;")
        self._subtitle.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")
        self._scenario_label.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniSec: Cyber Conflict Simulation")
        self.setGeometry(100, 100, 1600, 960)

        self._tm = ThemeManager.instance()

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
        self._header.theme_toggled.connect(self._apply_theme_all)

        # --- Main content area ---
        content = QWidget()
        self._content = content
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Network graph canvas (takes most of the space)
        self._canvas = NetworkGraphCanvas()

        # Right sidebar — event feed
        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(450)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self._event_feed = EventFeedWidget()
        sidebar_layout.addWidget(self._event_feed)

        content_layout.addWidget(self._canvas, stretch=1)
        content_layout.addWidget(self._sidebar)

        # --- Popup ---
        self._node_popup = NodePopupWidget(self._canvas._view)
        self._node_popup.hide()
        self._canvas.node_clicked.connect(self._on_node_clicked)
        self._last_snapshot = {}

        # --- Bottom control bar (now gets canvas reference for zoom) ---
        self._control_bar = ControlBar(self.api_client, self._canvas)

        # --- Stack everything ---
        root.addWidget(self._header)
        root.addWidget(content, stretch=1)
        root.addWidget(self._control_bar)

        # --- Wire up WebSocket signal to all components ---
        self.api_client.state_updated.connect(self._canvas.on_state_updated)
        self.api_client.state_updated.connect(self._event_feed.on_state_updated)
        self.api_client.state_updated.connect(self._control_bar.on_state_updated)
        self.api_client.state_updated.connect(self._on_state_updated)

        # --- Fix 5: Wire reset button to clear all UI ---
        self._control_bar._reset_btn.clicked.connect(self._on_reset)

        # --- Start WebSocket listener ---
        self.api_client.start_websocket_listener()

        # --- Apply initial theme ---
        self._apply_theme_all()

    def _on_state_updated(self, snapshot):
        self._last_snapshot = snapshot
        if not self._node_popup.isHidden():
            self._node_popup.set_data(self._node_popup._current_node_id, snapshot)

    def _on_node_clicked(self, node_id):
        self._node_popup.set_data(node_id, self._last_snapshot)
        item = self._canvas._node_items.get(node_id)
        if item:
            # Get position directly within the canvas view
            view_pt = self._canvas._view.mapFromScene(item.scenePos())
            tx = view_pt.x() + 90
            ty = view_pt.y() - 100
            
            # Ensure it's correctly calculating its geometry after data update
            self._node_popup.adjustSize()
            pw = self._node_popup.width()
            ph = self._node_popup.height() or 400
            
            view_rect = self._canvas._view.rect()
            
            if tx + pw > view_rect.width():
                tx = view_pt.x() - pw - 90
            if ty + ph > view_rect.height():
                ty = view_rect.height() - ph - 10
            if ty < 10:
                ty = 10
                
            self._node_popup.move(tx, ty)
        
        self._node_popup.show()
        self._node_popup.raise_()

    def _on_reset(self):
        """Fix 5: Clear event feed and canvas on reset."""
        self._event_feed.clear()
        self._canvas.clear()
        self._node_popup.hide()

    def _apply_theme_all(self):
        """Applies the current theme to every widget."""
        t = self._tm.colors()
        self.setStyleSheet(f"background-color: {t['bg']};")
        self._header.apply_theme()
        self._control_bar.apply_theme()
        self._event_feed.apply_theme()
        self._canvas.apply_theme()
        self._node_popup.apply_theme()
        self._sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg']};
                border-left: 1px solid {t['border']};
            }}
        """)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())