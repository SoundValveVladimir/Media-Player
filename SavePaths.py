import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class SavePathsThread(QThread):
    finished = pyqtSignal(list)
    def __init__(self, listbox, parent=None):
        super().__init__(parent)
        self.listbox = listbox

    def run(self):
        try:
            paths = []
            for index in range(self.listbox.count()):
                item = self.listbox.item(index)
                path = item.data(Qt.UserRole)
                if path:
                    paths.append(os.path.normpath(path))
            self.finished.emit(paths)
        except Exception as e:
            print(f"Ошибка при сохранении путей: {str(e)}")