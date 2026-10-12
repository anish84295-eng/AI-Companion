from PySide6.QtGui import QPalette, QColor, QFont, QGuiApplication

COLORS_LIGHT = {
    "bg": "#F7F8FB",
    "surface": "#FFFFFF",
    "elevated": "#EEF0F6",
    "border": "#E1E4ED",
    "text": "#14161D",
    "text_secondary": "#5A6274",
    "accent": "#6C5CE7",
    "accent_hover": "#7C6DF7",
    "accent_pressed": "#5C4CD7",
    "success": "#2ECC71",
    "warning": "#F5A623",
    "danger": "#FF5C5C",
    "sidebar_top": "#F8F7FD",
    "sidebar_bottom": "#F0EFF8",
    "sidebar_card": "#FFFFFF",
}

COLORS_DARK = {
    "bg": "#0F1117",
    "surface": "#171A23",
    "elevated": "#1F2430",
    "border": "#2A2F3D",
    "text": "#E8EAF0",
    "text_secondary": "#9AA3B5",
    "accent": "#6C5CE7",
    "accent_hover": "#7C6DF7",
    "accent_pressed": "#5C4CD7",
    "success": "#2ECC71",
    "warning": "#F5A623",
    "danger": "#FF5C5C",
    "sidebar_top": "#14161F",
    "sidebar_bottom": "#101219",
    "sidebar_card": "#1A1D28",
}

COLORS_BLACK = {
    "bg": "#000000",
    "surface": "#0B0B10",
    "elevated": "#141419",
    "border": "#2A2A33",
    "text": "#F2F2F7",
    "text_secondary": "#9B9BA8",
    "accent": "#8B5CF6",
    "accent_hover": "#9D71F7",
    "accent_pressed": "#7A4EE4",
    "success": "#2ECC71",
    "warning": "#F5A623",
    "danger": "#FF5C5C",
    "sidebar_top": "#0C0C12",
    "sidebar_bottom": "#07070C",
    "sidebar_card": "#121218",
}

COLORS_WHITE = {
    "bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "elevated": "#F2F3F7",
    "border": "#D9DDE7",
    "text": "#0B0D12",
    "text_secondary": "#51586A",
    "accent": "#4F46E5",
    "accent_hover": "#5F57EA",
    "accent_pressed": "#4338CA",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "sidebar_top": "#FBFBFE",
    "sidebar_bottom": "#F4F4FA",
    "sidebar_card": "#FFFFFF",
}

COLORS_BLUE = {
    "bg": "#0A1424",
    "surface": "#111C33",
    "elevated": "#182744",
    "border": "#25385C",
    "text": "#E7EEF9",
    "text_secondary": "#90A2C0",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_pressed": "#1D4ED8",
    "success": "#22C55E",
    "warning": "#EAB308",
    "danger": "#EF4444",
    "sidebar_top": "#0E1A2E",
    "sidebar_bottom": "#0B1424",
    "sidebar_card": "#14203A",
}

THEMES = {
    "Light": COLORS_LIGHT,
    "Dark": COLORS_DARK,
    "Black": COLORS_BLACK,
    "White": COLORS_WHITE,
    "Blue": COLORS_BLUE,
}

COLORS = dict(COLORS_LIGHT)

FONTS = {
    "family": "'Inter', 'Segoe UI', sans-serif",
    "mono": "'JetBrains Mono', 'Consolas', monospace",
}


def apply_theme(widget):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["elevated"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["elevated"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    QGuiApplication.setPalette(palette)
    font = QFont("Inter", 10)
    font.setStyleHint(QFont.SansSerif)
    QGuiApplication.setFont(font)
    app = QGuiApplication.instance()
    if app is not None:
        app.setStyleSheet(_global_qss())
    widget.setStyleSheet(_global_qss())


def apply_dark_theme(widget):
    global COLORS
    COLORS.clear()
    COLORS.update(COLORS_DARK)
    apply_theme(widget)


def apply_light_theme(widget):
    global COLORS
    COLORS.clear()
    COLORS.update(COLORS_LIGHT)
    apply_theme(widget)


def apply_named_theme(widget, name: str):
    global COLORS
    COLORS.clear()
    COLORS.update(THEMES.get(name, COLORS_LIGHT))
    apply_theme(widget)


def _global_qss() -> str:
    return f"""
        * {{
            font-family: {FONTS['family']};
            outline: none;
        }}
        QToolTip {{
            background-color: {COLORS['elevated']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        QScrollBar:vertical {{
            background: {COLORS['bg']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS['border']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLORS['text_secondary']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {COLORS['bg']};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {COLORS['border']};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLORS['text_secondary']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """
