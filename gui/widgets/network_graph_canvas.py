# gui/widgets/network_graph_canvas.py

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsPolygonItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsDropShadowEffect, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, QLineF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath,
    QPolygonF, QRadialGradient, QLinearGradient, QFontDatabase
)


# ---------------------------------------------------------------------------
# Color palette — deep space tactical display
# ---------------------------------------------------------------------------
BG_DEEP          = "#04080f"
BG_MID           = "#060d18"
GRID_MAJOR       = "#0a1628"
GRID_MINOR       = "#070e1c"
SCANLINE_COLOR   = "#050a14"

EDGE_IDLE        = "#0d2a42"
EDGE_ACTIVE      = "#00d4ff"
EDGE_ATTACK      = "#ff2244"

SUBTEXT          = "#4a7a9b"
CORNER_ACCENT    = "#00d4ff"

STATUS_STYLES = {
    "OPERATIONAL": {
        "fill_inner":  "#020f08",
        "fill_outer":  "#041208",
        "border":      "#00ff88",
        "glow":        "#00ff88",
        "ring":        "#00cc66",
        "text":        "#00ff88",
        "label":       "#00dd66",
        "tag":         "SECURE",
    },
    "COMPROMISED_COVERT_FOOTHOLD": {
        "fill_inner":  "#150800",
        "fill_outer":  "#1a0a00",
        "border":      "#ff8800",
        "glow":        "#ff5500",
        "ring":        "#cc6600",
        "text":        "#ffaa00",
        "label":       "#ff9900",
        "tag":         "BREACH",
    },
    "CONFIRMED_BREACH_PERSISTENT_ACCESS": {
        "fill_inner":  "#180000",
        "fill_outer":  "#1e0004",
        "border":      "#ff0044",
        "glow":        "#ff0033",
        "ring":        "#cc0033",
        "text":        "#ff3366",
        "label":       "#ff1144",
        "tag":         "COMPROMISED",
    },
    "ISOLATED_QUARANTINED": {
        "fill_inner":  "#080c10",
        "fill_outer":  "#0a0f14",
        "border":      "#223344",
        "glow":        "#112233",
        "ring":        "#1a2a38",
        "text":        "#334455",
        "label":       "#223344",
        "tag":         "ISOLATED",
    },
}

NODE_TYPE_LABELS = {
    "Firewall":    "FW",
    "Server":      "SRV",
    "Workstation": "WS",
    "Router":      "RTR",
    "Database":    "DB",
}

HEX_R      = 80   # Outer hex radius
HEX_R_MID  = 68   # Middle ring radius  
HEX_R_INNER = 54  # Inner fill radius


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def hex_points(cx, cy, r, rotation=0):
    pts = []
    for i in range(6):
        a = math.radians(60 * i + rotation)
        pts.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
    return QPolygonF(pts)


# ---------------------------------------------------------------------------
# NodeItem — triple-layered hex with glow, ring, and data readout
# ---------------------------------------------------------------------------
class NodeItem(QGraphicsItem):
    """
    A fully custom node rendered with multiple hex layers:
      - Outer hex: glowing border
      - Mid hex: secondary ring (slightly rotated for depth)
      - Inner hex: dark fill with type label
      - Corner bracket decorations
      - Status tag
      - Name label below
    """

    def __init__(self, node_id, name, node_type, status):
        super().__init__()

        self.node_id   = node_id
        self.name      = name
        self.node_type = node_type
        self._status   = status
        self._pulse    = False

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(3)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # Glow effect on the whole item
        self._glow_fx = QGraphicsDropShadowEffect()
        self._glow_fx.setOffset(0, 0)
        self._glow_fx.setBlurRadius(30)
        self.setGraphicsEffect(self._glow_fx)

        self._apply_status(status)

    def _apply_status(self, status):
        self._status = status
        s = STATUS_STYLES.get(status, STATUS_STYLES["OPERATIONAL"])
        self._style = s
        self._glow_fx.setColor(QColor(s["glow"]))
        self.update()

    def set_status(self, status):
        if status != self._status:
            self._apply_status(status)

    def set_pulse(self, pulse: bool):
        self._pulse = pulse
        r = 45 if pulse else 30
        self._glow_fx.setBlurRadius(r)
        self.update()

    def boundingRect(self):
        # Generous bounding rect to include labels and glow
        return QRectF(-HEX_R - 20, -HEX_R - 20, (HEX_R + 20) * 2, HEX_R * 2 + 80)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        s = self._style

        # --- Outer hex (glowing border) ---
        outer_pen = QPen(QColor(s["border"]), 1.5)
        painter.setPen(outer_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(hex_points(0, 0, HEX_R, rotation=30))

        # --- Mid hex (rotated, dimmer) ---
        mid_color = QColor(s["border"])
        mid_color.setAlphaF(0.3)
        painter.setPen(QPen(mid_color, 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(hex_points(0, 0, HEX_R_MID, rotation=0))

        # --- Inner hex (filled) ---
        inner_grad = QRadialGradient(0, 0, HEX_R_INNER)
        inner_grad.setColorAt(0.0, QColor(s["fill_inner"]))
        inner_grad.setColorAt(1.0, QColor(s["fill_outer"]))
        painter.setPen(QPen(QColor(s["border"]), 1.0))
        painter.setBrush(QBrush(inner_grad))
        painter.drawPolygon(hex_points(0, 0, HEX_R_INNER, rotation=30))

        # --- Corner brackets (top-left and bottom-right) ---
        bracket_color = QColor(s["border"])
        bracket_color.setAlphaF(0.5)
        painter.setPen(QPen(bracket_color, 1.5))
        bw = 10
        # Top-left
        painter.drawLine(QPointF(-HEX_R - 6, -8), QPointF(-HEX_R - 6, -HEX_R + 10))
        painter.drawLine(QPointF(-HEX_R - 6, -HEX_R + 10), QPointF(-HEX_R + 4, -HEX_R + 10))
        # Bottom-right
        painter.drawLine(QPointF(HEX_R + 6, 8), QPointF(HEX_R + 6, HEX_R - 10))
        painter.drawLine(QPointF(HEX_R + 6, HEX_R - 10), QPointF(HEX_R - 4, HEX_R - 10))

        # --- Type label (center of hex) ---
        type_text = NODE_TYPE_LABELS.get(self.node_type, self.node_type[:3].upper())
        font = QFont("Courier New", 16, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(s["text"])))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(type_text)
        painter.drawText(QPointF(-tw / 2, fm.ascent() / 2 - 2), type_text)

        # --- Status tag (small, top-right of hex) ---
        tag = s["tag"]
        tag_font = QFont("Courier New", 9, QFont.Bold)
        painter.setFont(tag_font)
        tag_color = QColor(s["label"])
        painter.setPen(QPen(tag_color))
        fm2 = painter.fontMetrics()
        tw2 = fm2.horizontalAdvance(tag)
        painter.drawText(QPointF(HEX_R - tw2 + 2, -HEX_R + 8), tag)

        # --- Node name (below hex) ---
        name_font = QFont("Courier New", 11, QFont.Bold)
        painter.setFont(name_font)
        name_color = QColor(s["label"])
        painter.setPen(QPen(name_color))
        fm3 = painter.fontMetrics()
        nw = fm3.horizontalAdvance(self.name)
        painter.drawText(QPointF(-nw / 2, HEX_R + 24), self.name)

        # --- Node ID (tiny, below name) ---
        id_font = QFont("Courier New", 8)
        painter.setFont(id_font)
        id_color = QColor(SUBTEXT)
        painter.setPen(QPen(id_color))
        fm4 = painter.fontMetrics()
        iw = fm4.horizontalAdvance(self.node_id)
        painter.drawText(QPointF(-iw / 2, HEX_R + 40), self.node_id)


# ---------------------------------------------------------------------------
# EdgeItem — glowing directional line
# ---------------------------------------------------------------------------
class EdgeItem(QGraphicsPathItem):

    def __init__(self, source_node: NodeItem, target_node: NodeItem):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self._active = False
        self._attack = False
        self.setZValue(1)
        self.update_position()

    def _get_pen(self):
        if self._attack:
            pen = QPen(QColor(EDGE_ATTACK), 2.0, Qt.SolidLine)
        elif self._active:
            pen = QPen(QColor(EDGE_ACTIVE), 1.5, Qt.SolidLine)
        else:
            pen = QPen(QColor(EDGE_IDLE), 1.2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def set_active(self, active: bool, attack: bool = False):
        self._active = active
        self._attack = attack
        self.setPen(self._get_pen())

    def update_position(self):
        src = self.source_node.scenePos()
        tgt = self.target_node.scenePos()

        path = QPainterPath()
        path.moveTo(src)

        # Slight curve — offset the midpoint perpendicular to the edge
        mx = (src.x() + tgt.x()) / 2
        my = (src.y() + tgt.y()) / 2
        dx = tgt.x() - src.x()
        dy = tgt.y() - src.y()
        length = math.sqrt(dx * dx + dy * dy) or 1
        # Perpendicular offset proportional to length
        perp_scale = 0.08
        ctrl = QPointF(mx - dy * perp_scale, my + dx * perp_scale)

        path.quadTo(ctrl, tgt)
        self.setPath(path)
        self.setPen(self._get_pen())


# ---------------------------------------------------------------------------
# Background scene with scanlines + grid
# ---------------------------------------------------------------------------
class TacticalBackground(QGraphicsRectItem):
    """Draws a grid + scanline texture as the canvas background."""

    MAJOR = 80
    MINOR = 20

    def __init__(self, rect):
        super().__init__(rect)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(Qt.NoBrush))
        self.setZValue(0)

    def paint(self, painter, option, widget=None):
        rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Minor grid
        painter.setPen(QPen(QColor(GRID_MINOR), 0.5))
        x = rect.left()
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += self.MINOR
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += self.MINOR

        # Major grid
        painter.setPen(QPen(QColor(GRID_MAJOR), 1.0))
        x = rect.left()
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += self.MAJOR
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += self.MAJOR

        # Scanlines (very subtle horizontal lines)
        scan_color = QColor(SCANLINE_COLOR)
        painter.setPen(QPen(scan_color, 1.0))
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += 4  # Every 4px


# ---------------------------------------------------------------------------
# NetworkGraphCanvas — the main widget
# ---------------------------------------------------------------------------
class NetworkGraphCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-3000, -3000, 6000, 6000)

        # Background gradient
        bg_grad = QRadialGradient(0, 0, 2000)
        bg_grad.setColorAt(0.0, QColor(BG_MID))
        bg_grad.setColorAt(1.0, QColor(BG_DEEP))
        self._scene.setBackgroundBrush(QBrush(bg_grad))

        # Tactical grid
        self._bg = TacticalBackground(QRectF(-3000, -3000, 6000, 6000))
        self._scene.addItem(self._bg)

        # View
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setRenderHint(QPainter.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.ScrollHandDrag)
        self._view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._view.setStyleSheet("border: none; background: transparent;")
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.wheelEvent = self._wheel_zoom

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._node_items: dict[str, NodeItem] = {}
        self._edge_items: dict[str, EdgeItem] = {}
        self._last_statuses: dict[str, str] = {}
        self._initial_layout_done = False

        # Pulse timer
        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(900)

    def _wheel_zoom(self, event):
        factor = 1.12 if event.angleDelta().y() > 0 else 0.89
        self._view.scale(factor, factor)

    def _pulse_tick(self):
        self._pulse_state = not self._pulse_state
        for node_id, item in self._node_items.items():
            status = self._last_statuses.get(node_id, "OPERATIONAL")
            if status in ("COMPROMISED_COVERT_FOOTHOLD",
                          "CONFIRMED_BREACH_PERSISTENT_ACCESS"):
                item.set_pulse(self._pulse_state)

    # -----------------------------------------------------------------------
    # Public slot — called on every WebSocket snapshot
    # -----------------------------------------------------------------------
    def on_state_updated(self, snapshot: dict):
        network = snapshot.get("network", {})
        nodes   = network.get("nodes", [])
        edges   = network.get("edges", [])

        self._last_statuses = {
            n["id"]: n.get("current_status", "OPERATIONAL") for n in nodes
        }

        self._sync_nodes(nodes)
        self._sync_edges(edges)

        if not self._initial_layout_done and self._node_items:
            self._apply_layout()
            self._initial_layout_done = True

    def _sync_nodes(self, nodes):
        incoming = {n["id"] for n in nodes}
        for nid in list(self._node_items):
            if nid not in incoming:
                self._scene.removeItem(self._node_items.pop(nid))
        for nd in nodes:
            nid    = nd["id"]
            status = nd.get("current_status", "OPERATIONAL")
            if nid not in self._node_items:
                item = NodeItem(
                    node_id=nid,
                    name=nd.get("name", nid),
                    node_type=nd.get("node_type", "Server"),
                    status=status,
                )
                self._scene.addItem(item)
                self._node_items[nid] = item
            else:
                self._node_items[nid].set_status(status)

    def _sync_edges(self, edges):
        incoming = set()
        for ed in edges:
            src = ed.get("source", ed.get("source_node_id"))
            tgt = ed.get("target", ed.get("target_node_id"))
            key = f"{min(src,tgt)}->{max(src,tgt)}"
            incoming.add(key)

        for key in list(self._edge_items):
            if key not in incoming:
                self._scene.removeItem(self._edge_items.pop(key))

        for ed in edges:
            src = ed.get("source", ed.get("source_node_id"))
            tgt = ed.get("target", ed.get("target_node_id"))
            key = f"{min(src,tgt)}->{max(src,tgt)}"
            if key not in self._edge_items:
                si = self._node_items.get(src)
                ti = self._node_items.get(tgt)
                if si and ti:
                    ei = EdgeItem(si, ti)
                    self._scene.addItem(ei)
                    self._edge_items[key] = ei

        for ei in self._edge_items.values():
            ei.update_position()

    def _apply_layout(self):
        items = list(self._node_items.values())
        n = len(items)
        if n == 0:
            return
        if n == 1:
            items[0].setPos(0, 0)
        else:
            radius = max(220, n * 90)
            for i, item in enumerate(items):
                angle = (2 * math.pi * i) / n - math.pi / 2
                item.setPos(radius * math.cos(angle), radius * math.sin(angle))

        # Fit to NODES only — not the full 6000x6000 scene
        nodes_rect = QRectF()
        for item in self._node_items.values():
            r = item.mapToScene(item.boundingRect()).boundingRect()
            nodes_rect = nodes_rect.united(r)

        self._view.fitInView(
            nodes_rect.adjusted(-160, -160, 160, 160),
            Qt.KeepAspectRatio
        )