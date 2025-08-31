import sys

from PySide6.QtWidgets import QMainWindow, QApplication

from ui.library_widget import LibraryWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Test Library")

        self.library = LibraryWidget()
        self.setCentralWidget(self.library)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
