import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from translator_app.cuda import configure_cuda_dll_paths
from translator_app.ui.main_window import MainWindow


def main() -> int:
    configure_cuda_dll_paths()
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Subtitle Translator")
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.resize(1180, 760)
    window.show()
    return app.exec()
