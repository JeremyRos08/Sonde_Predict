import sys
from PyQt5.QtWidgets import QApplication

from App.main_window import MainWindow
from App.themes import  enable_dark_blue


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 🔥 blue mode global
    enable_dark_blue(app)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
