from PyQt5.QtCore import QThread, pyqtSignal
import os
import glob


class LoadTracksThread(QThread):
    tracks_loaded = pyqtSignal(list)  # Сигнал для передачи результата

    def __init__(self, rootpath):
        super().__init__()
        self.rootpath = rootpath

    def run(self):
        # Выполнение операции в потоке
        loaded_tracks = self.load_tracks(self.rootpath)
        self.tracks_loaded.emit(loaded_tracks)  # Отправляем результат через сигнал

    def load_tracks(self, rootpath):
        files = []
        try:
            if os.path.exists(rootpath) and os.path.isdir(rootpath):
                formats = [
                    "*.mp3", "*.wav", "*.flac", "*.ogg", "*.aac",
                    "*.m4a", "*.wma", "*.opus", "*.alac", "*.aiff",
                    "*.amr", "*.ape", "*.wv", "*.mpc", "*.spx", "*.cached",
                    "*.mp4", "*.mkv"
                ]
                for pattern in formats:
                    files.extend(glob.glob(os.path.join(rootpath, pattern)))
            elif isinstance(rootpath, list) and all(os.path.isfile(path) for path in rootpath):
                files = rootpath
            else:
                raise ValueError("Неверный путь или формат")

            return files
        except Exception as e:
            print(f"Ошибка загрузки треков: {e}")
            return []