import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from main_window import MainWindow


def enable_dark_theme(app: QApplication):
    # Style de base
    app.setStyle("Fusion")

    palette = QPalette()

    # Fond principal
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.black)

    # Widgets (groupbox, boutons, etc.)
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(55, 55, 55))
    palette.setColor(QPalette.ButtonText, Qt.black)

    # Surbrillance (sélections dans tables, combo…)
    palette.setColor(QPalette.Highlight, QColor(90, 140, 200))
    palette.setColor(QPalette.HighlightedText, Qt.black)

    # Tooltips
    palette.setColor(QPalette.ToolTipBase, QColor(60, 60, 60))
    palette.setColor(QPalette.ToolTipText, Qt.white)

    # Lignes / disabled
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(130, 130, 130))

    app.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 🔥 Dark mode global
    enable_dark_theme(app)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
