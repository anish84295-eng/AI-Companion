from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor
from ai_companion.ui.theme import COLORS
from typing import Optional


class ToastNotification(QWidget):
    def __init__(self, message: str, severity: str = "info",
                 action_text: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(360)
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {COLORS.get(severity, COLORS['accent'])};
                border-radius: 10px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(msg, 1)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setFixedHeight(24)
            action_btn.setCursor(Qt.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS.get(severity, COLORS['accent'])};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background: {COLORS.get(severity, COLORS['accent'])}CC; }}
            """)
            btn_layout.addWidget(action_btn)

        dismiss_btn = QPushButton("\u2715")
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{ color: {COLORS['text']}; }}
        """)
        btn_layout.addWidget(dismiss_btn)
        layout.addLayout(btn_layout)

        self._dismiss_btn = dismiss_btn
        self._action_btn = action_btn if action_text else None

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

        self._auto_dismiss = QTimer(self)
        self._auto_dismiss.setSingleShot(True)
        self._auto_dismiss.setInterval(8000)
        self._auto_dismiss.timeout.connect(self.fade_out)
        self._auto_dismiss.start()

        dismiss_btn.clicked.connect(self.fade_out)

    def fade_out(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


class NotificationManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 600)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(8)
        self._layout.addStretch()

    def showNotification(self, message: str, severity: str = "info",
                         action_text: Optional[str] = None):
        toast = ToastNotification(message, severity, action_text, self)
        self._layout.insertWidget(0, toast)
        self.show()
        self._reposition()

    def _reposition(self):
        if self.parent():
            geo = self.parent().geometry()
            self.move(geo.right() - 420, geo.bottom() - 120)

    def clear_all(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.hide()
