from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, Signal, QObject
from ai_companion.ui.theme import COLORS


def _create_cat_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QColor(COLORS["accent"]))
    p.setPen(QColor(COLORS["accent"]))
    p.drawEllipse(14, 20, 36, 32)

    p.setBrush(QColor(COLORS["accent"]))
    tri = [QColor(COLORS["accent"])]
    from PySide6.QtGui import QPolygon
    from PySide6.QtCore import QPoint as QP
    ear_l = QPolygon([QP(16, 22), QP(10, 6), QP(26, 18)])
    ear_r = QPolygon([QP(48, 22), QP(54, 6), QP(38, 18)])
    p.drawPolygon(ear_l)
    p.drawPolygon(ear_r)

    p.setBrush(QColor("#FFFFFF"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(22, 30, 6, 6)
    p.drawEllipse(36, 30, 6, 6)

    p.setBrush(QColor(COLORS["bg"]))
    p.drawEllipse(23, 32, 4, 4)
    p.drawEllipse(37, 32, 4, 4)

    p.end()
    return QIcon(pixmap)


class SystemTray(QObject):
    show_window = Signal()
    quit_app = Signal()
    toggle_monitoring = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(_create_cat_icon(), QApplication.instance())
        self._tray.setToolTip("AI-Companion")
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #171A23;
                color: #E8EAF0;
                border: 1px solid #2A2F3D;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #6C5CE7;
            }
        """)
        show_act = menu.addAction("\u2302  Show")
        show_act.triggered.connect(self.show_window.emit)
        toggle_act = menu.addAction("\u25C9  Toggle Monitoring")
        toggle_act.triggered.connect(self.toggle_monitoring.emit)
        menu.addSeparator()
        quit_act = menu.addAction("\u2715  Quit")
        quit_act.triggered.connect(self.quit_app.emit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activate)

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window.emit()

    def show(self):
        self._tray.show()

    def hide(self):
        self._tray.hide()

    def set_tooltip(self, text: str):
        self._tray.setToolTip(text)
