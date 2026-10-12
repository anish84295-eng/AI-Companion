from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QTimer, QSize
from PySide6.QtGui import QColor, QPainter, QPainterPath, QFont, QFontMetrics
from ai_companion.ui.theme import COLORS, FONTS
import textwrap


class Card(QFrame):
    def __init__(self, parent=None, radius=12):
        super().__init__(parent)
        self._radius = radius
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            QFrame#Card {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {radius}px;
            }}
            QFrame#Card:hover {{
                border-color: {COLORS['accent']};
            }}
        """)
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        self._shadow.setBlurRadius(36)
        self._shadow.setOffset(0, 7)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 4)
        super().leaveEvent(event)


class HoverPushButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(14)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        self._shadow.setBlurRadius(28)
        self._shadow.setOffset(0, 6)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow.setBlurRadius(14)
        self._shadow.setOffset(0, 3)
        super().leaveEvent(event)


class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str = "", accent: str = "accent", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._accent = COLORS.get(accent, COLORS["accent"])
        self.setMinimumSize(180, 110)
        self.setMaximumHeight(130)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 28px; font-weight: bold; border: none; background: transparent;")
        icon_wrap = QFrame()
        icon_wrap.setFixedSize(34, 34)
        icon_wrap.setStyleSheet(f"background: {self._accent}22; border: 1px solid {self._accent}33; border-radius: 17px;")
        icon_wrap_layout = QHBoxLayout(icon_wrap)
        icon_wrap_layout.setContentsMargins(0, 0, 0, 0)
        icon_wrap_layout.setAlignment(Qt.AlignCenter)
        self._icon_label = QLabel(icon)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(f"color: {self._accent}; font-size: 16px; border: none; background: transparent;")
        icon_wrap_layout.addWidget(self._icon_label)
        top = QHBoxLayout()
        top.addWidget(icon_wrap)
        top.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.addLayout(top)
        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        layout.addStretch()
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(self._shadow)
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-left: 3px solid {self._accent};
                border-radius: 12px;
            }}
            QFrame#StatCard:hover {{
                background: {COLORS['elevated']};
                border-color: {self._accent};
            }}
        """)

    def enterEvent(self, event):
        self._shadow.setBlurRadius(34)
        self._shadow.setOffset(0, 6)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 3)
        super().leaveEvent(event)

    def set_value(self, v: str):
        self._value_label.setText(v)


class Badge(QLabel):
    def __init__(self, text: str, color: str = "accent", parent=None):
        c = COLORS.get(color, COLORS["accent"])
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                background: {c}22;
                color: {c};
                border: 1px solid {c}44;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.setFixedHeight(22)


class ToggleSwitch(QWidget):
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self._checked = checked
        self._offset = 22 if checked else 2
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, v: bool):
        self._checked = v
        self._offset = 22 if v else 2
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._offset = 22 if self._checked else 2
        self.toggled.emit(self._checked)
        self.update()

    toggled = None

    def paintEvent(self, event):
        from PySide6.QtCore import Signal
        pass

    # use signal hack
    pass


# Re-implement ToggleSwitch properly with Signal
from PySide6.QtCore import Signal as _Signal

class ToggleSwitch(QWidget):
    toggled = _Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self._checked = checked
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, v: bool):
        if self._checked != v:
            self._checked = v
            self.toggled.emit(v)
            self.update()

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = COLORS["accent"] if self._checked else COLORS["border"]
        p.setBrush(QColor(bg))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 48, 26, 13, 13)
        dot_x = 26 if self._checked else 2
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(dot_x, 2, 22, 22)
        p.end()


class CodeBlock(QWidget):
    def __init__(self, code: str, language: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("CodeBlock")
        self._code = code
        self._lang = language

        header = QHBoxLayout()
        lang_label = QLabel(language or "code")
        lang_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: 600; font-family: {FONTS['mono']}; background: transparent;")
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(52, 24)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['elevated']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {COLORS['border']}; color: {COLORS['text']}; }}
        """)
        copy_btn.clicked.connect(self._copy)
        header.addWidget(lang_label)
        header.addStretch()
        header.addWidget(copy_btn)

        code_label = QLabel(code)
        code_label.setWordWrap(True)
        code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_label.setStyleSheet(f"""
            QLabel {{
                background: {COLORS['bg']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-family: {FONTS['mono']};
                font-size: 12px;
                line-height: 1.5;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(code_label)

        self.setStyleSheet(f"background: transparent; border: none;")

    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._code)
        # flash feedback
        btn = self.findChild(QPushButton)
        if btn:
            btn.setText("Copied!")
            QTimer.singleShot(1500, lambda: btn.setText("Copy"))


class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("MessageBubble")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setMaximumWidth(600)

        if is_user:
            content.setStyleSheet(f"""
                QLabel {{
                    background: {COLORS['accent']};
                    color: #FFFFFF;
                    border-radius: 14px;
                    padding: 10px 16px;
                    font-size: 13px;
                }}
            """)
            layout.addStretch()
            layout.addWidget(content)
        else:
            content.setStyleSheet(f"""
                QLabel {{
                    background: {COLORS['elevated']};
                    color: {COLORS['text']};
                    border-radius: 14px;
                    padding: 10px 16px;
                    border: 1px solid {COLORS['border']};
                    font-size: 13px;
                }}
            """)
            avatar = QLabel("\U0001F431")
            avatar.setFixedSize(32, 32)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(f"""
                QLabel {{
                    background: {COLORS['accent']};
                    border-radius: 16px;
                    font-size: 16px;
                }}
            """)
            layout.addWidget(avatar)
            layout.addWidget(content)
            layout.addStretch()


class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self._dots = [0.0, 0.0, 0.0]
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def _animate(self):
        self._phase += 0.15
        for i in range(3):
            self._dots[i] = max(0.0, min(1.0, abs(((self._phase + i * 0.4) % 2.0) - 1.0)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i in range(3):
            y = 15 - self._dots[i] * 6
            alpha = int(100 + 155 * self._dots[i])
            p.setBrush(QColor(108, 92, 231, alpha))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(10 + i * 18), int(y), 10, 10)
        p.end()

    def start(self):
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()
