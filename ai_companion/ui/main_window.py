from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QSizePolicy, QSpacerItem,
    QGraphicsDropShadowEffect, QScrollArea, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QInputDialog, QDialog, QTextEdit,
    QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize, QDateTime
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont, QImage
from ai_companion.ui.theme import COLORS, FONTS, THEMES, apply_theme, apply_dark_theme, apply_light_theme, apply_named_theme
from ai_companion.ui.widgets import Card, StatCard, Badge, ToggleSwitch, CodeBlock, MessageBubble, TypingIndicator, HoverPushButton
from ai_companion.ui.companion import FloatingCat
from ai_companion.ui.toasts import NotificationManager
from ai_companion.ui.tray import SystemTray
from ai_companion.core.database import (
    init_db, get_conversations, get_all_settings, get_all_memory,
    save_memory, delete_memory, load_history, clear_history,
    save_settings, get_setting, get_messages_for_conversation,
    purge_generic_history
)
from ai_companion.core.screen_monitor import ScreenMonitor
from ai_companion.core.error_detector import ErrorDetector
from ai_companion.core.file_watcher import FileWatcher
from ai_companion.core.chat_manager import ChatManager
from ai_companion.core.ai_engine import AIRequestThread
from ai_companion.core.vision_analyzer import VisionAnalyzer
from ai_companion.core.context_engine import ContextEngine
from ai_companion.core.config import get_api_key, get_provider, set_provider, set_api_key, set_model, set_base_url, test_connection, get_model, get_base_url, _ENV_PATH
from dotenv import load_dotenv
import time
import os
import re


class SidebarButton(QPushButton):
    def __init__(self, text: str, icon_char: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._icon_char = icon_char
        self._active = False
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("NavBtn")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 16, 0)
        layout.setSpacing(12)

        self._icon_badge = QLabel(icon_char)
        self._icon_badge.setFixedSize(30, 30)
        self._icon_badge.setAlignment(Qt.AlignCenter)
        self._icon_badge.setObjectName("navIcon")

        self._label = QLabel(text)
        self._label.setObjectName("navLabel")
        layout.addWidget(self._icon_badge)
        layout.addWidget(self._label, 1)

        self._update_style()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton#NavBtn {{
                    background: {COLORS['accent']}14;
                    border: none;
                    border-left: 3px solid {COLORS['accent']};
                    border-radius: 0px;
                }}
                QLabel#navIcon {{
                    background: {COLORS['accent']};
                    color: #FFFFFF;
                    border-radius: 15px;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                }}
                QLabel#navLabel {{
                    color: {COLORS['accent']};
                    font-size: 13px;
                    font-weight: 600;
                    border: none;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton#NavBtn {{
                    background: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                }}
                QPushButton#NavBtn:hover {{
                    background: {COLORS['elevated']};
                }}
                QLabel#navIcon {{
                    background: {COLORS['elevated']};
                    color: {COLORS['text_secondary']};
                    border-radius: 15px;
                    font-size: 14px;
                    border: none;
                }}
                QPushButton#NavBtn:hover QLabel#navIcon {{
                    background: {COLORS['accent']}22;
                    color: {COLORS['accent']};
                }}
                QLabel#navLabel {{
                    color: {COLORS['text_secondary']};
                    font-size: 13px;
                    border: none;
                    background: transparent;
                }}
                QPushButton#NavBtn:hover QLabel#navLabel {{
                    color: {COLORS['text']};
                }}
            """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        purge_generic_history()
        self.setWindowTitle("AI-Companion")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._drag_pos = None
        self._start_time = time.time()
        self._error_count = 0
        self._chat_count = 0
        self._last_error_info = None
        self._last_ocr_text = ""
        self._active_fingerprint = None
        self._clean_frames = 0
        self._paused_fingerprints = set()
        self._test_thread = None

        try:
            if get_setting("theme", "") in THEMES:
                _startup_theme = get_setting("theme")
            else:
                _startup_theme = "Dark" if get_setting("dark_mode", "0") == "1" else "Light"
        except Exception:
            _startup_theme = "Light"
        apply_named_theme(self, _startup_theme)

        self._monitor = ScreenMonitor(parent=self)
        self._detector = ErrorDetector()
        self._watcher = FileWatcher(self)
        self._chat_mgr = ChatManager(self)
        self._vision = VisionAnalyzer(self)
        self._context = ContextEngine()

        central = QWidget()
        central.setStyleSheet(f"background: {COLORS['bg']};")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_bar = self._build_title_bar()
        root_layout.addWidget(title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        sidebar = self._build_sidebar()
        body.addWidget(sidebar)

        self._content_area = QStackedWidget()
        self._content_area.setStyleSheet(f"background: {COLORS['bg']};")
        body.addWidget(self._content_area, 1)

        root_layout.addLayout(body, 1)

        self._build_pages()

        self._nav_buttons = []
        pages_info = [
            ("Dashboard", "\u2302", 0),
            ("Chat", "\u2709", 1),
            ("Monitoring", "\u25C9", 2),
            ("History", "\u231B", 3),
            ("Memory", "\u2637", 4),
            ("Settings", "\u2699", 5),
        ]
        for name, icon, idx in pages_info:
            btn = SidebarButton(name, icon)
            btn.clicked.connect(lambda checked, i=idx, b=btn: self._switch_page(i, b))
            self._nav_buttons.append(btn)
            self._nav_layout.addWidget(btn)

        self._companion = FloatingCat()
        self._companion.chat_requested.connect(self._on_companion_chat)
        self._companion.errorAsked.connect(self._on_companion_error_asked)
        self._companion.pauseRequested.connect(self._on_companion_pause_requested)
        self._companion.dashboard_requested.connect(self._on_companion_dashboard)
        self._companion.menu_requested.connect(self._on_companion_menu)
        self._companion.viewRequested.connect(self._on_companion_view)
        self._companion.window_requested.connect(self._show_from_tray)
        self._companion.dblClicked.connect(self._on_companion_dbl_click)

        self._notifications = NotificationManager(self)

        self._tray = SystemTray(self)
        self._tray.show_window.connect(self._show_from_tray)
        self._tray.quit_app.connect(self._quit_app)
        self._tray.toggle_monitoring.connect(self._toggle_monitoring_from_tray)

        self._monitor.frameCaptured.connect(self._on_frame_captured)
        self._monitor.errorDetected.connect(self._on_monitor_error)
        self._monitor.statusChanged.connect(self._on_monitor_status)
        self._monitor.error.connect(lambda e: self._notifications.showNotification(e, "danger"))

        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.errorFound.connect(self._on_watcher_error)

        self._chat_mgr.responseReceived.connect(self._on_chat_response)
        self._chat_mgr.error.connect(lambda e: self._notifications.showNotification(e, "danger"))

        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(60000)

        self._switch_page(0, self._nav_buttons[0])
        self.showDashboard()
        self._update_ai_status()

        self._tray.show()
        self._companion.show()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(232)
        sidebar.setObjectName("Sidebar")
        sidebar.setStyleSheet(f"""
            QFrame#Sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['sidebar_top']}, stop:1 {COLORS['sidebar_bottom']});
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        self._sidebar = sidebar
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._nav_layout = QVBoxLayout()
        self._nav_layout.setContentsMargins(0, 12, 0, 0)
        self._nav_layout.setSpacing(2)
        layout.addLayout(self._nav_layout, 1)

        status_card = QFrame()
        status_card.setObjectName("StatusCard")
        status_card.setFixedHeight(72)
        status_card.setStyleSheet(f"""
            QFrame#StatusCard {{
                background: {COLORS['sidebar_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin: 8px 12px 12px 12px;
            }}
        """)
        self._status_card = status_card
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(8)

        mon_row = QHBoxLayout()
        mon_row.setSpacing(8)
        self._monitor_dot = QLabel()
        self._monitor_dot.setFixedSize(8, 8)
        self._monitor_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 4px; border: none;")
        self._monitor_status = QLabel("Monitoring: Off")
        self._monitor_status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        mon_row.addWidget(self._monitor_dot)
        mon_row.addWidget(self._monitor_status)
        mon_row.addStretch()
        status_layout.addLayout(mon_row)

        ai_row = QHBoxLayout()
        ai_row.setSpacing(8)
        self._ai_dot = QLabel()
        self._ai_dot.setFixedSize(8, 8)
        self._ai_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 4px; border: none;")
        self._ai_status = QLabel("AI: Disconnected")
        self._ai_status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        ai_row.addWidget(self._ai_dot)
        ai_row.addWidget(self._ai_status)
        ai_row.addStretch()
        status_layout.addLayout(ai_row)

        status_wrap = QVBoxLayout()
        status_wrap.setContentsMargins(0, 0, 0, 0)
        status_wrap.setSpacing(0)
        status_wrap.addWidget(status_card)
        layout.addLayout(status_wrap)

        return sidebar

    def _build_title_bar(self):
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        logo = QLabel("\U0001F431 AI-Companion")
        logo.setStyleSheet(f"color: {COLORS['accent']}; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(logo)
        layout.addStretch()

        for char, slot in [("\u2014", self.showMinimized), ("\u25A1", self._toggle_max), ("\u2715", self.close)]:
            btn = QPushButton(char)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background: {COLORS['elevated']};
                    color: {COLORS['text']};
                }}
            """)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
        return bar

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _switch_page(self, index: int, active_btn: SidebarButton):
        self._content_area.setCurrentIndex(index)
        for btn in self._nav_buttons:
            btn.set_active(False)
        active_btn.set_active(True)

    def _build_pages(self):
        self._content_area.addWidget(self._dashboard_page())
        self._content_area.addWidget(self._chat_page())
        self._content_area.addWidget(self._monitoring_page())
        self._content_area.addWidget(self._history_page())
        self._content_area.addWidget(self._memory_page())
        self._content_area.addWidget(self._settings_page())

    # ════════════════════════════════════════════════════════
    # Dashboard
    # ════════════════════════════════════════════════════════

    def _dashboard_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("AI-Companion")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 30px; font-weight: 800; border: none; background: transparent;")
        header.addWidget(title)
        tagline = QLabel("Your AI-powered programming assistant.")
        tagline.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        header.addWidget(tagline)
        layout.addLayout(header)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        self._stat_errors = StatCard("Errors Found", "0", "⚠", "danger")
        self._stat_chats = StatCard("Chats", "0", "✉", "accent")
        self._stat_fixes = StatCard("Fixes Applied", "0", "✔", "success")
        self._stat_uptime = StatCard("Uptime", "0m", "⏱", "warning")
        for sc in [self._stat_errors, self._stat_chats, self._stat_fixes, self._stat_uptime]:
            stats_layout.addWidget(sc)
        layout.addLayout(stats_layout)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(16)

        recent_card = Card()
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setContentsMargins(20, 16, 20, 16)
        rc_title = QLabel("Recent Errors")
        rc_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        rc_layout.addWidget(rc_title)
        self._recent_errors_list = QVBoxLayout()
        self._recent_errors_list.setSpacing(8)
        self._recent_errors_placeholder = QLabel("No errors detected yet")
        self._recent_errors_placeholder.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
        self._recent_errors_list.addWidget(self._recent_errors_placeholder)
        rc_layout.addLayout(self._recent_errors_list)
        mid_layout.addWidget(recent_card, 1)

        tips_card = Card()
        tips_card.setFixedWidth(270)
        tc_layout = QVBoxLayout(tips_card)
        tc_layout.setContentsMargins(20, 16, 20, 16)
        tc_layout.setSpacing(10)
        tips_title = QLabel("Quick Tips")
        tips_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        tc_layout.addWidget(tips_title)
        tips = [
            "Enable monitoring on the Monitoring page to get automatic error detection while you code.",
            "Click Ask AI on any error popup for an instant explanation of what went wrong.",
            "Switch your companion pet in Settings → Companion Pet.",
        ]
        for tip in tips:
            tip_label = QLabel(f"•  {tip}")
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
            tc_layout.addWidget(tip_label)
        tc_layout.addStretch()
        mid_layout.addWidget(tips_card)

        layout.addLayout(mid_layout, 1)

        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(12)
        for text, slot in [("Start Monitoring", self.showScreenContext), ("New Chat", self.showChat), ("View History", self.showHistory)]:
            btn = HoverPushButton(text)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
                QPushButton:pressed {{ background: {COLORS['accent_pressed']}; }}
            """)
            btn.clicked.connect(slot)
            quick_layout.addWidget(btn)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        return w

    def _update_uptime(self):
        elapsed = int(time.time() - self._start_time)
        minutes = elapsed // 60
        hours = minutes // 60
        if hours > 0:
            self._stat_uptime.set_value(f"{hours}h {minutes % 60}m")
        else:
            self._stat_uptime.set_value(f"{minutes}m")

    def _update_ai_status(self):
        if self._chat_mgr.isConnected():
            self._ai_status.setText("AI: Connected")
            self._ai_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self._ai_dot.setStyleSheet(f"background: {COLORS['success']}; border-radius: 4px; border: none;")
        else:
            self._ai_status.setText("AI: Disconnected")
            self._ai_status.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self._ai_dot.setStyleSheet(f"background: {COLORS['danger']}; border-radius: 4px; border: none;")

    def _add_recent_error(self, error_text: str, severity: str = "info"):
        if hasattr(self, '_recent_errors_placeholder'):
            self._recent_errors_placeholder.hide()
        label = QLabel(f"\u2022  {error_text[:120]}")
        label.setStyleSheet(f"color: {COLORS.get(severity, COLORS['text'])}; font-size: 12px; border: none; background: transparent;")
        label.setWordWrap(True)
        self._recent_errors_list.insertWidget(0, label)
        while self._recent_errors_list.count() > 10:
            item = self._recent_errors_list.takeAt(self._recent_errors_list.count() - 1)
            if item.widget():
                item.widget().deleteLater()

    # ════════════════════════════════════════════════════════
    # Chat
    # ════════════════════════════════════════════════════════

    def _chat_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        chat_header = QFrame()
        chat_header.setFixedHeight(48)
        chat_header.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        ch_layout = QHBoxLayout(chat_header)
        ch_layout.setContentsMargins(20, 0, 20, 0)
        ch_title = QLabel("Chat")
        ch_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        ch_layout.addWidget(ch_title)
        ch_layout.addStretch()

        new_chat_btn = QPushButton("+ New Chat")
        new_chat_btn.setCursor(Qt.PointingHandCursor)
        new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        new_chat_btn.clicked.connect(self._new_chat)
        ch_layout.addWidget(new_chat_btn)
        layout.addWidget(chat_header)

        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._chat_container = QWidget()
        self._chat_messages_layout = QVBoxLayout(self._chat_container)
        self._chat_messages_layout.setContentsMargins(32, 16, 32, 16)
        self._chat_messages_layout.setSpacing(8)
        self._chat_messages_layout.addStretch()
        self._chat_scroll.setWidget(self._chat_container)
        layout.addWidget(self._chat_scroll, 1)

        self._typing_indicator = TypingIndicator()
        self._typing_indicator.hide()

        input_bar = QFrame()
        input_bar.setFixedHeight(72)
        input_bar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        ib_layout = QHBoxLayout(input_bar)
        ib_layout.setContentsMargins(32, 12, 32, 12)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Type a message... (Enter to send)")
        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        self._chat_input.returnPressed.connect(self._send_chat_message)
        ib_layout.addWidget(self._chat_input, 1)

        send_btn = QPushButton("\u27A4")
        send_btn.setFixedSize(40, 40)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                font-size: 16px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        send_btn.clicked.connect(self._send_chat_message)
        ib_layout.addWidget(send_btn)
        layout.addWidget(input_bar)

        return w

    def _send_chat_message(self):
        text = self._chat_input.text().strip()
        if not text:
            return
        self._chat_input.clear()
        bubble = MessageBubble(text, is_user=True)
        self._chat_messages_layout.insertWidget(self._chat_messages_layout.count() - 1, bubble)
        self._chat_count += 1
        self._stat_chats.set_value(str(self._chat_count))
        self._typing_indicator.start()
        self._chat_messages_layout.insertWidget(self._chat_messages_layout.count() - 1, self._typing_indicator)
        QTimer.singleShot(100, lambda: self._chat_mgr.sendMessageAsync(text))
        QTimer.singleShot(200, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()))

    def _on_chat_response(self, response: str):
        self._typing_indicator.stop()
        try:
            idx = self._chat_messages_layout.indexOf(self._typing_indicator)
            if idx >= 0:
                item = self._chat_messages_layout.takeAt(idx)
                if item.widget():
                    item.widget().setParent(None)
        except Exception:
            pass
        bubble = MessageBubble(response, is_user=False)
        self._chat_messages_layout.insertWidget(self._chat_messages_layout.count() - 1, bubble)
        QTimer.singleShot(100, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()))

    def _new_chat(self):
        self._chat_mgr.newConversation()
        for i in range(self._chat_messages_layout.count() - 1, -1, -1):
            item = self._chat_messages_layout.itemAt(i)
            if item and item.widget() and item.widget() != self._typing_indicator:
                item.widget().deleteLater()

    # ════════════════════════════════════════════════════════
    # Monitoring
    # ════════════════════════════════════════════════════════

    def _monitoring_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        title = QLabel("Screen Monitoring")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(title)

        toggle_card = Card()
        tc_layout = QHBoxLayout(toggle_card)
        tc_layout.setContentsMargins(20, 16, 20, 16)
        tc_info = QVBoxLayout()
        tc_info.setSpacing(4)
        tc_label = QLabel("Screen Monitoring")
        tc_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 600; border: none; background: transparent;")
        tc_desc = QLabel("Periodically captures the screen, runs OCR, and detects errors")
        tc_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        tc_info.addWidget(tc_label)
        tc_info.addWidget(tc_desc)
        tc_layout.addLayout(tc_info, 1)
        self._monitor_btn = QPushButton("Start Monitoring")
        self._monitor_btn.setFixedHeight(40)
        self._monitor_btn.setCursor(Qt.PointingHandCursor)
        self._monitor_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        self._monitor_btn.clicked.connect(self._on_monitor_toggle)
        tc_layout.addWidget(self._monitor_btn)
        layout.addWidget(toggle_card)

        summary_card = Card()
        sc_layout = QVBoxLayout(summary_card)
        sc_layout.setContentsMargins(16, 12, 16, 12)
        sc_layout.setSpacing(8)
        sc_title = QLabel("Current Status")
        sc_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        sc_layout.addWidget(sc_title)
        self._ocr_summary = QLabel("No issues detected")
        self._ocr_summary.setWordWrap(True)
        self._ocr_summary.setFixedHeight(44)
        self._ocr_summary.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._ocr_summary.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                border: none;
                background: transparent;
            }}
        """)
        sc_layout.addWidget(self._ocr_summary)
        layout.addWidget(summary_card)

        pause_card = Card()
        pc_layout = QHBoxLayout(pause_card)
        pc_layout.setContentsMargins(16, 10, 16, 10)
        self._pause_indicator = QLabel("  Detection: Active")
        self._pause_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; border: none; background: transparent;")
        pc_layout.addWidget(self._pause_indicator, 1)
        self._resume_btn = QPushButton("Resume")
        self._resume_btn.setFixedSize(70, 28)
        self._resume_btn.setCursor(Qt.PointingHandCursor)
        self._resume_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        self._resume_btn.clicked.connect(self._on_resume_detection)
        self._resume_btn.hide()
        pc_layout.addWidget(self._resume_btn)
        layout.addWidget(pause_card)

        feed_card = Card()
        fc_layout = QVBoxLayout(feed_card)
        fc_layout.setContentsMargins(16, 12, 16, 12)
        fc_layout.setSpacing(8)
        fc_title = QLabel("Live Error Feed")
        fc_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        fc_layout.addWidget(fc_title)

        self._error_feed_scroll = QScrollArea()
        self._error_feed_scroll.setWidgetResizable(True)
        self._error_feed_scroll.setFrameShape(QFrame.NoFrame)
        self._error_feed_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._error_feed_container = QWidget()
        self._error_feed_container.setStyleSheet("background: transparent; border: none;")
        self._error_feed = QVBoxLayout(self._error_feed_container)
        self._error_feed.setContentsMargins(4, 4, 8, 8)
        self._error_feed.setSpacing(10)
        self._error_feed_label = QLabel("No errors detected")
        self._error_feed_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 8px; border: none; background: transparent;")
        self._error_feed.addWidget(self._error_feed_label)
        self._error_feed.addStretch(1)
        self._error_feed_scroll.setWidget(self._error_feed_container)
        fc_layout.addWidget(self._error_feed_scroll, 1)
        layout.addWidget(feed_card, 1)

        return w

    def _on_monitor_toggle(self):
        if self._monitor.isMonitoring():
            self._monitor.stopMonitoring()
        else:
            self._monitor.startMonitoring()
        self._sync_monitor_button()

    def _sync_monitor_button(self):
        running = self._monitor.isMonitoring()
        if running:
            self._monitor_btn.setText("Stop Monitoring")
            self._monitor_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['danger']};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background: {COLORS['danger']}; }}
            """)
        else:
            self._monitor_btn.setText("Start Monitoring")
            self._monitor_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
            """)

    def _on_frame_captured(self, image, text: str):
        self._context.setOCRText(text)
        if not self._active_fingerprint:
            return
        if self._detector.detectError(text):
            self._clean_frames = 0
        else:
            self._clean_frames += 1
            if self._clean_frames >= 2:
                self._active_fingerprint = None
                self._last_error_info = None
                self._clean_frames = 0
                self._reset_ocr_summary()

    def _on_monitor_error(self, ocr_text: str, error_text: str):
        errors = self._detector.detectError(ocr_text)
        if not errors:
            self._last_ocr_text = ocr_text
            return

        error_info = errors[0]
        fp = self._error_fingerprint(error_info)
        if fp and fp == self._active_fingerprint:
            self._last_ocr_text = ocr_text
            return

        if fp and fp in self._paused_fingerprints:
            self._last_ocr_text = ocr_text
            self._active_fingerprint = fp
            self._clean_frames = 0
            return

        self._active_fingerprint = fp
        self._clean_frames = 0
        self._last_ocr_text = ocr_text
        self._last_error_info = error_info

        self._error_count += 1
        self._stat_errors.set_value(str(self._error_count))
        self._companion.setUnreadCount(self._error_count)

        for issue in errors[:3]:
            label = self._issue_label(issue)
            feed_item = self._create_error_feed_item(issue)
            self._error_feed_label.hide()
            self._error_feed.insertWidget(0, feed_item)
            self._add_recent_error(label, "danger")

        QTimer.singleShot(0, lambda: self._error_feed_scroll.verticalScrollBar().setValue(0))

        label = self._issue_label(error_info)
        self._set_ocr_summary(error_info, label)
        self._notifications.showNotification(
            f"Error detected: {error_info.get('error_type', 'Unknown')}",
            "danger", "Explain"
        )
        self._companion.setState("alert")
        QTimer.singleShot(3000, lambda: self._companion.setState("idle"))
        self._companion.showNotificationPopup(
            error_info.get("error_type", "Error"),
            error_info.get("error_message") or label,
            error_info=error_info
        )

    def _issue_label(self, error_info: dict) -> str:
        parts = [str(error_info.get("error_type") or "Error")]
        msg = str(error_info.get("error_message") or "").strip()
        if msg:
            parts.append(msg)
        return ": ".join(parts)[:200]

    def _error_fingerprint(self, error_info: dict) -> str:
        etype = (error_info.get("error_type") or "unknown").strip()
        msg = re.sub(r"\s+", " ", (error_info.get("error_message") or "").strip()).lower()[:200]
        fname = (error_info.get("file_name") or "").replace("\\", "/").lower()
        line = int(error_info.get("line_number") or 0)
        parts = [etype]
        if fname:
            parts.append(fname)
        if line > 0:
            parts.append(str(line))
        parts.append(msg)
        return "|".join(parts)

    def _reset_ocr_summary(self):
        self._ocr_summary.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                border: none;
                background: transparent;
            }}
        """)
        self._ocr_summary.setText("No issues detected")

    def _set_ocr_summary(self, error_info: dict, fallback: str = ""):
        fname = error_info.get("file_name") or "unknown file"
        line = error_info.get("line_number") or ""
        msg = error_info.get("error_message") or fallback or ""
        summary = f"Detected: {error_info.get('error_type', 'Error')} in {fname}"
        if line:
            summary += f", line {line}"
        if msg:
            summary += f" \u2014 {msg[:80]}"
        self._ocr_summary.setText(summary)
        self._ocr_summary.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-size: 13px;
                border: none;
                background: transparent;
            }}
        """)

    def _create_error_feed_item(self, error_info: dict) -> QWidget:
        container = QFrame()
        container.setStyleSheet("background: transparent; border: none;")
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_layout = QVBoxLayout(container)
        row_layout.setContentsMargins(0, 6, 0, 6)
        row_layout.setSpacing(8)

        item = QFrame()
        item.setMinimumHeight(58)
        item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        item.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['elevated']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(item)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        error_text = self._issue_label(error_info)

        severity = error_info.get("severity", "danger")
        if severity not in COLORS:
            severity = "danger"
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {COLORS.get(severity, COLORS['danger'])}; border-radius: 5px; border: none;")
        layout.addWidget(dot, 0, Qt.AlignTop | Qt.AlignLeft)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(8)

        error_type_label = QLabel(error_text[:150])
        error_type_label.setWordWrap(True)
        error_type_label.setMinimumHeight(18)
        error_type_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        error_type_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        text_layout.addWidget(error_type_label)

        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(8)

        file_info = QLabel("")
        fname = error_info.get("file_name") or ""
        if fname:
            short = fname.replace("\\", "/").split("/")[-1]
            line = int(error_info.get("line_number") or 0)
            file_info.setText(f"{short}:{line}" if line > 0 else short)
        file_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-family: {FONTS['mono']}; border: none; background: transparent;")
        meta_layout.addWidget(file_info)

        timestamp = QLabel(time.strftime("%H:%M:%S"))
        timestamp.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        meta_layout.addWidget(timestamp)
        meta_layout.addStretch()

        text_layout.addLayout(meta_layout)
        layout.addLayout(text_layout, 1)

        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        btn_wrapper = QWidget()
        btn_wrapper.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        explain_btn = QPushButton("Explain")
        explain_btn.setFixedSize(76, 28)
        explain_btn.setCursor(Qt.PointingHandCursor)
        explain_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        explain_btn.clicked.connect(lambda: self._explain_error_from_feed(error_text))
        row3 = QVBoxLayout(btn_wrapper)
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(8)
        row3.addWidget(explain_btn, 0, Qt.AlignRight | Qt.AlignTop)

        dismiss_btn = QPushButton("\u2715 Dismiss")
        dismiss_btn.setFixedHeight(24)
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {COLORS['danger']}; border-color: {COLORS['danger']}; }}
        """)
        dismiss_btn.clicked.connect(lambda: container.deleteLater())
        row3.addWidget(dismiss_btn, 0, Qt.AlignRight | Qt.AlignTop)

        row3.addStretch(1)
        btn_layout.addWidget(btn_wrapper, 0, Qt.AlignTop)

        layout.addLayout(btn_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background: {COLORS['border']}; border: none; max-height: 1px;")

        row_layout.addWidget(item)
        row_layout.addWidget(divider)

        return container

    def _explain_error_from_feed(self, error_text: str):
        error_info = self._last_error_info or {"error_type": "Detected", "error_message": error_text, "language": "unknown"}
        self._auto_explain(error_info, self._last_ocr_text or "")

    def _auto_explain(self, error_info: dict, ocr_text: str = ""):
        self.showChat()
        self.activateWindow()
        self.raise_()
        etype = error_info.get("error_type", "Error")
        msg = error_info.get("error_message", "")
        summary = f"Explain this error:\n{etype}"
        if error_info.get("file_name"):
            summary += f" in {error_info.get('file_name')}"
            if error_info.get("line_number"):
                summary += f":{error_info.get('line_number')}"
        if msg:
            summary += f"\n{msg[:400]}"
        bubble = MessageBubble(summary, is_user=True)
        self._chat_messages_layout.insertWidget(self._chat_messages_layout.count() - 1, bubble)
        if self._typing_indicator:
            self._typing_indicator.start()
            self._chat_messages_layout.insertWidget(self._chat_messages_layout.count() - 1, self._typing_indicator)
        QTimer.singleShot(100, lambda: self._chat_mgr.explainErrorAsync(error_info, ocr_text))
        QTimer.singleShot(200, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()))

    def _on_companion_view(self):
        self._show_ocr_dialog()

    def _show_ocr_dialog(self):
        text = self._last_ocr_text or "No OCR text available."
        dlg = QDialog(self)
        dlg.setWindowTitle("Detected Screen OCR")
        dlg.resize(560, 420)
        dlg.setStyleSheet(f"background: {COLORS['surface']};")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        dlg_layout.setSpacing(12)
        title = QLabel("Raw OCR Text (last detected error)")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 600; border: none; background: transparent;")
        dlg_layout.addWidget(title)
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        viewer.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-family: {FONTS['mono']};
                font-size: 12px;
            }}
        """)
        dlg_layout.addWidget(viewer, 1)
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        close_btn.clicked.connect(dlg.accept)
        dlg_layout.addWidget(close_btn, 0, Qt.AlignRight)
        dlg.exec()

    # ════════════════════════════════════════════════════════
    # History
    # ════════════════════════════════════════════════════════

    def _history_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("History")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        self._history_search = QLineEdit()
        self._history_search.setPlaceholderText("Search errors...")
        self._history_search.setFixedWidth(250)
        self._history_search.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        self._history_search.textChanged.connect(self._filter_history)
        header.addWidget(self._history_search)

        self._history_filter = QComboBox()
        self._history_filter.addItems(["All", "Python", "JavaScript", "Java", "C/C++"])
        self._history_filter.setFixedWidth(120)
        self._history_filter.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 9pt;
            }}
        """)
        self._history_filter.currentIndexChanged.connect(self._filter_history)
        header.addWidget(self._history_filter)

        clear_btn = QPushButton("Clear History")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']}22;
                color: {COLORS['danger']};
                border: 1px solid {COLORS['danger']}44;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {COLORS['danger']}44; }}
        """)
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._history_container = QWidget()
        self._history_list = QVBoxLayout(self._history_container)
        self._history_list.setContentsMargins(0, 0, 0, 0)
        self._history_list.setSpacing(8)
        self._history_list.addStretch()
        history_scroll.setWidget(self._history_container)
        layout.addWidget(history_scroll, 1)

        self._load_history_items()
        return w

    def _load_history_items(self):
        while self._history_list.count() > 1:
            item = self._history_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        errors = load_history()
        if not errors:
            placeholder = QLabel("No history yet")
            placeholder.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
            self._history_list.insertWidget(0, placeholder)
            return

        current_date = ""
        for err in errors:
            date_str = err.get("created_at", "")[:10]
            if date_str != current_date:
                current_date = date_str
                date_label = QLabel(date_str)
                date_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 600; border: none; background: transparent; margin-top: 8px;")
                self._history_list.insertWidget(self._history_list.count() - 1, date_label)

            card = self._create_history_card(err)
            self._history_list.insertWidget(self._history_list.count() - 1, card)

    def _create_history_card(self, err: dict) -> QWidget:
        card = Card()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        header_layout = QHBoxLayout()

        type_label = QLabel(err.get("error_type", "Unknown"))
        type_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        header_layout.addWidget(type_label)

        sev = err.get("severity", "info")
        badge = Badge(sev.title(), sev)
        header_layout.addWidget(badge)
        header_layout.addStretch()

        lang_label = Badge(err.get("language", "unknown"), "accent")
        header_layout.addWidget(lang_label)

        info_layout.addLayout(header_layout)

        msg_label = QLabel(err.get("error_message", "")[:120])
        msg_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; border: none; background: transparent;")
        msg_label.setWordWrap(True)
        info_layout.addWidget(msg_label)

        if err.get("file_name"):
            file_label = QLabel(f"File: {err['file_name']}:{err.get('line_number', '')}")
            file_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: {FONTS['mono']}; border: none; background: transparent;")
            info_layout.addWidget(file_label)

        card_layout.addLayout(info_layout, 1)

        explain_btn = QPushButton("Explain")
        explain_btn.setFixedHeight(28)
        explain_btn.setCursor(Qt.PointingHandCursor)
        explain_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        explain_btn.clicked.connect(lambda: self._explain_from_history(err))
        card_layout.addWidget(explain_btn)

        return card

    def _explain_from_history(self, err: dict):
        self.showChat()
        self._chat_mgr.explainError(err)

    def _filter_history(self):
        search = self._history_search.text().lower()
        lang_filter = self._history_filter.currentText()
        errors = load_history()
        filtered = []
        for err in errors:
            if lang_filter != "All" and err.get("language", "").lower() != lang_filter.lower():
                continue
            if search and search not in err.get("error_type", "").lower() and search not in err.get("error_message", "").lower():
                continue
            filtered.append(err)

        while self._history_list.count() > 1:
            item = self._history_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not filtered:
            placeholder = QLabel("No matching errors")
            placeholder.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; background: transparent;")
            self._history_list.insertWidget(0, placeholder)
            return

        for err in filtered:
            card = self._create_history_card(err)
            self._history_list.insertWidget(self._history_list.count() - 1, card)

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear all error history?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_history()
            self._error_count = 0
            self._stat_errors.set_value("0")
            self._load_history_items()
            self._notifications.showNotification("History cleared", "success")

    # ════════════════════════════════════════════════════════
    # Memory
    # ════════════════════════════════════════════════════════

    def _memory_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Memory")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Add Memory")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        add_btn.clicked.connect(self._add_memory)
        header.addWidget(add_btn)
        layout.addLayout(header)

        memory_scroll = QScrollArea()
        memory_scroll.setWidgetResizable(True)
        memory_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._memory_container = QWidget()
        self._memory_list = QVBoxLayout(self._memory_container)
        self._memory_list.setContentsMargins(0, 0, 0, 0)
        self._memory_list.setSpacing(8)
        self._memory_list.addStretch()
        memory_scroll.setWidget(self._memory_container)
        layout.addWidget(memory_scroll, 1)

        self._load_memory_items()
        return w

    def _load_memory_items(self):
        while self._memory_list.count() > 1:
            item = self._memory_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        memories = get_all_memory()
        if not memories:
            empty = QLabel("No memory entries yet.\nAdd key-value pairs to help the AI remember context.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; border: none; background: transparent;")
            self._memory_list.insertWidget(0, empty)
            return

        for mem in memories:
            card = self._create_memory_card(mem)
            self._memory_list.insertWidget(self._memory_list.count() - 1, card)

    def _create_memory_card(self, mem: dict) -> QWidget:
        card = Card()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        info_layout = QVBoxLayout()
        key_label = QLabel(mem.get("memory_key", ""))
        key_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; font-family: {FONTS['mono']}; border: none; background: transparent;")
        info_layout.addWidget(key_label)

        val_label = QLabel(mem.get("memory_value", "")[:200])
        val_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; border: none; background: transparent;")
        val_label.setWordWrap(True)
        info_layout.addWidget(val_label)
        card_layout.addLayout(info_layout, 1)

        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {COLORS['danger']}; }}
        """)
        del_btn.clicked.connect(lambda: self._delete_memory(mem.get("memory_id"), card))
        card_layout.addWidget(del_btn)

        return card

    def _add_memory(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Memory")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {COLORS['surface']}; }}
            QLabel {{ color: {COLORS['text']}; font-size: 13px; border: none; background: transparent; }}
            QLineEdit, QTextEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus {{ border-color: {COLORS['accent']}; }}
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)

        form = QFormLayout(dialog)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        key_input = QLineEdit()
        key_input.setPlaceholderText("e.g., project_name")
        form.addRow("Key:", key_input)

        val_input = QTextEdit()
        val_input.setPlaceholderText("e.g., My awesome project")
        val_input.setFixedHeight(80)
        form.addRow("Value:", val_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(save_btn)
        form.addRow(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            key = key_input.text().strip()
            val = val_input.toPlainText().strip()
            if key and val:
                save_memory(key, val)
                self._load_memory_items()
                self._notifications.showNotification(f"Memory saved: {key}", "success")

    def _delete_memory(self, memory_id: int, card: QWidget):
        delete_memory(memory_id)
        card.deleteLater()
        self._notifications.showNotification("Memory deleted", "info")

    # ════════════════════════════════════════════════════════
    # Settings
    # ════════════════════════════════════════════════════════

    def _settings_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        theme_select = QComboBox()
        theme_select.addItems(["Light", "Dark", "Black", "White", "Blue"])
        theme_select.setFixedWidth(150)
        theme_select.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }}
            QComboBox:focus {{ border-color: {COLORS['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {COLORS['text_secondary']}; margin-right: 8px; }}
        """)
        try:
            current_theme = get_setting("theme", "")
            if current_theme not in THEMES:
                current_theme = "Dark" if get_setting("dark_mode", "0") == "1" else "Light"
        except Exception:
            current_theme = "Light"
        theme_select.setCurrentText(current_theme)
        self._theme_select = theme_select

        sections = [
            ("General", [
                ("Theme", "Choose the app color theme", "theme", theme_select),
                ("Notifications", "Enable desktop notifications", "notifications", ToggleSwitch(get_setting("notifications", "1") == "1")),
                ("Start on boot", "Launch application at system startup", "start_on_boot", ToggleSwitch(get_setting("start_on_boot", "0") == "1")),
            ]),
            ("Monitoring", [
                ("Auto-start", "Begin monitoring when the app launches", "auto_start_monitor", ToggleSwitch(get_setting("auto_start_monitor", "0") == "1")),
                ("Capture interval", "Seconds between screen captures", "capture_interval", ToggleSwitch(get_setting("capture_interval", "5") != "0")),
                ("Skip unchanged", "Ignore frames identical to the previous capture", "skip_unchanged", ToggleSwitch(get_setting("skip_unchanged", "1") == "1")),
            ]),
            ("OCR", [
                ("Auto-detect language", "Automatically identify the text language", "ocr_auto_lang", ToggleSwitch(get_setting("ocr_auto_lang", "1") == "1")),
                ("Confidence threshold", "Minimum OCR confidence to accept results", "ocr_confidence", ToggleSwitch(get_setting("ocr_confidence", "1") == "1")),
            ]),
            ("AI", [
                ("Stream responses", "Show AI responses as they arrive", "ai_stream", ToggleSwitch(get_setting("ai_stream", "1") == "1")),
                ("Auto-explain errors", "AI automatically explains detected errors", "ai_auto_explain", ToggleSwitch(get_setting("ai_auto_explain", "1") == "1")),
            ]),
            ("Companion", [
                ("Show companion", "Display the floating cat on screen", "show_companion", ToggleSwitch(get_setting("show_companion", "1") == "1")),
                ("Always on top", "Keep the companion above other windows", "companion_top", ToggleSwitch(get_setting("companion_top", "1") == "1")),
            ]),
            ("Data", [
                ("Auto-save", "Persist chat messages automatically", "auto_save", ToggleSwitch(get_setting("auto_save", "1") == "1")),
            ]),
        ]

        self._settings_toggles = {}

        ai_card = self._build_ai_config_card()
        scroll_layout.addWidget(ai_card)

        skill_card = self._build_skill_level_card()
        scroll_layout.addWidget(skill_card)

        pet_card = self._build_pet_select_card()
        scroll_layout.addWidget(pet_card)

        for section_name, items in sections:
            card = QFrame()
            card.setObjectName("SettingsCard")
            card.setStyleSheet(f"""
                QFrame#SettingsCard {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)
            card_layout.setSpacing(0)

            sec_label = QLabel(section_name)
            sec_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
            card_layout.addWidget(sec_label)
            card_layout.addSpacing(12)

            for idx, (label, desc, key, toggle) in enumerate(items):
                row = QHBoxLayout()
                row.setContentsMargins(0, 12, 0, 12)
                row.setSpacing(12)

                info = QVBoxLayout()
                info.setContentsMargins(0, 0, 0, 0)
                info.setSpacing(4)

                lbl = QLabel(label)
                lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
                info.addWidget(lbl)

                dsc = QLabel(desc)
                dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
                info.addWidget(dsc)

                row.addLayout(info, 1)
                row.addWidget(toggle)
                card_layout.addLayout(row)

                if isinstance(toggle, QComboBox):
                    toggle.currentTextChanged.connect(self._on_theme_changed)
                else:
                    self._settings_toggles[key] = toggle
                    toggle.toggled.connect(lambda checked, k=key: self._on_setting_changed(k, checked))

                if idx < len(items) - 1:
                    divider = QFrame()
                    divider.setFrameShape(QFrame.HLine)
                    divider.setStyleSheet(f"background: {COLORS['border']}; border: none; max-height: 1px;")
                    card_layout.addWidget(divider)

            scroll_layout.addWidget(card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
        return w

    def _build_ai_config_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)

        sec_label = QLabel("AI Configuration")
        sec_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        card_layout.addWidget(sec_label)
        card_layout.addSpacing(16)

        provider_row = QHBoxLayout()
        provider_row.setContentsMargins(0, 12, 0, 12)
        provider_row.setSpacing(12)
        provider_info = QVBoxLayout()
        provider_info.setSpacing(4)
        provider_lbl = QLabel("Provider")
        provider_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        provider_dsc = QLabel("Select your AI provider")
        provider_dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        provider_info.addWidget(provider_lbl)
        provider_info.addWidget(provider_dsc)
        provider_row.addLayout(provider_info, 1)
        self._ai_provider = QComboBox()
        self._ai_provider.addItems(["openrouter", "openai", "custom"])
        self._ai_provider.setFixedWidth(150)
        self._ai_provider.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }}
            QComboBox:focus {{ border-color: {COLORS['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {COLORS['text_secondary']}; margin-right: 8px; }}
        """)
        self._ai_provider.setCurrentText(get_provider())
        provider_row.addWidget(self._ai_provider)
        card_layout.addLayout(provider_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background: {COLORS['border']}; border: none; max-height: 1px;")
        card_layout.addWidget(divider)

        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 12, 0, 12)
        key_row.setSpacing(12)
        key_info = QVBoxLayout()
        key_info.setSpacing(4)
        key_lbl = QLabel("API Key")
        key_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        key_dsc = QLabel("Your API key from the provider")
        key_dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        key_info.addWidget(key_lbl)
        key_info.addWidget(key_dsc)
        key_row.addLayout(key_info, 1)
        key_input_layout = QHBoxLayout()
        key_input_layout.setSpacing(4)
        self._ai_key_input = QLineEdit()
        self._ai_key_input.setEchoMode(QLineEdit.Password)
        self._ai_key_input.setPlaceholderText("sk-...")
        self._ai_key_input.setFixedWidth(260)
        self._ai_key_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        self._ai_key_input.setText(get_api_key())
        key_input_layout.addWidget(self._ai_key_input)
        show_btn = QPushButton("\u25C9")
        show_btn.setFixedSize(32, 32)
        show_btn.setCursor(Qt.PointingHandCursor)
        show_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['elevated']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {COLORS['text']}; border-color: {COLORS['accent']}; }}
        """)
        show_btn.clicked.connect(self._toggle_key_visibility)
        key_input_layout.addWidget(show_btn)
        save_key_btn = QPushButton("Save")
        save_key_btn.setFixedHeight(32)
        save_key_btn.setCursor(Qt.PointingHandCursor)
        save_key_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_hover']}; }}
        """)
        save_key_btn.clicked.connect(self._save_ai_config)
        key_input_layout.addWidget(save_key_btn)
        key_row.addLayout(key_input_layout)
        card_layout.addLayout(key_row)

        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setStyleSheet(f"background: {COLORS['border']}; border: none; max-height: 1px;")
        card_layout.addWidget(divider2)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 12, 0, 12)
        model_row.setSpacing(12)
        model_info = QVBoxLayout()
        model_info.setSpacing(4)
        model_lbl = QLabel("Model")
        model_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        model_dsc = QLabel("The model to use for chat and analysis")
        model_dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        model_info.addWidget(model_lbl)
        model_info.addWidget(model_dsc)
        model_row.addLayout(model_info, 1)
        self._ai_model = QComboBox()
        self._ai_model.setEditable(True)
        self._ai_model.addItems([
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.1-8b-instruct:free",
        ])
        self._ai_model.setFixedWidth(260)
        self._ai_model.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }}
            QComboBox:focus {{ border-color: {COLORS['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {COLORS['text_secondary']}; margin-right: 8px; }}
        """)
        self._ai_model.setCurrentText(get_model())
        model_row.addWidget(self._ai_model)
        card_layout.addLayout(model_row)

        self._base_url_row_widget = QWidget()
        base_url_row = QHBoxLayout(self._base_url_row_widget)
        base_url_row.setContentsMargins(0, 12, 0, 12)
        base_url_row.setSpacing(12)
        bu_info = QVBoxLayout()
        bu_info.setSpacing(4)
        bu_lbl = QLabel("Base URL")
        bu_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        bu_dsc = QLabel("API endpoint URL (custom providers only)")
        bu_dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        bu_info.addWidget(bu_lbl)
        bu_info.addWidget(bu_dsc)
        base_url_row.addLayout(bu_info, 1)
        self._ai_base_url = QLineEdit()
        self._ai_base_url.setPlaceholderText("https://your-api.com/v1")
        self._ai_base_url.setFixedWidth(260)
        self._ai_base_url.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        self._ai_base_url.setText(get_base_url())
        base_url_row.addWidget(self._ai_base_url)
        card_layout.addWidget(self._base_url_row_widget)
        self._base_url_row_widget.setVisible(get_provider() == "custom")

        divider3 = QFrame()
        divider3.setFrameShape(QFrame.HLine)
        divider3.setStyleSheet(f"background: {COLORS['border']}; border: none; max-height: 1px;")
        card_layout.addWidget(divider3)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 12, 0, 0)
        status_row.setSpacing(12)
        status_info = QVBoxLayout()
        status_info.setSpacing(4)
        status_lbl = QLabel("Connection Status")
        status_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        status_info.addWidget(status_lbl)
        status_row.addLayout(status_info, 1)
        self._ai_status_dot = QLabel()
        self._ai_status_dot.setFixedSize(10, 10)
        self._ai_status_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 5px; border: none;")
        status_row.addWidget(self._ai_status_dot)
        self._ai_status_label = QLabel("Not configured")
        self._ai_status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        status_row.addWidget(self._ai_status_label)
        test_btn = QPushButton("Test Connection")
        test_btn.setFixedHeight(30)
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['accent']}; }}
        """)
        test_btn.clicked.connect(self._test_ai_connection)
        status_row.addWidget(test_btn)
        card_layout.addLayout(status_row)

        self._ai_provider.currentTextChanged.connect(self._on_provider_changed)

        return card

    def _build_skill_level_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)

        card_title = QLabel("AI Skill Level")
        card_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        card_layout.addWidget(card_title)
        card_layout.addSpacing(8)

        card_desc = QLabel("Adjusts how detailed the AI's explanations are")
        card_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        card_layout.addWidget(card_desc)
        card_layout.addSpacing(12)

        row = QHBoxLayout()
        row.setContentsMargins(0, 12, 0, 12)
        row.setSpacing(12)
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(4)
        lbl = QLabel("Skill Level")
        lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        info.addWidget(lbl)
        dsc = QLabel("Beginner \u2014 simple, jargon-free guidance | Intermediate \u2014 balanced | Advanced \u2014 precise technical detail")
        dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        info.addWidget(dsc)
        row.addLayout(info, 1)
        self._skill_level = QComboBox()
        self._skill_level.addItems(["Beginner", "Intermediate", "Advanced"])
        self._skill_level.setFixedWidth(150)
        self._skill_level.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }}
            QComboBox:focus {{ border-color: {COLORS['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {COLORS['text_secondary']}; margin-right: 8px; }}
        """)
        current = get_setting("skill_level", "intermediate").lower()
        current = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}.get(current, "Intermediate")
        self._skill_level.setCurrentText(current)
        self._skill_level.currentTextChanged.connect(
            lambda level: save_settings("skill_level", level.lower()))
        row.addWidget(self._skill_level)
        card_layout.addLayout(row)

        return card

    def _build_pet_select_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)

        card_title = QLabel("Companion Pet")
        card_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600; border: none; background: transparent;")
        card_layout.addWidget(card_title)
        card_layout.addSpacing(8)

        card_desc = QLabel("Choose the floating companion that appears on screen")
        card_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        card_layout.addWidget(card_desc)
        card_layout.addSpacing(12)

        row = QHBoxLayout()
        row.setContentsMargins(0, 12, 0, 12)
        row.setSpacing(12)
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(4)
        lbl = QLabel("Pet")
        lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        info.addWidget(lbl)
        dsc = QLabel("Changes the floating companion's appearance")
        dsc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; border: none; background: transparent;")
        info.addWidget(dsc)
        row.addLayout(info, 1)
        self._pet_select = QComboBox()
        self._pet_select.addItems(["Blue Cat", "Dog", "Panda", "Red Panda", "Fox"])
        self._pet_select.setFixedWidth(150)
        self._pet_select.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['elevated']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }}
            QComboBox:focus {{ border-color: {COLORS['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {COLORS['text_secondary']}; margin-right: 8px; }}
        """)
        pet_map = {
            "blue_tabby_pet1.png": "Blue Cat",
            "pet_dog.png": "Dog",
            "pet_panda.png": "Panda",
            "pet_red_panda.png": "Red Panda",
            "pet_fox.png": "Fox",
        }
        reverse_map = {v: k for k, v in pet_map.items()}
        current_file = get_setting("companion_pet", "blue_tabby_pet1.png")
        if current_file == "blue_tabby_pet.png":
            current_file = "blue_tabby_pet1.png"
        current_name = pet_map.get(current_file, "Blue Cat")
        self._pet_select.setCurrentText(current_name)
        self._pet_select.currentTextChanged.connect(
            lambda name: self._on_pet_changed(name))
        row.addWidget(self._pet_select)
        card_layout.addLayout(row)

        return card

    def _on_pet_changed(self, name: str):
        pet_map = {
            "Blue Cat": "blue_tabby_pet1.png",
            "Dog": "pet_dog.png",
            "Panda": "pet_panda.png",
            "Red Panda": "pet_red_panda.png",
            "Fox": "pet_fox.png",
        }
        filename = pet_map.get(name, "blue_tabby_pet1.png")
        save_settings("companion_pet", filename)
        self._companion.refresh_pet()

    def _toggle_key_visibility(self):
        if self._ai_key_input.echoMode() == QLineEdit.Password:
            self._ai_key_input.setEchoMode(QLineEdit.Normal)
        else:
            self._ai_key_input.setEchoMode(QLineEdit.Password)

    def _on_provider_changed(self, provider: str):
        self._base_url_row_widget.setVisible(provider == "custom")
        if provider == "openrouter":
            self._ai_model.setCurrentText("anthropic/claude-3-haiku")
        elif provider == "openai":
            self._ai_model.setCurrentText("gpt-4o")
        else:
            self._ai_model.setCurrentText("")
        self._ai_key_input.setText(get_api_key())
        self._ai_base_url.setText(get_base_url())

    def _save_ai_config(self):
        provider = self._ai_provider.currentText()
        key = self._ai_key_input.text().strip()
        model = self._ai_model.currentText().strip()
        base_url = self._ai_base_url.text().strip()
        set_provider(provider)
        if key:
            set_api_key(key)
        if model:
            set_model(model)
        if provider == "custom" and base_url:
            set_base_url(base_url)
        load_dotenv(_ENV_PATH, override=True)
        self._chat_mgr._ai.refresh_client()
        self._test_ai_connection()

    def _test_ai_connection(self):
        self._ai_status_dot.setStyleSheet(f"background: {COLORS['warning']}; border-radius: 5px; border: none;")
        self._ai_status_label.setText("Testing...")
        self._ai_status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 13px; border: none; background: transparent;")
        QTimer.singleShot(100, self._do_ai_connection_test)

    def _do_ai_connection_test(self):
        def _apply(result):
            ok, msg = result
            if ok:
                self._ai_status_dot.setStyleSheet(f"background: {COLORS['success']}; border-radius: 5px; border: none;")
                self._ai_status_label.setText(msg)
                self._ai_status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 13px; border: none; background: transparent;")
            else:
                self._ai_status_dot.setStyleSheet(f"background: {COLORS['danger']}; border-radius: 5px; border: none;")
                self._ai_status_label.setText(msg)
                self._ai_status_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 13px; border: none; background: transparent;")

        thread = AIRequestThread(test_connection)
        thread.succeeded.connect(_apply)
        thread.failed.connect(lambda e: _apply((False, f"Failed: {str(e)[:60]}")))
        thread.finished.connect(lambda: setattr(self, "_test_thread", None))
        self._test_thread = thread
        thread.start()

    def _on_theme_changed(self, name: str):
        if name not in THEMES:
            return
        save_settings("theme", name)
        apply_named_theme(self, name)
        self._rebuild_ui_for_theme()
        self._notifications.showNotification(f"Theme changed to {name}", "info")

    def _rebuild_ui_for_theme(self):
        current_index = self._content_area.currentIndex()

        self.centralWidget().setStyleSheet(f"background: {COLORS['bg']};")
        self._content_area.setStyleSheet(f"background: {COLORS['bg']};")

        self._sidebar.setStyleSheet(f"""
            QFrame#Sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['sidebar_top']}, stop:1 {COLORS['sidebar_bottom']});
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        self._status_card.setStyleSheet(f"""
            QFrame#StatusCard {{
                background: {COLORS['sidebar_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin: 8px 12px 12px 12px;
            }}
        """)
        self._monitor_status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        self._monitor_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 4px; border: none;")
        self._ai_status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        self._ai_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 4px; border: none;")

        for btn in self._nav_buttons:
            btn._update_style()

        while self._content_area.count():
            widget = self._content_area.widget(0)
            self._content_area.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

        self._build_pages()

        if current_index < self._content_area.count():
            self._content_area.setCurrentIndex(current_index)
        else:
            self._content_area.setCurrentIndex(0)

        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == current_index)

    def _on_setting_changed(self, key: str, value: bool):
        save_settings(key, "1" if value else "0")
        if key == "dark_mode":
            if value:
                apply_dark_theme(self)
            else:
                apply_light_theme(self)
            self._notifications.showNotification("Theme changed — restart for full effect", "info")
        elif key == "show_companion":
            if value:
                self._companion.show()
            else:
                self._companion.hide()
        elif key == "notifications":
            if value:
                self._notifications.showNotification("Notifications enabled", "success")

    # ════════════════════════════════════════════════════════
    # Navigation slots
    # ════════════════════════════════════════════════════════

    def showDashboard(self):
        self._content_area.setCurrentIndex(0)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[0].set_active(True)
        self._update_uptime()

    def showChat(self):
        self._content_area.setCurrentIndex(1)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[1].set_active(True)

    def showScreenContext(self):
        self._content_area.setCurrentIndex(2)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[2].set_active(True)

    def showHistory(self):
        self._content_area.setCurrentIndex(3)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[3].set_active(True)
        self._load_history_items()

    def showMemory(self):
        self._content_area.setCurrentIndex(4)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[4].set_active(True)
        self._load_memory_items()

    def showSettings(self):
        self._content_area.setCurrentIndex(5)
        for btn in self._nav_buttons:
            btn.set_active(False)
        self._nav_buttons[5].set_active(True)

    # ════════════════════════════════════════════════════════
    # Companion / Tray / Watcher integration
    # ════════════════════════════════════════════════════════

    def _on_companion_chat(self):
        self.show()
        self.showChat()
        self.activateWindow()
        self.raise_()
        if self._last_error_info:
            error_info = self._last_error_info
            self._last_error_info = None
            self._auto_explain(error_info, self._last_ocr_text or "")

    def _on_companion_error_asked(self, error_info: dict):
        self.show()
        self.showChat()
        self.activateWindow()
        self.raise_()
        self._last_error_info = None
        self._auto_explain(error_info, self._last_ocr_text or "")

    def _on_companion_pause_requested(self):
        if self._active_fingerprint:
            self._paused_fingerprints.add(self._active_fingerprint)
            self._update_pause_indicator()
            self._notifications.showNotification(
                "Detection paused for current error", "warning", "OK"
            )

    def _update_pause_indicator(self):
        if hasattr(self, '_pause_indicator'):
            paused = len(self._paused_fingerprints) > 0
            if paused:
                self._pause_indicator.setText("  Detection: Paused")
                self._pause_indicator.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px; border: none; background: transparent;")
                self._pause_indicator.show()
                self._resume_btn.show()
            else:
                self._pause_indicator.setText("  Detection: Active")
                self._pause_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; border: none; background: transparent;")
                self._resume_btn.hide()

    def _on_resume_detection(self):
        self._paused_fingerprints.clear()
        self._update_pause_indicator()

    def _on_companion_dbl_click(self):
        if self._companion.popup() is not None:
            self._companion.raisePopup()
            return
        if self._last_error_info:
            info = self._last_error_info
            self._companion.showNotificationPopup(
                info.get("error_type", "Error Detected"),
                (info.get("error_message") or "Detected error")[:140],
                error_info=info
            )
            return
        if self._last_ocr_text:
            self._companion.showNotificationPopup(
                "AI-Companion",
                "No error detected in the latest screen capture."
            )
            return
        self._companion.showNotificationPopup(
            "AI-Companion",
            "No errors detected yet. Start monitoring to analyze the screen."
        )

    def _on_companion_dashboard(self):
        self.show()
        self.showDashboard()
        if self.isMinimized():
            self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_companion_menu(self):
        menu = QFrame(self)
        menu.setFixedSize(160, 120)
        menu.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['elevated']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(menu)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        for text, slot in [("Show Window", self._on_companion_chat),
                           ("Toggle Monitoring", self._toggle_monitoring_from_tray),
                           ("Quit", self._quit_app)]:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['text']};
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{ background: {COLORS['accent']}22; }}
            """)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        pos = self._companion.pos()
        menu.move(pos.x() - 40, pos.y() - 130)
        menu.show()

    def _show_from_tray(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def _stop_monitor_thread(self):
        if self._monitor.isMonitoring():
            self._monitor.stopMonitoring()
        thread = self._monitor._thread
        deadline = time.time() + 3.0
        while thread is not None and thread.isRunning() and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.005)
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(3000)

    def _quit_app(self):
        self._stop_monitor_thread()
        self._chat_mgr.shutdown(8000)
        if self._test_thread is not None:
            self._test_thread.wait(1000)
        self._watcher.stopWatching()
        self._companion.hide()
        self._tray.hide()
        QApplication.instance().quit()

    def _toggle_monitoring_from_tray(self):
        if self._monitor.isMonitoring():
            self._monitor.stopMonitoring()
            self._sync_monitor_button()
        else:
            self._monitor.startMonitoring()
            self._sync_monitor_button()

    def _on_file_changed(self, path: str):
        self._notifications.showNotification(f"File changed: {os.path.basename(path)}", "info")

    def _on_watcher_error(self, path: str, message: str):
        self._error_count += 1
        self._stat_errors.set_value(str(self._error_count))
        self._add_recent_error(f"{os.path.basename(path)}: {message}", "warning")
        self._notifications.showNotification(f"Pyflakes: {message}", "warning", "Explain")

    def _on_monitor_status(self, running: bool):
        if running:
            self._monitor_status.setText("Monitoring: On")
            self._monitor_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self._monitor_dot.setStyleSheet(f"background: {COLORS['success']}; border-radius: 4px; border: none;")
        else:
            self._monitor_status.setText("Monitoring: Off")
            self._monitor_status.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self._monitor_dot.setStyleSheet(f"background: {COLORS['text_secondary']}; border-radius: 4px; border: none;")
            self._last_error_info = None
            self._active_fingerprint = None
            self._clean_frames = 0
            self._paused_fingerprints.clear()
            self._update_pause_indicator()
            self._reset_ocr_summary()

    # ════════════════════════════════════════════════════════
    # Draggable window
    # ════════════════════════════════════════════════════════

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 48:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def showEvent(self, event):
        super().showEvent(event)
        companion = getattr(self, "_companion", None)
        if companion is not None:
            companion.show()
            companion.raise_()

    def closeEvent(self, event):
        self._stop_monitor_thread()
        self._watcher.stopWatching()
        self._companion.hide()
        self._tray.hide()
        super().closeEvent(event)
