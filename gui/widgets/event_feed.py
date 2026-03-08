# gui/widgets/event_feed.py

"""
Event feed with pinned alerts, filter bar, colored borders, and timestamps.
Fix 6 — Full revamp.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import ThemeManager

FONT_FAMILY = "Segoe UI"

def _font(size=13, bold=False):
    return QFont(FONT_FAMILY, size, QFont.Bold if bold else QFont.Normal)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
# Critical actions — these populate the pinned ALERTS section
CRITICAL_ACTIONS = {
    "ExploitPublicFacingApp", "ExploitSUID", "TokenImpersonation",
    "PassTheHashMove", "RDPLateralMove", "EstablishC2",
    "DumpCredentials", "ExfilOverHTTPS", "StageData",
    "PhishingEmail",
}

CRITICAL_EVENT_TYPES = {
    "RED_TEAM_INFO_GAINED",
}

RED_EVENT_TYPES = {
    "ACTION_INITIATED", "ACTION_SUCCESS", "ACTION_FAILURE", "ACTION_FAILED",
    "RED_TEAM_INFO_GAINED",
}

BLUE_EVENT_TYPES = {
    "BLUE_ALERT", "BLUE_TEAM_VULN_DISCOVERED",
}

NOISE_EVENT_TYPES = {
    "ACTION_INITIATED", "ACTION_COMPLETED",
}


def classify_event(event_type: str, payload: dict) -> dict:
    """Returns classification info: border_color, is_noise, is_critical, team."""
    action = payload.get("action", "")
    is_critical = (
        action in CRITICAL_ACTIONS
        or event_type in CRITICAL_EVENT_TYPES
    )
    # Only ACTION_SUCCESS with a critical action is actually critical
    if event_type == "ACTION_SUCCESS" and action in CRITICAL_ACTIONS:
        is_critical = True
    elif event_type == "ACTION_SUCCESS":
        is_critical = False

    is_noise = event_type in NOISE_EVENT_TYPES

    # Border color key (resolved at render time to theme colors)
    # Noise events always get muted grey border
    if is_noise:
        border_key = "muted"
    elif is_critical and event_type in ("ACTION_SUCCESS", "RED_TEAM_INFO_GAINED"):
        border_key = "critical"
    elif event_type in ("ACTION_FAILURE", "ACTION_FAILED"):
        border_key = "orange"
    elif event_type == "ACTION_SUCCESS":
        border_key = "green"
    elif event_type in BLUE_EVENT_TYPES:
        border_key = "blue_team"
    elif event_type in RED_EVENT_TYPES:
        border_key = "red_team"
    else:
        border_key = "muted"

    # Team
    if event_type in BLUE_EVENT_TYPES:
        team = "BLUE"
    elif event_type in RED_EVENT_TYPES:
        team = "RED"
    else:
        team = "OTHER"

    return {
        "border_key": border_key,
        "is_noise": is_noise,
        "is_critical": is_critical,
        "team": team,
    }


def format_event_text(event_type: str, payload: dict, node_names: dict) -> str:
    """One-line description of the event."""
    action = payload.get("action", "")
    target_id = payload.get("target", "")
    target_name = node_names.get(target_id, target_id)

    if event_type == "ACTION_SUCCESS":
        if action == "PortScan": return f"Red scanned {target_name} and found open ports"
        if action == "ServiceFingerprint": return f"Red fingerprinted {target_name} and identified running services"
        if action == "ExploitPublicFacingApp": return f"Red exploited a vulnerability and broke into {target_name}"
        if action == "PhishingEmail": return f"Red's phishing email succeeded — initial access gained on {target_name}"
        if action == "ExploitSUID": return f"Red escalated to root on {target_name}"
        if action == "TokenImpersonation": return f"Red stole an admin token on {target_name}"
        if action == "DumpCredentials": return f"Red dumped password hashes from {target_name}"
        if action == "Kerberoasting": return f"Red cracked Kerberos tickets on {target_name}"
        if action == "PassTheHashMove": return f"Red pivoted to {target_name} using a stolen hash"
        if action == "RDPLateralMove": return f"Red logged into {target_name} via RDP using stolen credentials"
        if action == "ClearEventLogs": return f"Red cleared event logs on {target_name} — Blue visibility reduced"
        if action == "DisableAV": return f"Red disabled antivirus on {target_name}"
        if action == "EstablishC2": return f"Red planted a C2 beacon on {target_name} — persistent access established"
        if action == "C2BeaconKeepAlive": return f"C2 beacon checked in from {target_name}"
        if action == "StageData": return f"Red staged data on {target_name} — preparing to exfiltrate"
        if action == "ExfilOverHTTPS": return f"Red exfiltrated data from {target_name} over HTTPS — attack objective complete"
        return f"✓ {action} → {target_name}" if target_name else f"✓ {action}"
        
    elif event_type in ("ACTION_FAILURE", "ACTION_FAILED"):
        if action == "ServiceFingerprint":
            return f"Red's fingerprint attempt on {target_name} was blocked"
        reason = payload.get("reason", "failed")
        return f"✗ {action} — {reason}"
        
    elif event_type == "RED_TEAM_INFO_GAINED":
        return f"Red discovered vulnerabilities on {target_name}"
        
    elif event_type == "BLUE_ALERT":
        return f"⚠ Alert: {payload.get('message', 'detection')}"
        
    elif event_type == "BLUE_TEAM_VULN_DISCOVERED":
        return f"🔵 Blue found vulnerability on {target_name}"
        
    else:
        return f"◆ {event_type}"


def format_sim_time(sim_time: float) -> str:
    """Convert sim_time (minutes) to MM:SS."""
    total_s = int(sim_time * 60)
    m = total_s // 60
    s = total_s % 60
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Border color mapping
# ---------------------------------------------------------------------------
BORDER_COLORS = {
    "dark": {
        "critical": "#ff2244",
        "red_team": "#f55555",
        "blue_team": "#55aaff",
        "green": "#44cc88",
        "orange": "#ff9944",
        "muted": "#4a4a60",
    },
    "light": {
        "critical": "#cc0022",
        "red_team": "#d93333",
        "blue_team": "#2277cc",
        "green": "#22aa66",
        "orange": "#cc7722",
        "muted": "#c0c0cc",
    },
}

def get_border_color(border_key: str) -> str:
    mode = ThemeManager.instance().mode
    return BORDER_COLORS[mode].get(border_key, BORDER_COLORS[mode]["muted"])


# ---------------------------------------------------------------------------
# Single event row widget
# ---------------------------------------------------------------------------
class EventRow(QFrame):
    def __init__(self, text: str, border_key: str, team: str,
                 timestamp: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._border_key = border_key
        self._team = team
        self._timestamp = timestamp

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)

        self._label = QLabel(text)
        self._label.setFont(_font(12))
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._ts_label = QLabel(timestamp)
        self._ts_label.setFont(_font(10))
        self._ts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ts_label.setFixedWidth(46)
        
        self.setMinimumHeight(32)

        layout.addWidget(self._label, stretch=1)
        layout.addWidget(self._ts_label)

        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        bc = get_border_color(self._border_key)
        
        bg_color = "transparent"
        if self._team == "RED":
            c = QColor(t['red_team'])
            c.setAlpha(20)
            bg_color = c.name(QColor.HexArgb)
        elif self._team == "BLUE":
            c = QColor(t['blue_team'])
            c.setAlpha(20)
            bg_color = c.name(QColor.HexArgb)
            
        self._label.setStyleSheet(f"color: {t['text']}; background: transparent; border: none;")
        self._ts_label.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")
        self.setStyleSheet(f"""
            EventRow {{
                background: {bg_color};
                border-left: 4px solid {bc};
                border-bottom: 1px solid {t['border']};
            }}
        """)


# ---------------------------------------------------------------------------
# Alert row (pinned at top)
# ---------------------------------------------------------------------------
class AlertRow(QFrame):
    def __init__(self, text: str, timestamp: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._timestamp = timestamp

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)

        self._icon = QLabel("⚡")
        self._icon.setFont(_font(13))
        self._icon.setFixedWidth(22)

        self._label = QLabel(text)
        self._label.setFont(_font(11, bold=True))
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._ts_label = QLabel(timestamp)
        self._ts_label.setFont(_font(10))
        self._ts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ts_label.setFixedWidth(46)

        layout.addWidget(self._icon)
        layout.addWidget(self._label, stretch=1)
        layout.addWidget(self._ts_label)

        self.setMinimumHeight(44)
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        bc = get_border_color("critical")
        self.setStyleSheet(f"""
            AlertRow {{
                background: {t['surface']};
                border-left: 4px solid {bc};
                border-bottom: 1px solid {t['border']};
            }}
        """)
        self._icon.setStyleSheet(f"color: {t['red_team']}; border: none; background: transparent;")
        self._label.setStyleSheet(f"color: {t['red_team']}; border: none; background: transparent;")
        self._ts_label.setStyleSheet(f"color: {t['text_secondary']}; border: none; background: transparent;")


# ---------------------------------------------------------------------------
# Filter button
# ---------------------------------------------------------------------------
class FilterButton(QPushButton):
    def __init__(self, text, key, parent=None):
        super().__init__(text, parent)
        self.key = key
        self._active = (key == "ALL")
        self.setFont(_font(10, bold=True))
        self.setFixedHeight(26)
        self.setMinimumWidth(60)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_theme()

    def set_active(self, active: bool):
        self._active = active
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {t['accent']};
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 2px 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {t['surface']};
                    color: {t['text_secondary']};
                    border: 1px solid {t['border']};
                    border-radius: 4px;
                    padding: 2px 10px;
                }}
                QPushButton:hover {{
                    background: {t['surface_hover']};
                    color: {t['text']};
                }}
            """)


# ---------------------------------------------------------------------------
# EventFeedWidget
# ---------------------------------------------------------------------------
class EventFeedWidget(QWidget):
    MAX_EVENTS = 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_event_count = 0
        self._current_sim_time = 0.0
        self._all_events = []       # List of event dicts
        self._alert_events = []     # Last 3 critical events
        self._node_names = {}
        self._active_filter = "ALL"
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Header ---
        self._header = QFrame()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(14, 8, 14, 8)

        self._title = QLabel("EVENT FEED")
        self._title.setFont(_font(12, bold=True))

        self._count_label = QLabel("0 events")
        self._count_label.setFont(_font(10))
        self._count_label.setAlignment(Qt.AlignRight)

        header_layout.addWidget(self._title)
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)
        
        # --- LATEST banner ---
        self._latest_container = QFrame()
        latest_layout = QVBoxLayout(self._latest_container)
        latest_layout.setContentsMargins(14, 10, 14, 10)
        self._latest_label = QLabel("LATEST — Waiting for events...")
        self._latest_label.setFont(_font(12, bold=True))
        self._latest_label.setWordWrap(True)
        latest_layout.addWidget(self._latest_label)

        # --- Alerts section ---
        self._alerts_container = QWidget()
        self._alerts_layout = QVBoxLayout(self._alerts_container)
        self._alerts_layout.setContentsMargins(0, 0, 0, 0)
        self._alerts_layout.setSpacing(0)

        self._alerts_header = QLabel("  ⚡ ALERTS")
        self._alerts_header.setFont(_font(10, bold=True))
        self._alerts_header.setFixedHeight(24)
        self._alerts_layout.addWidget(self._alerts_header)

        # Placeholder for up to 3 alert rows
        self._alert_rows = []

        self._alerts_divider = QFrame()
        self._alerts_divider.setFrameShape(QFrame.HLine)
        self._alerts_divider.setFixedHeight(2)

        # --- Filter bar ---
        self._filter_bar = QFrame()
        filter_layout = QHBoxLayout(self._filter_bar)
        filter_layout.setContentsMargins(10, 6, 10, 6)
        filter_layout.setSpacing(6)

        self._filter_buttons = []
        for label, key in [("ALL", "ALL"), ("RED", "RED"), ("BLUE", "BLUE"), ("CRITICAL", "CRITICAL")]:
            btn = FilterButton(label, key)
            btn.clicked.connect(lambda checked=False, k=key: self._set_filter(k))
            self._filter_buttons.append(btn)
            filter_layout.addWidget(btn)
        filter_layout.addStretch()
        
        self._sim_time_header = QLabel("SIM TIME")
        self._sim_time_header.setFont(_font(10, bold=True))
        self._sim_time_header.setAlignment(Qt.AlignCenter)
        self._sim_time_header.setFixedWidth(60)
        filter_layout.addWidget(self._sim_time_header)

        # --- Scrollable feed ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._feed_widget = QWidget()
        self._feed_layout = QVBoxLayout(self._feed_widget)
        self._feed_layout.setContentsMargins(0, 0, 0, 0)
        self._feed_layout.setSpacing(0)
        self._feed_layout.addStretch()  # Pushes content to top

        self._scroll.setWidget(self._feed_widget)

        # --- Assemble ---
        root.addWidget(self._header)
        root.addWidget(self._latest_container)
        root.addWidget(self._alerts_container)
        root.addWidget(self._alerts_divider)
        root.addWidget(self._filter_bar)
        root.addWidget(self._scroll, stretch=1)

        self.apply_theme()

    def _set_filter(self, key: str):
        self._active_filter = key
        for btn in self._filter_buttons:
            btn.set_active(btn.key == key)
        self._rebuild_feed()

    def _rebuild_feed(self):
        """Clear and re-populate the feed based on the active filter."""
        # Clear existing rows
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-add filtered events
        for ev in self._all_events:
            if self._passes_filter(ev):
                row = EventRow(
                    ev["text"], ev["border_key"], ev["team"],
                    ev["timestamp"]
                )
                self._feed_layout.insertWidget(self._feed_layout.count() - 1, row)

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _passes_filter(self, ev: dict) -> bool:
        f = self._active_filter
        if f == "ALL":
            return True
        if f == "RED":
            return ev["team"] == "RED"
        if f == "BLUE":
            return ev["team"] == "BLUE"
        if f == "CRITICAL":
            return ev["is_critical"]
        return True

    def apply_theme(self):
        t = ThemeManager.instance().colors()
        self._header.setStyleSheet(f"""
            QFrame {{
                background-color: {t['surface']};
                border-bottom: 1px solid {t['border']};
            }}
        """)
        self._title.setStyleSheet(f"color: {t['accent']}; background: transparent; border: none;")
        self._count_label.setStyleSheet(f"color: {t['text_muted']}; background: transparent; border: none;")
        
        self._latest_container.setStyleSheet(f"""
            QFrame {{
                background-color: {t['surface']};
                border-bottom: 2px solid {t['accent']};
            }}
        """)
        self._latest_label.setStyleSheet(f"color: {t['accent']}; background: transparent; border: none;")

        self._alerts_header.setStyleSheet(f"color: {t['red_team']}; background: {t['surface']}; border: none; padding-left: 8px;")
        self._alerts_container.setStyleSheet(f"background: {t['surface']};")
        self._alerts_divider.setStyleSheet(f"background: {t['border']};")

        self._filter_bar.setStyleSheet(f"background: {t['bg_alt']}; border-bottom: 1px solid {t['border']};")
        self._sim_time_header.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")

        for btn in self._filter_buttons:
            btn.apply_theme()

        scroll_style = f"""
            QScrollArea {{
                background: {t['bg']};
                border: none;
            }}
            QWidget {{
                background: {t['bg']};
            }}
            QScrollBar:vertical {{
                background: {t['scrollbar_bg']};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar_handle']};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        self._scroll.setStyleSheet(scroll_style)

        # Re-theme alert rows
        for row in self._alert_rows:
            row.apply_theme()

        # Re-theme feed rows
        for i in range(self._feed_layout.count()):
            item = self._feed_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), EventRow):
                item.widget().apply_theme()

    def clear(self):
        """Fix 5: Clear everything for reset."""
        self._all_events.clear()
        self._alert_events.clear()
        self._node_names.clear()
        self._last_event_count = 0
        self._current_sim_time = 0.0
        self._count_label.setText("0 events")
        self._latest_label.setText("LATEST — Waiting for events...")

        # Clear alert rows
        for row in self._alert_rows:
            row.deleteLater()
        self._alert_rows.clear()

        # Clear feed rows
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # -----------------------------------------------------------------------
    # Public slot — called on every WebSocket snapshot
    # -----------------------------------------------------------------------
    def on_state_updated(self, snapshot: dict):
        self._current_sim_time = snapshot.get("sim_time", 0.0)
        
        network = snapshot.get("network", {})
        nodes = network.get("nodes", [])
        for n in nodes:
            self._node_names[n["id"]] = n.get("name", n["id"])
            
        recent_events = snapshot.get("recent_events", [])
        total = len(recent_events)

        if total <= self._last_event_count:
            return

        new_events = recent_events[self._last_event_count:]
        self._last_event_count = total

        for event in new_events:
            self._process_event(event)

        self._count_label.setText(f"{len(self._all_events)} events")

        # Trim if too many
        while len(self._all_events) > self.MAX_EVENTS:
            self._all_events.pop(0)

        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _process_event(self, event: dict):
        event_type = event["event_type"]
        payload = event.get("payload", {})
        timestamp = format_sim_time(self._current_sim_time)

        classification = classify_event(event_type, payload)
        
        if classification["is_noise"]:
            return
            
        text = format_event_text(event_type, payload, self._node_names)
        
        self._latest_label.setText(f"LATEST — {text}")

        ev_data = {
            "event_type": event_type,
            "payload": payload,
            "text": text,
            "timestamp": timestamp,
            "border_key": classification["border_key"],
            "team": classification["team"],
            "is_critical": classification["is_critical"],
        }

        self._all_events.append(ev_data)

        # Update pinned alerts if critical
        if classification["is_critical"] and event_type == "ACTION_SUCCESS":
            self._alert_events.append(ev_data)
            if len(self._alert_events) > 3:
                self._alert_events.pop(0)
            self._rebuild_alerts()

        # Add to feed if passes current filter
        if self._passes_filter(ev_data):
            row = EventRow(text, ev_data["border_key"], ev_data["team"], timestamp)
            self._feed_layout.insertWidget(self._feed_layout.count() - 1, row)

    def _rebuild_alerts(self):
        """Rebuild the pinned alerts section."""
        for row in self._alert_rows:
            row.deleteLater()
        self._alert_rows.clear()

        for ev in self._alert_events:
            row = AlertRow(ev["text"], ev["timestamp"])
            self._alerts_layout.addWidget(row)
            self._alert_rows.append(row)