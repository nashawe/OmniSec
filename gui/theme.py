# gui/theme.py

"""
Centralized theme engine for OmniSec GUI.
Provides dark/light palettes and a signal for instant theme switching.
"""

from PySide6.QtCore import QObject, Signal


DARK = {
    "name":           "dark",
    "bg":             "#1e1e2e",
    "bg_alt":         "#16161e",    # slightly darker for contrast panels
    "surface":        "#2a2a3c",
    "surface_hover":  "#333348",
    "border":         "#3a3a50",
    "border_light":   "#44445a",
    "text":           "#e8e8f0",
    "text_secondary": "#9090a8",
    "text_muted":     "#666680",
    "accent":         "#5b9cf5",
    "accent_hover":   "#7bb4ff",
    "red_team":       "#f55555",
    "blue_team":      "#55aaff",
    "green":          "#44cc88",
    "yellow":         "#ffcc44",
    "orange":         "#ff9944",

    # Graph-specific
    "graph_bg":         "#1a1a2e",
    "graph_bg_outer":   "#12121e",
    "grid_major":       "#2a2a40",
    "grid_minor":       "#1f1f30",
    "edge_idle":        "#4a5a70",
    "edge_active":      "#5b9cf5",
    "edge_attack":      "#f55555",

    # Progress bar track
    "bar_track":        "#1a1a2e",
    "bar_track_border": "#2a2a3c",

    # Scrollbar
    "scrollbar_bg":         "#1e1e2e",
    "scrollbar_handle":     "#3a3a50",
    "scrollbar_handle_hover": "#4a4a60",
}

LIGHT = {
    "name":           "light",
    "bg":             "#f2f2f7",
    "bg_alt":         "#e8e8ee",
    "surface":        "#ffffff",
    "surface_hover":  "#eaeaf0",
    "border":         "#d0d0d8",
    "border_light":   "#c0c0cc",
    "text":           "#1a1a2e",
    "text_secondary": "#606078",
    "text_muted":     "#8888a0",
    "accent":         "#3378d9",
    "accent_hover":   "#2266c0",
    "red_team":       "#d93333",
    "blue_team":      "#2277cc",
    "green":          "#22aa66",
    "yellow":         "#cc9900",
    "orange":         "#cc7722",

    # Graph-specific
    "graph_bg":         "#e8e8f0",
    "graph_bg_outer":   "#dcdce8",
    "grid_major":       "#ccccda",
    "grid_minor":       "#d8d8e4",
    "edge_idle":        "#b0b8c0",
    "edge_active":      "#3378d9",
    "edge_attack":      "#d93333",

    # Progress bar track
    "bar_track":        "#e0e0e8",
    "bar_track_border": "#d0d0d8",

    # Scrollbar
    "scrollbar_bg":         "#f2f2f7",
    "scrollbar_handle":     "#c0c0cc",
    "scrollbar_handle_hover": "#a0a0b0",
}


# Node status palettes — each status needs variants for both themes
# Dark: vibrant glowing colors on dark fills
# Light: saturated colors on pastel fills
STATUS_THEMES = {
    "OPERATIONAL": {
        "dark": {
            "fill_inner": "#0a2818", "fill_outer": "#0e3020",
            "border": "#44cc88", "glow": "#44cc88", "ring": "#33aa66",
            "text": "#44cc88", "label": "#33bb77", "tag": "SECURE",
        },
        "light": {
            "fill_inner": "#a0d8b8", "fill_outer": "#88ccaa",
            "border": "#118844", "glow": "#118844", "ring": "#0e6633",
            "text": "#0e6633", "label": "#0e6633", "tag": "SECURE",
        },
    },
    "PORT_SCANNED": {
        "dark": {
            "fill_inner": "#14142e", "fill_outer": "#1a1a38",
            "border": "#8899ff", "glow": "#7788ee", "ring": "#6677cc",
            "text": "#99aaff", "label": "#8899ee", "tag": "SCANNED",
        },
        "light": {
            "fill_inner": "#c0c0f0", "fill_outer": "#ababea",
            "border": "#3344aa", "glow": "#3344aa", "ring": "#2233aa",
            "text": "#222288", "label": "#222288", "tag": "SCANNED",
        },
    },
    "SERVICE_FINGERPRINTED": {
        "dark": {
            "fill_inner": "#1a1030", "fill_outer": "#201438",
            "border": "#bb77ff", "glow": "#9955dd", "ring": "#8844cc",
            "text": "#cc99ff", "label": "#aa66ee", "tag": "FINGERPRINTED",
        },
        "light": {
            "fill_inner": "#d8c0f0", "fill_outer": "#c8aae8",
            "border": "#5522aa", "glow": "#5522aa", "ring": "#441199",
            "text": "#441099", "label": "#441099", "tag": "FINGERPRINTED",
        },
    },
    "INITIAL_ACCESS_GAINED": {
        "dark": {
            "fill_inner": "#2a1800", "fill_outer": "#301e00",
            "border": "#ffaa33", "glow": "#ff8800", "ring": "#dd7700",
            "text": "#ffbb44", "label": "#ffaa33", "tag": "BREACH",
        },
        "light": {
            "fill_inner": "#f0d8a8", "fill_outer": "#e8c890",
            "border": "#995500", "glow": "#995500", "ring": "#884400",
            "text": "#774400", "label": "#774400", "tag": "BREACH",
        },
    },
    "PRIVILEGED_ACCESS": {
        "dark": {
            "fill_inner": "#2a0a00", "fill_outer": "#301000",
            "border": "#ff6633", "glow": "#ff4400", "ring": "#dd3300",
            "text": "#ff7744", "label": "#ff5533", "tag": "PRIV ESC",
        },
        "light": {
            "fill_inner": "#f0c0a8", "fill_outer": "#e8b090",
            "border": "#aa2200", "glow": "#aa2200", "ring": "#881800",
            "text": "#881800", "label": "#881800", "tag": "PRIV ESC",
        },
    },
    "CREDENTIALS_DUMPED": {
        "dark": {
            "fill_inner": "#2a0018", "fill_outer": "#30001e",
            "border": "#ff4488", "glow": "#ee2266", "ring": "#cc1155",
            "text": "#ff6699", "label": "#ff3377", "tag": "CREDS DUMPED",
        },
        "light": {
            "fill_inner": "#f0b0c8", "fill_outer": "#e8a0bc",
            "border": "#aa0044", "glow": "#aa0044", "ring": "#880033",
            "text": "#770033", "label": "#770033", "tag": "CREDS DUMPED",
        },
    },
    "LATERAL_ACCESS": {
        "dark": {
            "fill_inner": "#280010", "fill_outer": "#300018",
            "border": "#ff2288", "glow": "#ee0066", "ring": "#cc0055",
            "text": "#ff4499", "label": "#ff1177", "tag": "LATERAL",
        },
        "light": {
            "fill_inner": "#ffd0e4", "fill_outer": "#ffc0d8",
            "border": "#cc0055", "glow": "#cc0055", "ring": "#aa0044",
            "text": "#880033", "label": "#880033", "tag": "LATERAL",
        },
    },
    "EVASION_ACTIVE": {
        "dark": {
            "fill_inner": "#181828", "fill_outer": "#1e1e30",
            "border": "#7788aa", "glow": "#6677aa", "ring": "#556699",
            "text": "#8899bb", "label": "#7788aa", "tag": "EVASION",
        },
        "light": {
            "fill_inner": "#e0e0f0", "fill_outer": "#d4d4e8",
            "border": "#556688", "glow": "#556688", "ring": "#445577",
            "text": "#334466", "label": "#334466", "tag": "EVASION",
        },
    },
    "C2_ESTABLISHED": {
        "dark": {
            "fill_inner": "#2a0008", "fill_outer": "#300010",
            "border": "#ff2244", "glow": "#ff0033", "ring": "#dd0033",
            "text": "#ff4466", "label": "#ff2244", "tag": "C2 ACTIVE",
        },
        "light": {
            "fill_inner": "#ffd0d4", "fill_outer": "#ffc0c4",
            "border": "#cc0022", "glow": "#cc0022", "ring": "#aa0018",
            "text": "#880018", "label": "#880018", "tag": "C2 ACTIVE",
        },
    },
    "DATA_STAGED": {
        "dark": {
            "fill_inner": "#280020", "fill_outer": "#300028",
            "border": "#ff33bb", "glow": "#ee0099", "ring": "#cc0088",
            "text": "#ff55cc", "label": "#ff22bb", "tag": "DATA STAGED",
        },
        "light": {
            "fill_inner": "#f8d0f0", "fill_outer": "#f0c0e8",
            "border": "#bb0088", "glow": "#bb0088", "ring": "#990066",
            "text": "#770055", "label": "#770055", "tag": "DATA STAGED",
        },
    },
    "DATA_EXFILTRATED": {
        "dark": {
            "fill_inner": "#300000", "fill_outer": "#380008",
            "border": "#ff3333", "glow": "#ff0000", "ring": "#dd0000",
            "text": "#ff5555", "label": "#ff2222", "tag": "EXFILTRATED",
        },
        "light": {
            "fill_inner": "#ffc8c8", "fill_outer": "#ffb8b8",
            "border": "#cc0000", "glow": "#cc0000", "ring": "#aa0000",
            "text": "#880000", "label": "#880000", "tag": "EXFILTRATED",
        },
    },
    "ISOLATED_QUARANTINED": {
        "dark": {
            "fill_inner": "#141820", "fill_outer": "#181c28",
            "border": "#445566", "glow": "#334455", "ring": "#2a3a48",
            "text": "#556677", "label": "#445566", "tag": "ISOLATED",
        },
        "light": {
            "fill_inner": "#d8dce0", "fill_outer": "#ccd0d8",
            "border": "#667788", "glow": "#667788", "ring": "#556677",
            "text": "#445566", "label": "#445566", "tag": "ISOLATED",
        },
    },
}


class ThemeManager(QObject):
    """Singleton theme manager. Emits theme_changed when mode is toggled."""

    theme_changed = Signal(dict)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._mode = "dark"

    @property
    def mode(self):
        return self._mode

    def colors(self):
        return DARK if self._mode == "dark" else LIGHT

    def status_style(self, status_key: str) -> dict:
        """Returns the status style dict for the current theme mode."""
        entry = STATUS_THEMES.get(status_key, STATUS_THEMES["OPERATIONAL"])
        return entry.get(self._mode, entry["dark"])

    def toggle(self):
        self._mode = "light" if self._mode == "dark" else "dark"
        self.theme_changed.emit(self.colors())
        return self._mode

    def is_dark(self):
        return self._mode == "dark"
