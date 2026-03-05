# gui/widgets/event_feed.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


# ---------------------------------------------------------------------------
# Color coding by event type
# ---------------------------------------------------------------------------
EVENT_COLORS = {
    # Red team events
    "ACTION_INITIATED":       "#00aaff",   # Blue — neutral action started
    "RED_TEAM_INFO_GAINED":   "#ff4444",   # Red — red team got intel
    "ACTION_SUCCESS":         "#ff6600",   # Orange — action succeeded
    "ACTION_FAILURE":         "#666688",   # Dim — action failed
    "ACTION_FAILED":          "#555566",   # Dimmer — resource failure

    # Blue team events
    "BLUE_TEAM_VULN_DISCOVERED": "#00ff88", # Green — blue team found vuln
    "ACTION_COMPLETED":          "#4488aa", # Muted blue — generic complete

    # Default
    "DEFAULT":                "#aabbcc",
}

EVENT_ICONS = {
    "ACTION_INITIATED":          "▶",
    "RED_TEAM_INFO_GAINED":      "🔴",
    "ACTION_SUCCESS":            "✓",
    "ACTION_FAILURE":            "✗",
    "ACTION_FAILED":             "✗",
    "BLUE_TEAM_VULN_DISCOVERED": "🔵",
    "ACTION_COMPLETED":          "◼",
    "DEFAULT":                   "◆",
}

# Human-readable descriptions
EVENT_DESCRIPTIONS = {
    "ACTION_INITIATED":          "Action started",
    "RED_TEAM_INFO_GAINED":      "Red gained intel",
    "ACTION_SUCCESS":            "Action succeeded",
    "ACTION_FAILURE":            "Action failed",
    "ACTION_FAILED":             "Insufficient resources",
    "BLUE_TEAM_VULN_DISCOVERED": "Blue found vulnerability",
    "ACTION_COMPLETED":          "Action completed",
}


def format_event(event_type: str, payload: dict) -> str:
    """Formats an event into a single readable line."""
    icon = EVENT_ICONS.get(event_type, EVENT_ICONS["DEFAULT"])
    desc = EVENT_DESCRIPTIONS.get(event_type, event_type)

    # Pull the most useful field from the payload
    detail = ""
    if "action" in payload:
        detail = f" · {payload['action']}"
    if "target" in payload:
        detail += f" → {payload['target']}"
    if "vulnerabilities" in payload:
        vulns = payload["vulnerabilities"]
        detail = f" · {len(vulns)} vuln(s): {', '.join(vulns[:2])}"
    if "reason" in payload:
        detail = f" · {payload['reason']}"

    return f"{icon}  {desc}{detail}"


# ---------------------------------------------------------------------------
# EventFeedWidget
# ---------------------------------------------------------------------------
class EventFeedWidget(QWidget):
    """
    Scrolling log of simulation events, color-coded by type.
    Updates automatically when on_state_updated() is called.
    """

    MAX_ITEMS = 200  # Cap list length to avoid memory growth

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_event_count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --- Header bar ---
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #060d18;
                border-bottom: 1px solid #0d2a42;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)

        title = QLabel("EVENT FEED")
        title.setFont(QFont("Courier New", 10, QFont.Bold))
        title.setStyleSheet("color: #00d4ff; background: transparent; border: none;")

        self._count_label = QLabel("0 events")
        self._count_label.setFont(QFont("Courier New", 8))
        self._count_label.setStyleSheet("color: #2a5070; background: transparent; border: none;")
        self._count_label.setAlignment(Qt.AlignRight)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)

        # --- Event list ---
        self._list = QListWidget()
        self._list.setFont(QFont("Courier New", 10))
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #04080f;
                border: none;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #080f1a;
                color: #aabbcc;
            }
            QListWidget::item:selected {
                background-color: #0d2a42;
                color: #ffffff;
            }
            QScrollBar:vertical {
                background: #04080f;
                width: 6px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #0d2a42;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setSpacing(1)

        layout.addWidget(header)
        layout.addWidget(self._list)

    # -----------------------------------------------------------------------
    # Public slot — called on every WebSocket snapshot
    # -----------------------------------------------------------------------
    def on_state_updated(self, snapshot: dict):
        """
        Checks recent_events in the snapshot. If there are new events
        since last update, appends them to the list.
        """
        recent_events = snapshot.get("recent_events", [])
        total = len(recent_events)

        # Only process events we haven't seen yet
        if total <= self._last_event_count:
            return

        new_events = recent_events[self._last_event_count:]
        self._last_event_count = total

        for event in new_events:
            self._add_event(event["event_type"], event.get("payload", {}))

        # Update count label
        self._count_label.setText(f"{self._list.count()} events")

    def _add_event(self, event_type: str, payload: dict):
        """Creates and appends a single event row."""
        text = format_event(event_type, payload)
        color_hex = EVENT_COLORS.get(event_type, EVENT_COLORS["DEFAULT"])

        item = QListWidgetItem(text)
        item.setForeground(QColor(color_hex))
        item.setFont(QFont("Courier New", 10))

        # Prepend so newest events are at the top
        self._list.insertItem(0, item)

        # Cap the list
        while self._list.count() > self.MAX_ITEMS:
            self._list.takeItem(self._list.count() - 1)