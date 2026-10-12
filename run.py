import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ai_companion.core.database import init_db
from ai_companion.ui.main_window import MainWindow


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("AI-Companion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
