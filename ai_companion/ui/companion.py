from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import (
    Qt, QTimer, QPoint, QPointF, QPropertyAnimation, QEasingCurve,
    Property, QRectF, Signal
)
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QRadialGradient, QPen,
    QPainterPath, QFont, QPixmap, QImage, qRgba, QAction, QCursor
)
from ai_companion.ui.theme import COLORS
from ai_companion.core.database import get_setting
from ai_companion.core.paths import data_path, resource_path
import math
import json
import time
from pathlib import Path


class ErrorPopup(QWidget):
    viewClicked = Signal()
    askAIClicked = Signal(dict)
    pauseClicked = Signal()
    dismissClicked = Signal()

    def __init__(self, error_type: str, description: str, error_info: dict = None, parent=None):
        super().__init__(parent)
        self._error_info = error_info or {}
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(300)
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {COLORS['danger']}; border-radius: 4px; border: none;")
        header.addWidget(dot)

        title = QLabel(error_type)
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        header.addWidget(title, 1)
        layout.addLayout(header)

        desc = QLabel(description[:150])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        for text, signal in [("View", self.viewClicked), ("Ask AI", self.askAIClicked), ("Pause", self.pauseClicked), ("Ignore", self.dismissClicked)]:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            if text == "Ask AI":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['accent']};
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
                """)
                btn.clicked.connect(lambda checked, info=self._error_info: self.askAIClicked.emit(info))
            elif text == "Pause":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['warning']};
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{ background: {COLORS.get('warning_hover', COLORS['warning'])}; }}
                """)
                btn.clicked.connect(signal)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['elevated']};
                        color: {COLORS['text']};
                        border: 1px solid {COLORS['border']};
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{ background: {COLORS['border']}; }}
                """)
                btn.clicked.connect(signal)
            btn_layout.addWidget(btn)

        dismiss_btn = QPushButton("\u2715")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{ color: {COLORS['danger']}; }}
        """)
        dismiss_btn.clicked.connect(self.dismissClicked)
        btn_layout.addWidget(dismiss_btn)

        layout.addLayout(btn_layout)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(COLORS['surface']))
        p.setPen(QColor(COLORS['border']))
        p.drawRoundedRect(self.rect(), 10, 10)
        p.end()


def _paint_cat_static(p: QPainter, cx: float, cy: float):
    _ORANGE = "#E8943A"
    _ORANGE_D = "#C87830"
    _ORANGE_DD = "#A86020"
    _CREAM = "#F5E6D0"
    _CREAM_D = "#E8D4B8"
    _PINK = "#E8929A"
    _EYE_G = "#5A8A3C"
    _PUPIL = "#2A1A0A"
    _NOSE = "#E07080"

    tail = QPainterPath()
    tail.moveTo(cx - 20, cy + 18)
    tail.cubicTo(cx - 34, cy + 8, cx - 38, cy - 8, cx - 30, cy - 18)
    p.setPen(QPen(QColor(_ORANGE), 7, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(tail)

    p.setBrush(QBrush(QColor(_ORANGE)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(cx - 18, cy + 4, 36, 28))

    p.setBrush(QBrush(QColor(_CREAM)))
    p.drawEllipse(QRectF(cx - 10, cy + 10, 20, 18))

    p.setBrush(QBrush(QColor(_CREAM_D)))
    p.drawEllipse(QRectF(cx - 16, cy + 26, 12, 8))
    p.drawEllipse(QRectF(cx + 4, cy + 26, 12, 8))

    hg = QRadialGradient(cx - 1, cy - 16, 22)
    hg.setColorAt(0, _ORANGE)
    hg.setColorAt(1, _ORANGE_D)
    p.setBrush(QBrush(hg))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(cx - 20, cy - 32, 40, 34))

    mg = QRadialGradient(cx, cy - 14, 10)
    mg.setColorAt(0, QColor(_CREAM))
    mg.setColorAt(1, QColor(_CREAM_D))
    p.setBrush(QBrush(mg))
    p.drawEllipse(QRectF(cx - 9, cy - 18, 18, 14))

    ear_lo = QPainterPath()
    ear_lo.moveTo(cx - 16, cy - 28)
    ear_lo.lineTo(cx - 20, cy - 44)
    ear_lo.quadTo(cx - 14, cy - 47, cx - 8, cy - 42)
    ear_lo.lineTo(cx - 4, cy - 30)
    ear_lo.closeSubpath()
    ear_ro = QPainterPath()
    ear_ro.moveTo(cx + 16, cy - 28)
    ear_ro.lineTo(cx + 20, cy - 44)
    ear_ro.quadTo(cx + 14, cy - 47, cx + 8, cy - 42)
    ear_ro.lineTo(cx + 4, cy - 30)
    ear_ro.closeSubpath()
    p.setBrush(QBrush(QColor(_ORANGE_D)))
    p.setPen(Qt.NoPen)
    p.drawPath(ear_lo)
    p.drawPath(ear_ro)

    ear_li = QPainterPath()
    ear_li.moveTo(cx - 14, cy - 30)
    ear_li.lineTo(cx - 17, cy - 40)
    ear_li.quadTo(cx - 13, cy - 42, cx - 9, cy - 39)
    ear_li.lineTo(cx - 7, cy - 31)
    ear_li.closeSubpath()
    ear_ri = QPainterPath()
    ear_ri.moveTo(cx + 14, cy - 30)
    ear_ri.lineTo(cx + 17, cy - 40)
    ear_ri.quadTo(cx + 13, cy - 42, cx + 9, cy - 39)
    ear_ri.lineTo(cx + 7, cy - 31)
    ear_ri.closeSubpath()
    p.setBrush(QBrush(QColor(_PINK)))
    p.setPen(Qt.NoPen)
    p.drawPath(ear_li)
    p.drawPath(ear_ri)

    p.setBrush(QBrush(QColor(_EYE_G)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(cx - 9, cy - 20, 5.5, 6))
    p.drawEllipse(QRectF(cx + 3.5, cy - 20, 5.5, 6))

    p.setBrush(QBrush(QColor(_PUPIL)))
    p.drawEllipse(QRectF(cx - 7.5, cy - 19, 3, 4))
    p.drawEllipse(QRectF(cx + 5, cy - 19, 3, 4))

    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(QRectF(cx - 6.5, cy - 18.5, 1.3, 1.3))
    p.drawEllipse(QRectF(cx + 6, cy - 18.5, 1.3, 1.3))

    np_ = QPainterPath()
    np_.moveTo(cx, cy - 12)
    np_.lineTo(cx - 2.2, cy - 10)
    np_.quadTo(cx, cy - 9, cx + 2.2, cy - 10)
    np_.closeSubpath()
    p.setBrush(QBrush(QColor(_NOSE)))
    p.setPen(Qt.NoPen)
    p.drawPath(np_)

    mp = QPen(QColor(_ORANGE_DD), 1, Qt.SolidLine, Qt.RoundCap)
    p.setPen(mp)
    p.setBrush(Qt.NoBrush)
    ml = QPainterPath()
    ml.moveTo(cx - 3, cy - 8)
    ml.quadTo(cx - 1, cy - 5.5, cx, cy - 6)
    p.drawPath(ml)
    mr = QPainterPath()
    mr.moveTo(cx + 3, cy - 8)
    mr.quadTo(cx + 1, cy - 5.5, cx, cy - 6)
    p.drawPath(mr)

    wp = QPen(QColor(_CREAM_D), 0.5, Qt.SolidLine, Qt.RoundCap)
    p.setPen(wp)
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(cx - 18, cy - 14), QPointF(cx - 11, cy - 13))
    p.drawLine(QPointF(cx - 17, cy - 12), QPointF(cx - 11, cy - 11.5))
    p.drawLine(QPointF(cx + 18, cy - 14), QPointF(cx + 11, cy - 13))
    p.drawLine(QPointF(cx + 17, cy - 12), QPointF(cx + 11, cy - 11.5))


def _render_cat_base_pixmap() -> QPixmap:
    pm = QPixmap(140, 140)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _paint_cat_static(p, 70, 72)
    p.end()
    return pm


def _strip_black_background(pm: QPixmap, threshold: int = 15) -> QPixmap:
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    out = QImage(w, h, QImage.Format_ARGB32)
    out.fill(0)
    for y in range(h):
        for x in range(w):
            rgb = img.pixel(x, y)
            r = (rgb >> 16) & 0xFF
            g = (rgb >> 8) & 0xFF
            b = rgb & 0xFF
            if r >= threshold or g >= threshold or b >= threshold:
                out.setPixel(x, y, qRgba(r, g, b, 255))
    _remove_vertical_line_artifacts(out)
    return QPixmap.fromImage(out)


def _remove_vertical_line_artifacts(img: QImage):
    w, h = img.width(), img.height()
    if h < 10:
        return
    cols_to_strip = []
    for x in range(w):
        white_count = 0
        for y in range(h):
            rgb = img.pixel(x, y)
            if ((rgb >> 24) & 0xFF) == 0:
                continue
            r = (rgb >> 16) & 0xFF
            g = (rgb >> 8) & 0xFF
            b = rgb & 0xFF
            if r > 240 and g > 240 and b > 240:
                white_count += 1
        if white_count > h * 0.80:
            cols_to_strip.append(x)
    for x in cols_to_strip:
        for y in range(h):
            rgb = img.pixel(x, y)
            if ((rgb >> 24) & 0xFF) > 0:
                r = (rgb >> 16) & 0xFF
                g = (rgb >> 8) & 0xFF
                b = rgb & 0xFF
                if r > 240 and g > 240 and b > 240:
                    img.setPixel(x, y, qRgba(r, g, b, 0))


class FloatingCat(QWidget):
    chat_requested = Signal()
    errorAsked = Signal(dict)
    pauseRequested = Signal()
    dashboard_requested = Signal()
    menu_requested = Signal()
    viewRequested = Signal()
    window_requested = Signal()
    dblClicked = Signal()
    errorClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(140, 140)
        self._state = "idle"
        self._phase = 0.0
        self._ring_angle = 0.0
        self._pulse = 0.0
        self._shake_x = 0.0
        self._drag_pos = None
        self._dragging = False
        self._unread_count = 0

        self._popup = None
        self._press_pos = None
        self._last_click_pos = None
        self._last_click_ts = 0.0
        self._single_timer = QTimer(self)
        self._single_timer.setSingleShot(True)
        self._single_timer.setInterval(QApplication.doubleClickInterval() + 60)
        self._single_timer.timeout.connect(self._fire_single_click)

        self._cat_pixmap = QPixmap()
        self._load_cat_pixmap()

        self._config_path = data_path("cat_position.json")
        self._load_position()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)

    def _load_cat_pixmap(self):
        try:
            pet_file = get_setting("companion_pet", "blue_tabby_pet1.png")
            if pet_file == "blue_tabby_pet.png":
                pet_file = "blue_tabby_pet1.png"
            asset = resource_path("assets", "companion", pet_file)
            if not asset.exists():
                asset = resource_path("assets", "companion", "blue_tabby_pet1.png")
            if not asset.exists():
                asset.parent.mkdir(parents=True, exist_ok=True)
                _render_cat_base_pixmap().save(str(asset), "PNG")
            raw = QPixmap(str(asset))
            if not raw.isNull():
                scaled = raw.scaled(
                    140, 140,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._cat_pixmap = _strip_black_background(scaled)
            else:
                self._cat_pixmap = QPixmap()
        except Exception:
            self._cat_pixmap = QPixmap()

    def refresh_pet(self):
        self._load_cat_pixmap()
        self.update()

    def _default_position(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return 100, 100
        geo = screen.availableGeometry()
        x = geo.x() + geo.width() - self.width() - 40
        y = geo.y() + geo.height() // 3
        return int(x), int(y)

    def _load_position(self):
        try:
            x, y = self._default_position()
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text())
                x = int(data.get("x", x))
                y = int(data.get("y", y))
            from PySide6.QtCore import QRect
            screen = QApplication.primaryScreen()
            if screen is None:
                self.move(100, 100)
                return
            geo = screen.availableGeometry()
            test_rect = QRect(int(x), int(y), self.width(), self.height())
            if geo.contains(test_rect, True) and int(x) >= 0 and int(y) >= 0:
                self.move(int(x), int(y))
            else:
                dx, dy = self._default_position()
                self.move(dx, dy)
        except Exception:
            dx, dy = self._default_position()
            self.move(dx, dy)

    def _save_position(self):
        try:
            self._config_path.write_text(json.dumps({
                "x": self.x(), "y": self.y()
            }))
        except Exception:
            pass

    def setState(self, state: str):
        self._state = state
        self.update()

    def setUnreadCount(self, count: int):
        self._unread_count = count
        self.update()

    def showNotificationPopup(self, error_type: str, description: str, error_info: dict = None):
        self._close_popup()
        self._popup = ErrorPopup(error_type, description, error_info=error_info)
        self._popup.viewClicked.connect(self._on_popup_view)
        self._popup.askAIClicked.connect(self._on_popup_ask_ai)
        self._popup.pauseClicked.connect(self._on_popup_pause)
        self._popup.dismissClicked.connect(self._close_popup)
        self._position_popup()
        self._popup.show()
        self._popup.raise_()

    def _position_popup(self):
        if not self._popup:
            return
        cat_pos = self.pos()
        cat_size = self.size()
        screen = QApplication.primaryScreen().geometry()
        popup_w = self._popup.width()
        popup_h = self._popup.height()
        x = cat_pos.x() - popup_w - 10
        y = cat_pos.y()
        if x < screen.x() + 10:
            x = cat_pos.x() + cat_size.width() + 10
        if y + popup_h > screen.y() + screen.height() - 10:
            y = screen.y() + screen.height() - popup_h - 10
        if y < screen.y() + 10:
            y = screen.y() + 10
        self._popup.move(x, y)

    def _close_popup(self):
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None

    def _on_popup_view(self):
        self._close_popup()
        self.viewRequested.emit()

    def _on_popup_ask_ai(self, error_info: dict = None):
        self._close_popup()
        if error_info:
            self.errorAsked.emit(error_info)
        else:
            self.chat_requested.emit()

    def _on_popup_pause(self):
        self._close_popup()
        self.pauseRequested.emit()

    def _animate(self):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = 70
        cy = 72

        _ACCENT = COLORS["accent"]
        _DANGER = COLORS["danger"]

        if self._state == "alert":
            glow = QRadialGradient(cx, cy + 12, 60)
            glow.setColorAt(0, QColor(255, 80, 80, 45))
            glow.setColorAt(1, QColor(255, 80, 80, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(cx - 60, cy - 50, 120, 120))

        if self._state == "analyzing":
            rp = QPen(QColor(_ACCENT), 2.5, Qt.SolidLine)
            rp.setCapStyle(Qt.RoundCap)
            p.setPen(rp)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - 44, cy - 34, 88, 88), 0, int(270 * 16))

        if self._cat_pixmap and not self._cat_pixmap.isNull():
            pw = self._cat_pixmap.width()
            ph = self._cat_pixmap.height()
            px = (140 - pw) // 2
            py = (140 - ph) // 2
            p.drawPixmap(px, py, self._cat_pixmap)
        else:
            _paint_cat_static(p, 70, 72)

        if self._state == "thinking":
            accent_rgb = QColor(_ACCENT)
            for i in range(3):
                dy = cy - 48 - (i * 7)
                p.setBrush(QBrush(QColor(accent_rgb.red(), accent_rgb.green(), accent_rgb.blue(), 200)))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QRectF(cx + 28 + i * 6, dy, 4, 4))

        if self._unread_count > 0:
            bx = cx + 26
            by = cy - 50
            br = 12
            p.setBrush(QBrush(QColor(_DANGER)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(bx - br, by - br, br * 2, br * 2))
            txt = str(min(self._unread_count, 99))
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Inter", 9, QFont.Bold))
            p.drawText(QRectF(bx - br, by - br, br * 2, br * 2), Qt.AlignCenter, txt)

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            self._dragging = False
            self._single_timer.stop()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._single_timer.stop()
            self.menu_requested.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            if self._press_pos is not None:
                moved = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
                if moved > QApplication.startDragDistance():
                    self._dragging = True
                    self._single_timer.stop()
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            if self._popup:
                self._position_popup()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._single_timer.stop()
            if self._dragging:
                self._drag_pos = None
                self._press_pos = None
                self._dragging = False
                self._save_position()
                event.accept()
                return
            now = time.monotonic()
            pos = event.globalPosition().toPoint()
            if (self._last_click_pos is not None
                    and (now - self._last_click_ts) <= self._single_timer.interval() / 1000.0
                    and (pos - self._last_click_pos).manhattanLength() <= 60):
                self._last_click_pos = None
                self._last_click_ts = 0.0
                self._drag_pos = None
                self._press_pos = None
                self._save_position()
                self.dblClicked.emit()
                event.accept()
                return
            self._last_click_pos = pos
            self._last_click_ts = now
            self._single_timer.start()
        self._drag_pos = None
        self._press_pos = None
        self._dragging = False
        self._save_position()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._single_timer.stop()
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            self._press_pos = event.globalPosition().toPoint()
            self._dragging = False
        event.accept()

    def _fire_single_click(self):
        if self._popup and self._popup.isVisible():
            self._popup.hide()
        elif self._popup:
            self._position_popup()
            self._popup.show()
            self._popup.raise_()
        else:
            self.window_requested.emit()

    def popup(self):
        return self._popup

    def raisePopup(self):
        if self._popup:
            self._position_popup()
            self._popup.show()
            self._popup.raise_()

    def showEvent(self, event):
        super().showEvent(event)

    def show_with_state(self, state: str = "idle"):
        self.setState(state)
        self.show()
