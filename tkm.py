import os
import glob
from mutagen import File
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox



class TKM(QThread):
    """
    Поток загрузки треков: для полной загрузки (mode='load')
    и для добавления к существующему списку (mode='add').
    """
    # finished сигнал: mode, tracks list, total_duration, unsupported list
    finished = pyqtSignal(str, list, int, list)

    def __init__(self, rootpath, mode='load', existing_paths=None, start_index=1, parent=None):
        super().__init__(parent)
        self.rootpath = rootpath
        self.mode = mode  # 'load' or 'add'
        self.existing_paths = existing_paths or set()
        self.start_index = start_index

    def run(self):
        try:
            files = self.collect_tracks(self.rootpath)
            if not files:
                # ничего не найдено
                self.finished.emit(self.mode, [], 0, [])
                return

            tracks, total_duration, unsupported = self.prepare_track_entries(
                files,
                start_index=self.start_index,
                existing_paths=self.existing_paths
            )

            self.finished.emit(self.mode, tracks, total_duration, unsupported)
        except Exception as e:
            print(f"[TKM] Ошибка в потоке: {e}")
            self.finished.emit(self.mode, [], 0, [])

    def collect_tracks(self, rootpath):
        files = []
        if isinstance(rootpath, str) and os.path.isdir(rootpath):
            patterns = [
                "*.mp3", "*.wav", "*.flac", "*.ogg", "*.aac",
                "*.m4a", "*.wma", "*.opus", "*.alac", "*.aiff",
                "*.amr", "*.ape", "*.wv", "*.mpc", "*.spx", "*.cached",
                "*.mp4", "*.mkv"
            ]
            for pat in patterns:
                files.extend(glob.glob(os.path.join(rootpath, pat)))
        elif isinstance(rootpath, list) and all(os.path.isfile(p) for p in rootpath):
            files = rootpath
        return files

    def prepare_track_entries(self, files, start_index, existing_paths):
        total_duration = 0
        unsupported_files = []
        tracks = []

        for idx, path in enumerate(files, start=start_index):
            if path in existing_paths:
                continue
            base = os.path.splitext(os.path.basename(path))[0]
            name = base if len(base) <= 30 else base[:30] + '...'
            dur = self.get_track_duration(path)
            if dur is not None:
                dur_str = self.seconds_to_mm_ss(dur)
                total_duration += dur
            else:
                dur_str = "??:??"
                unsupported_files.append(path)
            tracks.append((str(idx), name, path, dur_str, dur))

        return tracks, total_duration, unsupported_files

    def get_track_duration(self, track_path):
        try:
            audio = File(track_path)
            if audio is None or not hasattr(audio, 'info') or not hasattr(audio.info, 'length'):
                return None
            return int(audio.info.length)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при обработке файла {track_path}:\n{e}")
            return None

    @staticmethod
    def seconds_to_mm_ss(seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02}:{s:02}"