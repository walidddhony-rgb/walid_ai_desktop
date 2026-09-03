import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def run_app() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
