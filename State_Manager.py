import json
import os
import sys
import uuid
import time
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from mutagen import File
from mutagen.mp3 import MP3

def resource_path(relative_path):
    """Получение абсолютного пути до ресурса"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)

    full_path = f"{base_path}\\{relative_path}"
    #print(full_path)  # Печать пути для отладки
    return full_path

state_file = resource_path("Data\\player_state.json")
state_file_ = resource_path("Data\\player_state_test.json")

class StateManager:
    def __init__(self, player, filename=state_file):
        self.player = player
        self.filename = filename
        self.default_state = resource_path("Data\\default_state.json")

    def load_file(self):
        try:
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except FileNotFoundError:
                print(f"Файл состояния {state_file} не найден.")
                return self.load_state(self.default_state)
            current_track_path = state.get("current_track_path")
            return current_track_path
        except Exception as e:
            QMessageBox.warning(self.player.ui, "Ошибка получения пути к файлу", str(e))

    def load_state(self, filename=None):
        if filename is None:
            filename = self.filename
        try:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except FileNotFoundError:
                print(f"Файл состояния {filename} не найден.")
                return self.load_state(self.default_state)
            self.player.rootpath = state.get("rootpath") or []
            path_map = {path: i for i, path in enumerate(self.player.rootpath)}
            current_track_path = state.get("current_track_path")
            current_index = (
                path_map.get(current_track_path)
                if current_track_path and path_map.get(current_track_path) is not None
                else state.get("current_index", 0)
            )
            self.player.current_index = current_index
            for attr in ("next_index", "prev_index"):
                setattr(self.player, attr, state.get(attr))
            track_state = (
                self.player.current_index,
                state.get("song_position"),
                state.get("volume"),
                state.get("play_mode")
            )
            self.player.load_tracks(self.player.rootpath, state=track_state)
            self.player.ui.switch_waveform(state.get("sw_wf", 2))
        except json.JSONDecodeError:
            self.load_state(self.default_state)
        except Exception as e:
            QMessageBox.warning(self.player.ui, "Произошла ошибка при загрузке состояния плеера:", str(e))
            self.load_state(self.default_state)


    def save_state(self, filename=None):
        if filename is None:
            filename = self.filename
        try:
            current_track_path = None
            index = self.player.current_index
            if (
                index is not None and
                0 <= index < self.player.ui.listbox.count()
            ):
                item = self.player.ui.listbox.item(index)
                if item is not None:
                    current_track_path = item.data(Qt.UserRole)
            state = {
                "rootpath": self.player.rootpath,
                "current_track_path": current_track_path,
                "current_index": self.player.current_index,
                "volume": self.player.ui.volume_slider.value(),
                "play_mode": self.player.mode,
                "song_position": self.player.sound_mx.get_time(),
                "device_1": self.player.device_1,
                "device_2": self.player.device_2,
                "active_device": self.player.active_device,
                "time_sleep": self.player.time_sleep,
                "next_index": self.player.next_index,
                "prev_index": self.player.prev_index,
                "sw_wf": self.player.ui.sw_wf,
                "length": self.player.length
            }
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(None, "Ошибка при сохранении состояния плеера:", str(e))

    def extract_audio_metadata(self, path):
        try:
            audio = File(path, easy=False)
            if audio is None:
                return {}
            info = getattr(audio, 'info', None)
            if info is None:
                return {}
            return {
                "duration": int(info.length * 1000),  # в миллисекундах
                "bitrate": getattr(info, 'bitrate', 0),
                "samplerate": getattr(info, 'sample_rate', 44100),
                "chans": getattr(info, 'channels', 2),
                "format": path.split('.')[-1].upper(),
                "size": os.path.getsize(path),
                "mtime": int(os.path.getmtime(path))
            }
        except Exception as e:
            print(f"Ошибка при обработке {path}: {e}")
            return {}

    def save_state_(self, filename=state_file_):
        if filename is None:
            filename = self.filename
        try:
            playlist = {
                "title": "Default",
                "contentDuration": 0,
                "contentFiles": 0,
                "contentSize": 0,
                "playbackCursor": self.player.current_index if self.player.current_index is not None else -1,
                "shuffled": getattr(self.player, 'shuffle', False),
                "userReordered": True,
                "tracks": []
            }
            total_duration = 0
            total_size = 0
            listbox = self.player.ui.listbox
            for i in range(listbox.count()):
                item = listbox.item(i)
                if item is None:
                    continue
                track_path = item.data(Qt.UserRole)
                if not track_path or not os.path.exists(track_path):
                    continue
                metadata = self.extract_audio_metadata(track_path)
                if not metadata:
                    continue
                track = {
                    "location": f"file:///{track_path.replace(os.sep, '/')}",
                    "duration": metadata["duration"],
                    "bitrate": metadata["bitrate"],
                    "samplerate": metadata["samplerate"],
                    "chans": metadata["chans"],
                    "format": metadata["format"],
                    "size": metadata["size"],
                    "queueIndex": i,
                    "mtime": metadata["mtime"],
                    "group": {
                        "title": os.path.dirname(track_path),
                        "state": 1
                    }
                }
                total_duration += track["duration"]
                total_size += track["size"]
                playlist["tracks"].append(track)
            playlist["contentDuration"] = total_duration
            playlist["contentFiles"] = len(playlist["tracks"])
            playlist["contentSize"] = total_size
            final_state = {
                "playlist": playlist
            }
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(final_state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(None, "Ошибка при сохранении плейлиста:", str(e))
