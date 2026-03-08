# gui/widgets/network_graph_canvas.py

import math
import sys, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsPolygonItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsDropShadowEffect, QGraphicsPathItem, QPushButton, QFrame,
    QSlider
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, QLineF, Signal
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath,
    QPolygonF, QRadialGradient, QLinearGradient
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import ThemeManager

FONT_FAMILY = "Segoe UI"

def _font(size=13, bold=False):
    return QFont(FONT_FAMILY, size, QFont.Bold if bold else QFont.Normal)


NODE_TYPE_LABELS = {
    "Firewall":    "FW",
    "Server":      "SRV",
    "Workstation": "WS",
    "Router":      "RTR",
    "Database":    "DB",
}

HEX_R       = 80
HEX_R_MID   = 68
HEX_R_INNER = 54


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
# NodeItem
# ---------------------------------------------------------------------------
class NodeItem(QGraphicsItem):

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

        self._glow_fx = QGraphicsDropShadowEffect()
        self._glow_fx.setOffset(0, 0)
        self._glow_fx.setBlurRadius(30)
        self.setGraphicsEffect(self._glow_fx)

        self._apply_status(status)

    def _apply_status(self, status):
        self._status = status
        tm = ThemeManager.instance()
        s = tm.status_style(status)
        self._style = s
        self._glow_fx.setColor(QColor(s["glow"]))
        self.update()

    def set_status(self, status):
        if status != self._status:
            self._apply_status(status)

    def refresh_theme(self):
        """Re-apply current status with new theme colors."""
        self._apply_status(self._status)

    def set_pulse(self, pulse: bool):
        self._pulse = pulse
        r = 45 if pulse else 30
        self._glow_fx.setBlurRadius(r)
        self.update()

    def boundingRect(self):
        # Extended significantly for very large labels
        return QRectF(-HEX_R - 30, -HEX_R - 20, (HEX_R + 30) * 2, HEX_R * 2 + 150)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        s = self._style
        t = ThemeManager.instance().colors()
        is_light = ThemeManager.instance().mode == "light"

        # --- Outer hex (thicker border in light mode for contrast) ---
        outer_pen_width = 3.0 if is_light else 2.0
        painter.setPen(QPen(QColor(s["border"]), outer_pen_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(hex_points(0, 0, HEX_R, rotation=30))

        # --- Mid hex (rotated, dimmer) ---
        mid_color = QColor(s["border"])
        mid_color.setAlphaF(0.35)
        painter.setPen(QPen(mid_color, 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(hex_points(0, 0, HEX_R_MID, rotation=0))

        # --- Inner hex (filled) ---
        inner_grad = QRadialGradient(0, 0, HEX_R_INNER)
        inner_grad.setColorAt(0.0, QColor(s["fill_inner"]))
        inner_grad.setColorAt(1.0, QColor(s["fill_outer"]))
        inner_pen_width = 2.0 if is_light else 1.5
        painter.setPen(QPen(QColor(s["border"]), inner_pen_width))
        painter.setBrush(QBrush(inner_grad))
        painter.drawPolygon(hex_points(0, 0, HEX_R_INNER, rotation=30))

        # --- Corner brackets ---
        bracket_color = QColor(s["border"])
        bracket_color.setAlphaF(0.5)
        painter.setPen(QPen(bracket_color, 1.5))
        painter.drawLine(QPointF(-HEX_R - 6, -8), QPointF(-HEX_R - 6, -HEX_R + 10))
        painter.drawLine(QPointF(-HEX_R - 6, -HEX_R + 10), QPointF(-HEX_R + 4, -HEX_R + 10))
        painter.drawLine(QPointF(HEX_R + 6, 8), QPointF(HEX_R + 6, HEX_R - 10))
        painter.drawLine(QPointF(HEX_R + 6, HEX_R - 10), QPointF(HEX_R - 4, HEX_R - 10))

        # --- Type label (center) — Fix 1: 18→22pt ---
        type_text = NODE_TYPE_LABELS.get(self.node_type, self.node_type[:3].upper())
        painter.setFont(_font(22, bold=True))
        painter.setPen(QPen(QColor(s["text"])))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(type_text)
        painter.drawText(QPointF(-tw / 2, fm.ascent() / 2 - 2), type_text)

        # --- Status tag (top-right) — Fix 1: 9→11pt ---
        tag = s["tag"]
        painter.setFont(_font(11, bold=True))
        painter.setPen(QPen(QColor(s["label"])))
        fm2 = painter.fontMetrics()
        tw2 = fm2.horizontalAdvance(tag)
        painter.drawText(QPointF(HEX_R - tw2 + 2, -HEX_R + 10), tag)

        # --- Node name (below hex) — Fix 1: 18→22pt ---
        painter.setFont(_font(22, bold=True))
        painter.setPen(QPen(QColor(s["label"])))
        fm3 = painter.fontMetrics()
        nw = fm3.horizontalAdvance(self.name)
        painter.drawText(QPointF(-nw / 2, HEX_R + 36), self.name)

        # --- Node ID (below name) — 12→14pt ---
        painter.setFont(_font(14))
        painter.setPen(QPen(QColor(t["text_muted"])))
        fm4 = painter.fontMetrics()
        iw = fm4.horizontalAdvance(self.node_id)
        painter.drawText(QPointF(-iw / 2, HEX_R + 64), self.node_id)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if hasattr(self.scene(), "views") and self.scene().views():
            canvas = self.scene().views()[0].parent()
            if hasattr(canvas, "emit_node_clicked"):
                canvas.emit_node_clicked(self.node_id)



# ---------------------------------------------------------------------------
# EdgeItem
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
        t = ThemeManager.instance().colors()
        if self._attack:
            pen = QPen(QColor(t["edge_attack"]), 2.0, Qt.SolidLine)
        elif self._active:
            pen = QPen(QColor(t["edge_active"]), 1.5, Qt.SolidLine)
        else:
            pen = QPen(QColor(t["edge_idle"]), 1.2, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def set_active(self, active: bool, attack: bool = False):
        self._active = active
        self._attack = attack
        self.setPen(self._get_pen())

    def refresh_theme(self):
        self.setPen(self._get_pen())

    def update_position(self):
        src = self.source_node.scenePos()
        tgt = self.target_node.scenePos()
        path = QPainterPath()
        path.moveTo(src)
        mx = (src.x() + tgt.x()) / 2
        my = (src.y() + tgt.y()) / 2
        dx = tgt.x() - src.x()
        dy = tgt.y() - src.y()
        length = math.sqrt(dx * dx + dy * dy) or 1
        perp_scale = 0.08
        ctrl = QPointF(mx - dy * perp_scale, my + dx * perp_scale)
        path.quadTo(ctrl, tgt)
        self.setPath(path)
        self.setPen(self._get_pen())


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
class TacticalBackground(QGraphicsRectItem):
    MAJOR = 80
    MINOR = 20

    def __init__(self, rect):
        super().__init__(rect)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(Qt.NoBrush))
        self.setZValue(0)

    def paint(self, painter, option, widget=None):
        t = ThemeManager.instance().colors()
        rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Minor grid
        painter.setPen(QPen(QColor(t["grid_minor"]), 0.5))
        x = rect.left()
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += self.MINOR
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += self.MINOR

        # Major grid
        painter.setPen(QPen(QColor(t["grid_major"]), 1.0))
        x = rect.left()
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += self.MAJOR
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += self.MAJOR


# ---------------------------------------------------------------------------
# NetworkGraphCanvas
# ---------------------------------------------------------------------------
class NetworkGraphCanvas(QWidget):

    # Signal emitted when zoom changes so control bar can sync slider
    zoom_changed = Signal(float)
    node_clicked = Signal(str)

    def emit_node_clicked(self, node_id: str):
        self.node_clicked.emit(node_id)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-3000, -3000, 6000, 6000)

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
        self._view.viewport().installEventFilter(self)

        self._view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self._pulse_timer.start(900)

        self._apply_bg()

    def _apply_bg(self):
        t = ThemeManager.instance().colors()
        bg_grad = QRadialGradient(0, 0, 2000)
        bg_grad.setColorAt(0.0, QColor(t["graph_bg"]))
        bg_grad.setColorAt(1.0, QColor(t["graph_bg_outer"]))
        self._scene.setBackgroundBrush(QBrush(bg_grad))

    def apply_theme(self):
        """Re-style everything when theme changes."""
        self._apply_bg()
        self._bg.update()  # Repaint the grid
        for item in self._node_items.values():
            item.refresh_theme()
        for item in self._edge_items.values():
            item.refresh_theme()

    # --- Fix 4: Smooth damped trackpad zoom ---
    def _wheel_zoom(self, event):
        # Use pixelDelta for trackpad (smooth), angleDelta for mouse wheel
        pixel_y = event.pixelDelta().y()
        angle_y = event.angleDelta().y()

        if pixel_y != 0:
            # Trackpad: very small increment per pixel for fine control
            factor = 1.0 + pixel_y * 0.002
        elif angle_y != 0:
            # Mouse wheel: slightly larger steps
            factor = 1.0 + angle_y * 0.001
        else:
            return

        # Clamp per-event zoom to prevent wild jumps
        factor = max(0.92, min(1.08, factor))

        self._view.scale(factor, factor)

        # Notify the control bar slider
        scale = self._view.transform().m11()
        self.zoom_changed.emit(scale)

    def set_zoom_level(self, scale_factor):
        current_transform = self._view.transform()
        m11 = current_transform.m11()
        if m11 == 0:
            return
        factor = scale_factor / m11
        self._view.scale(factor, factor)

    def zoom_in(self):
        self._view.scale(1.15, 1.15)
        scale = self._view.transform().m11()
        self.zoom_changed.emit(scale)

    def zoom_out(self):
        self._view.scale(1 / 1.15, 1 / 1.15)
        scale = self._view.transform().m11()
        self.zoom_changed.emit(scale)

    def reset_view(self):
        if not self._node_items:
            return
        rect = self._scene.itemsBoundingRect()
        if not rect.isNull():
            rect.adjust(-100, -100, 100, 100)
            self._view.fitInView(rect, Qt.KeepAspectRatio)
            scale = self._view.transform().m11()
            self.zoom_changed.emit(scale)

    def clear(self):
        """Fix 5: Remove all nodes and edges, reset state."""
        self._pulse_timer.stop()
        # Remove from scene
        for item in self._node_items.values():
            if item.scene() == self._scene:
                self._scene.removeItem(item)
        for item in self._edge_items.values():
            if item.scene() == self._scene:
                self._scene.removeItem(item)
        self._node_items.clear()
        self._edge_items.clear()
        self._last_statuses.clear()
        self._initial_layout_done = False
        self._pulse_timer.start(900)


    def _pulse_tick(self):
        self._pulse_state = not self._pulse_state
        _PULSE_STATUSES = {
            "INITIAL_ACCESS_GAINED", "PRIVILEGED_ACCESS", "CREDENTIALS_DUMPED",
            "LATERAL_ACCESS", "C2_ESTABLISHED", "DATA_STAGED", "DATA_EXFILTRATED",
        }
        for node_id, item in self._node_items.items():
            status = self._last_statuses.get(node_id, "OPERATIONAL")
            if status in _PULSE_STATUSES:
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

        nodes_rect = QRectF()
        for item in self._node_items.values():
            r = item.mapToScene(item.boundingRect()).boundingRect()
            nodes_rect = nodes_rect.united(r)

        self._view.fitInView(
            nodes_rect.adjusted(-160, -160, 160, 160),
            Qt.KeepAspectRatio
        )