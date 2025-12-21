from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def enable_dark_gray(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(40, 40, 40))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base, QColor(30, 30, 30))
    p.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    p.setColor(QPalette.Text, Qt.white)
    p.setColor(QPalette.Button, QColor(55, 55, 55))
    p.setColor(QPalette.ButtonText, Qt.white)
    p.setColor(QPalette.Highlight, QColor(90, 140, 200))
    p.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(p)


def enable_dark_blue(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(24, 26, 32))
    p.setColor(QPalette.WindowText, QColor(230, 230, 230))
    p.setColor(QPalette.Base, QColor(18, 20, 26))
    p.setColor(QPalette.AlternateBase, QColor(32, 35, 44))
    p.setColor(QPalette.Text, QColor(230, 230, 230))
    p.setColor(QPalette.Button, QColor(45, 50, 65))
    p.setColor(QPalette.ButtonText, QColor(240, 240, 240))
    p.setColor(QPalette.Highlight, QColor(0, 120, 215))
    p.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(p)


THEMES = {
    "Dark Gray (classique)": enable_dark_gray,
    "Dark Blue Tech": enable_dark_blue,
}
