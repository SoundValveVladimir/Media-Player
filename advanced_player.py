import os
import glob
import time
import pyaudio
import random
import sounddevice as sd
import numpy as np
import soundfile as sf
import multiprocessing as mp
from multiprocessing import Process
from PyQt5.QtWidgets import (QAction, QApplication, QWidget,
    QMessageBox, QListWidgetItem, QFileDialog, QMenu, QListWidget
)
from PyQt5.QtGui import QIcon, QMouseEvent, QCursor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from pygame import mixer
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis
from State_Manager import StateManager
from Hotkeys import HotkeyManager
from UI import UI
from SavePaths import SavePathsThread

class AdvancedPlayer(QWidget):
    def __init__(self, default_mode='single_device'):
        super().__init__()
        self.ui = UI(self)
        self.hotkey_manager = HotkeyManager(self)
        self.mode = "sequential"
        self.ui.mode_button.clicked.connect(self.toggle_play_mode)
        self.ui.browse_button.clicked.connect(self.browse_menu)
        self.current_track_index = 0
        self.current_index = 0
        self.volume = 1.0
        self.is_muted = False
        self.is_playing = False
        self.play_mode = 'sequential'  # 'sequential', 'shuffle', 'repeat'
        self.default_mode = default_mode  # 'single_device' or 'multi_device'
        self.multi_device_enabled = True  # Включение режима на несколько устройств

    def browse_menu(self):
        with open("./Data/style2.qss", "r", encoding="utf-8") as style_file:
            browse_menu = QMenu(self)
            browse_menu.setStyleSheet(style_file.read())
        browse_action = QAction("Выбрать 📂", self)
        browse_action.triggered.connect(self.browse_directory)
        file_action = QAction("Выбрать ♫♫♫", self)
        file_action.triggered.connect(self.browse_files)
        add_action = QAction("Добавить ♫♫♫", self)
        add_action.triggered.connect(self.add_files)
        browse_menu.addAction(browse_action)
        browse_menu.addAction(file_action)
        browse_menu.addAction(add_action)
        browse_menu.exec_(QCursor.pos())

    def browse_directory(self):
        try: # Открываем диалог выбора директории
            directory = QFileDialog.getExistingDirectory(
                self, "Выберите 📂", "",  # Пустая строка означает, что будет использоваться текущий путь по умолчанию
                QFileDialog.ShowDirsOnly
            )
            if directory: # Если пользователь выбрал директорию, загружаем треки из выбранного каталога
                self.rootpath = os.path.normpath(directory)
                self.load_tracks(self.rootpath)
            else:
                pass
        except Exception as e: # Отображаем сообщение об ошибке, если что-то пошло не так
            QMessageBox.critical(
               self, "Ошибка", f"Произошла ошибка при выборе 📂: {str(e)}"
            )
            
    def browse_files(self):
        try:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Выбрать файлы ♫♫♫", "", "Audio Files (*.mp3 *.wav *.flac *.ogg)")
            if file_paths:
                self.rootpath = [os.path.normpath(path) for path in file_paths]
                self.load_tracks(self.rootpath)
            else:
                pass
        except Exception as e:
            QMessageBox.critical(
               self, "Ошибка", f"Произошла ошибка при выборе ♫♫♫: {str(e)}"
            )
            
    def add_files(self):
        try:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Выбрать файлы ♫♫♫", "", "Audio Files (*.mp3 *.wav *.flac *.ogg)")
            if file_paths:
                self.rootpath = [os.path.normpath(path) for path in file_paths]
                self.add_tracks(self.rootpath)
            else:
                print("Файлы ??? не выбраны.")
        except Exception as e:
            QMessageBox.critical(
               self, "Ошибка", f"Произошла ошибка при выборе ♫♫♫: {str(e)}"
            )

    def seconds_to_hh_mm_ss(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def save_listbox_paths(self): # Сохраняет полный путь каждого трека из списка listbox в self.rootpath.
        try:
            self.save_paths_thread = SavePathsThread(listbox=self.ui.listbox)
            self.save_paths_thread.finished.connect(self.handle_paths_saved)
            self.save_paths_thread.start()
        except Exception as e:
            QMessageBox.critical(
            self, "Ошибка", f"Произошла ошибка при запуске потока для сохранения путей: {str(e)}")

    def handle_paths_saved(self, paths):
        try:
            self.rootpath = paths
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Произошла ошибка при обработке сохраненных путей: {str(e)}")

    def load_tracks(self, rootpath, state=None):
        try:
            files = []
            if isinstance(rootpath, str) and os.path.exists(rootpath) and os.path.isdir(rootpath):  # Проверка директории
                formats = ["*.mp3", "*.wav", "*.flac", "*.ogg"]
                for pattern in formats:
                    files.extend(glob.glob(os.path.join(rootpath, pattern)))
                if not files:  # Проверка, пуста ли папка
                    QMessageBox.warning(self.ui, "Пустая папка", "Выбранная папка не содержит поддерживаемых аудиофайлов.", QMessageBox.Ok)
                    return
            elif isinstance(rootpath, list) and all(os.path.isfile(path) for path in rootpath):  # Проверка списка файлов
                files = rootpath
            else:
                QMessageBox.warning(self, "Неудалось загрузить треки")
                self.add_choose_item()
                return
            self.ui.listbox.clear()  # Очистка списка перед добавлением новых треков
            total_duration = 0  # Общая продолжительность всех треков
            unsupported_files = []
            for i, track_path in enumerate(files, start=1):
                try:
                    MAX_TEXT_LENGTH = 30
                    track_name = os.path.splitext(os.path.basename(track_path))[0]
                    if len(track_name) > MAX_TEXT_LENGTH:
                        track_name = track_name[:MAX_TEXT_LENGTH] + '...'
                    numbered_track_name = f"{i}. {track_name}"
                    item = QListWidgetItem(numbered_track_name)  # Создаем элемент списка с отображаемым именем трека
                    item.setData(Qt.UserRole, track_path)  # Сохраняем полный путь в пользовательских данных
                    self.ui.listbox.addItem(item)
                    track_duration = self.get_track_duration(track_path)
                    if track_duration is not None:
                        total_duration += track_duration  # Прибавляем продолжительность нового трека
                    else:
                        unsupported_files.append(track_path)
                except Exception as e:
                    unsupported_files.append(track_path)
            track_count = self.ui.listbox.count()
            self.ui.track_info_label.setText(f"♫ {track_count} | {self.seconds_to_hh_mm_ss(total_duration)}")
            self.ui.track_info_label.setToolTip(f"Количество ♫: {track_count} | Продолжительность: {self.seconds_to_hh_mm_ss(total_duration)}")
            if unsupported_files:
                QMessageBox.warning(self.ui, "Некоторые файлы не были загружены",
                    f"Не удалось загрузить следующие файлы:\n" + "\n".join(unsupported_files))
            # if state is not None:  # Обработка состояния при загрузке
            #     track_index, start_offset, volume, play_mode = state
            #     self.play_track(track_index=track_index, start_offset=start_offset)
            #     self.ui.volume_slider.setValue(volume)
            #     self.set_volume(volume)
            #     self.set_play_mode(play_mode)
            # else:  # Обычная загрузка
            #     if track_count > 0:  # Проверяем, есть ли треки для воспроизведения
            #         self.current_index = 0
            #         self.play_track(track_index=0, start_offset=0)
            #     else:
            #         self.add_choose_item()
        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка", f"Произошла ошибка при загрузке треков: {e}")
        finally:
            self.save_listbox_paths()

    def get_track_duration(self, track_path):
        try:
            if track_path.endswith(".mp3"):
                return MP3(track_path).info.length
            elif track_path.endswith(".flac"):
                return FLAC(track_path).info.length
            elif track_path.endswith(".wav"):
                return WAVE(track_path).info.length
            elif track_path.endswith(".ogg"):
                return OggVorbis(track_path).info.length
            else:
                raise ValueError("Неподдерживаемый формат файла")
        except Exception as e:
            raise Exception(f"Ошибка при получении продолжительности для {track_path}: {e}")

    def play_track(self, track_index=None, start_offset=0):
        if track_index is None:
            track_index = self.current_index
        QTimer.singleShot(0, lambda: self._play_track_internal(track_index, start_offset))

    def _play_track_internal(self, track_index, start_offset):
        try:
            if track_index is None or track_index < 0 or track_index >= self.ui.listbox.count():
                return  # Если индекс трека некорректен, не выполняем никаких действий
            item = self.ui.listbox.item(track_index) # Получаем элемент списка по индексу
            if not item:
                self.play_prev_next("next")
                raise FileNotFoundError("Трек не найден в списке.")
            if item.text() == "Выберите 📂 или ♫♫♫":
                return  # Прекращаем выполнение, если это не трек
            track_path = item.data(Qt.UserRole) # Извлекаем полный путь к файлу из данных элемента списка
            track_name = os.path.splitext(os.path.basename(track_path))[0]
            self.audio_file = track_path
            if self.multi_device_enabled:
                 self.play_on_multiple_devices(track_path)
            else:
                 mixer.init()
                 mixer.music.stop()
                 mixer.music.load(track_path) # Загружаем и 
                 mixer.music.play(start=start_offset) # воспроизводим трек с использованием полного пути
            self.current_index = track_index  # Сохраняем новый текущий индекс
            #self.track_started.emit()
            self.start_time = time.time() - start_offset # Обновляем интерфейс
            self.ui.track_label.setToolTip(f"Сейчас играет - {track_name}")
            MAX_TEXT_LENGTH = 30
            if len(track_name) > MAX_TEXT_LENGTH:
                track_name = track_name[:MAX_TEXT_LENGTH] + '...'
            self.ui.track_label.setText(f"♫ {track_name}")
            duration = self.get_track_duration(track_path)
            self.track_duration = int(duration)
            self.ui.song_position_slider.setMaximum(int(self.track_duration * 1000))
            self.ui.listbox.setCurrentRow(track_index)
            self.ui.play_pause_button.setIcon(self.ui.pause_img)
            self.ui.position_label_right.setText(self.seconds_to_mm_ss(self.track_duration)) # Обновляем продолжительность трека и интерфейс
            self.ui.song_position_slider.setValue(int(start_offset))
            self.slider_moved = False
            #self.calculate_next_track_index()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка воспроизведения", f"Произошла ошибка: {str(e)}")
            self.play_prev_next("next")

    def seconds_to_mm_ss(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes:02}:{seconds:02}"

    def play(self):
        """Запускает воспроизведение трека"""
        if self.current_track_index != -1:
            track = self.playlist_widget.item(self.current_track_index).text()
            print(f"Воспроизведение трека: {track}")
            self.is_playing = True
            # Логика воспроизведения трека (через PyAudio или другой метод)

            # Если активирован режим многопоточности:
            if self.multi_device_enabled:
                self.play_on_multiple_devices(track)

    def stop(self):
        """Останавливает воспроизведение"""
        self.is_playing = False
        print("Воспроизведение остановлено")
        # Логика остановки потока воспроизведения

    def pause(self):
        """Ставит воспроизведение на паузу"""
        if self.is_playing:
            self.is_playing = False
            print("Пауза")
            # Логика паузы

    def next_track(self):
        """Переключает на следующий трек"""
        if self.play_mode == 'shuffle':
            next_index = random.randint(0, self.playlist_widget.count() - 1)
        else:
            next_index = (self.current_track_index + 1) % self.playlist_widget.count()

        self.load_track(next_index)
        self.play()

    def prev_track(self):
        """Переключает на предыдущий трек"""
        prev_index = (self.current_track_index - 1) % self.playlist_widget.count()
        self.load_track(prev_index)
        self.play()

    def toggle_mute(self):
        """Включает/выключает звук"""
        self.is_muted = not self.is_muted
        if self.is_muted:
            print("Звук выключен")
        else:
            print("Звук включен")
        # Логика изменения уровня громкости (например, через PyAudio)

    def set_volume(self, level: float):
        """Устанавливает уровень громкости"""
        self.volume = level
        print(f"Уровень громкости установлен на: {level}")
        # Логика установки громкости

    def toggle_play_mode(self):
        """Переключает режим воспроизведения"""
        modes = ['sequential', 'shuffle', 'repeat']
        current_index = modes.index(self.play_mode)
        self.play_mode = modes[(current_index + 1) % len(modes)]
        print(f"Режим воспроизведения: {self.play_mode}")

    def play_on_multiple_devices(self, track_path):
        try:
            # Example of initializing a stream on multiple devices
            device_list = sd.query_devices()
            if len(device_list) > 1:
                data, sample_rate = sf.read(track_path)
                processes = []
                for device in device_list:
                    if device['max_output_channels'] >= 2:  # Assuming stereo output
                        p = Process(target=self.stream_audio, args=(data, sample_rate, device['name']))
                        p.start()
                        processes.append(p)
                for p in processes:
                    p.join()
            else:
                raise RuntimeError("Not enough devices for multi-device playback.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка воспроизведения", f"Ошибка многопоточного воспроизведения: {str(e)}")
        
    def stream_audio(self, data, sample_rate, device_name):
         sd.play(data, sample_rate, device=device_name)
         sd.wait()

    def update_progress(self, progress):
        """Обновляет прогресс трека"""
        print(f"Прогресс: {progress}%")
        # Логика обновления прогресс-бара интерфейса

    def toggle_multi_device_mode(self):
        """Включает/выключает режим многопоточности"""
        self.multi_device_enabled = not self.multi_device_enabled
        mode = "Многопоточность включена" if self.multi_device_enabled else "Многопоточность отключена"
        print(mode)

    def select_mode(self, mode):
        """Установка режима воспроизведения"""
        if mode == 'multi_device':
            self.multi_device_enabled = True
        else:
            self.multi_device_enabled = False
        print(f"Режим проигрывателя: {mode}")
