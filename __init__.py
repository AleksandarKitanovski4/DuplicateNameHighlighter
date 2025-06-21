from PyQt5.QtWidgets import QMainWindow

from gui.region_selector import RegionSelector

from gui.main_window import MainWindow
__all__ = [
    "MainWindow",
    "RegionSelector",
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # …
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.on_region_selected)
        # …
