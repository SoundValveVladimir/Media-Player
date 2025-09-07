from operator import iconcat
import os
import sys
import time
import glob
import random
import Icon_Path
import sound_mx
from mutagen import File
from functools import partial
from PyQt5.QtWidgets import (QAction, QWidget,
    QMessageBox, QListWidgetItem, QFileDialog, QMenu, QToolTip
)
from PyQt5.QtGui import QMouseEvent, QCursor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QCoreApplication
from State_Manager import StateManager
from Hotkeys import HotkeyManager
from UIAudio import AudioUI, TrackWidget
from UIVideo import VideoUI
from SavePaths import SavePathsThread
from Icon_Path import IconPath

class BasicPlayer(QWidget):
    track_started = pyqtSignal()
    track_stopped = pyqtSignal()
    track_finished = pyqtSignal()

    def __init__(self, command_line_tracks=None):
        super().__init__()
        self.audio_file = StateManager.load_file(self)
        self.instance = sound_mx.Instance()
        self.sound_mx = self.instance.media_player_new()
        self.sound_mx.event_manager().event_attach(sound_mx.EventType.MediaPlayerEndReached, self._on_vlc_track_end)
        self.device_1 = None
        self.device_2 = None
        self.duration = 0
        self.active_device = False
        self.last_click_time = 0
        self.click_delay = 0.2
        self.time_sleep = 150
        self.current_index = 0
        self.start_offset = 0
        self.start_time = 0
        self.paused_time = 0
        self.track_duration = 0
        self.saved_volume = 0
        self.saved_volume_watcher = 0
        self.next_index = 0
        self.prev_index = 0
        self.call_calculate = 0
        self.run_watcher = True
        self.stop_flag = False
        self.is_muted = False
        self.is_playing = False
        self.is_paused = False
        self.slider_moved = False
        self.is_dragging = False
        self.repeat_mode = False
        self.shuffle_mode = False
        self.manual_switch_requested = False
        self.mute_icon_priority = False
        self.mode = "sequential"
        self.rootpath = ''
        self.length = ''
        self.player_mode = True
        if self.player_mode:
            self.ui = AudioUI(self)
            self.ui.mode_button.clicked.connect(self.toggle_play_mode)
            self.ui.browse_button.clicked.connect(self.browse_menu)
            self.ui.play_pause_button.clicked.connect(self.play_pause_toggle)
            self.ui.stop_button.clicked.connect(self.stop)
            self.ui.prev_button.clicked.connect(partial(self.play_prev_next, "prev"))
            self.ui.next_button.clicked.connect(partial(self.play_prev_next, "next"))
            self.ui.volume_slider.valueChanged.connect(self.set_volume)
            self.ui.mute_button.clicked.connect(self.toggle_mute)
            # self.ui.song_pos_slider.mousePressEvent = self.slider_mouse_event
            # self.ui.song_pos_slider.mouseReleaseEvent = self.slider_mouse_event
            # self.ui.song_pos_slider.mouseMoveEvent = self.slider_mouse_event
            self.ui.clear_button.clicked.connect(self.clear_listbox)
            self.ui.listbox.itemClicked.connect(self.play_selected_track)
            self.ui.listbox.itemActivated.connect(self.play_selected_track)
            self.ui.progress_timer.timeout.connect(self.update_progress)
            self.ui.save_state_timer.timeout.connect(self.save_playback_state)
        else:
            self.ui = VideoUI(self)
        self.track_started.connect(self.on_track_started)
        self.track_stopped.connect(self.on_track_stopped)
        self.track_finished.connect(self.on_track_finished)
        self.volume_watcher = VolumeWatcher(self)
        self.volume_watcher.volume_changed.connect(self.on_external_volume_changed)
        self.volume_watcher.start()
        self.state_manager = StateManager(self)
        self.hotkey_manager = HotkeyManager(self)

        self.ui.song_pos_slider_2.positionChanged.connect(self.set_player_position)

        if command_line_tracks:
            self.load_tracks(command_line_tracks)
        else:
            self.state_manager.load_state()
    
    def _on_vlc_track_end(self, event):
        self.track_finished.emit()

    def on_track_finished(self):
        if self.mode == "repeat" or self.manual_switch_requested:
            self.play_track()
            self.manual_switch_requested = False
        else:
            self.play_prev_next("next")

    def click_full_screen(self):
        self.ui.click_full_screen()
        
    @pyqtSlot()
    def on_track_started(self):
        self.is_playing = True
        self.is_paused = False
        self.ui.play_pause_button.setIcon(IconPath.PAUSE)
        self.ui.play_pause_button.setToolTip("Пауза")

    @pyqtSlot()
    def on_track_stopped(self):
        self.is_playing = False
        self.is_paused = False
        self.ui.play_pause_button.setIcon(IconPath.PLAY)
        self.ui.track_label.setText("▄︻デ══━一💥")
        #self.ui.song_pos_slider.setValue(0)
        self.ui.pos_label_left.setText('00:00')
        self.ui.play_pause_button.setToolTip("Воспроизведение")
        
    def load_tracks(self, rootpath, state=None):
        try:
            files = self.collect_tracks(rootpath)
            if not files:
                #QMessageBox.warning(self.ui, "Ошибка загрузки", "Не удалось загрузить треки.", QMessageBox.Ok)
                self.add_choose_item()
                return

            self.ui.listbox.clear()
            tracks, total_duration, unsupported = self.prepare_track_entries(files)
            self.add_tracks_to_listbox(tracks)
            count = self.ui.listbox.count()
            self.ui.track_info_label.setText(f"♫ {count} | {self.seconds_to_hh_mm_ss(total_duration)}")
            self.ui.track_info_label.setToolTip(
                f"Количество ♫: {count} | Продолжительность: {self.seconds_to_hh_mm_ss(total_duration)}"
            )
            if unsupported:
                QMessageBox.warning(
                    self.ui, "Некоторые файлы не загружены",
                    "Не удалось загрузить:\n" + "\n".join(unsupported),
                    QMessageBox.Ok
                )
            if state:
                idx, offset, vol, mode = state
                self.play_track(track_index=idx, start_offset=offset)
                self.ui.volume_slider.setValue(vol)
                self.set_volume(vol)
                self.set_play_mode(mode)
            else:
                if count:
                    self.current_index = 0
                    self.play_track(track_index=0, start_offset=0)
                else:
                    self.add_choose_item()
        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка", f"При загрузке треков: {e}")
        finally:
            self.save_listbox_paths()

    def add_tracks(self, rootpath):
        try:
            files = self.collect_tracks(rootpath)
            if not files:
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить треки.")
                return
            for i in range(self.ui.listbox.count()):
                item = self.ui.listbox.item(i)
                if item.text() == "Выберите 📂 или ♫♫♫":
                    self.ui.listbox.takeItem(i)
                    break
            existing_text = self.ui.track_info_label.text()
            if existing_text:
                existing_info = existing_text.split(" | ")
                existing_track_count = int(existing_info[0].split("♫ ")[1])
                existing_duration = self.hh_mm_ss_to_seconds(existing_info[1])
            else:
                existing_track_count = 0
                existing_duration = 0
            existing_paths = {self.ui.listbox.item(i).data(Qt.UserRole) for i in range(self.ui.listbox.count())}
            tracks, added_duration, unsupported_files = self.prepare_track_entries(files, start_index=existing_track_count + 1, existing_paths=existing_paths)
            self.add_tracks_to_listbox(tracks)
            total_duration = existing_duration + added_duration
            track_count = self.ui.listbox.count()
            self.ui.track_info_label.setText(f"♫ {track_count} | {self.seconds_to_hh_mm_ss(total_duration)}")
            self.ui.track_info_label.setToolTip(
                f"Количество ♫: {track_count} | Продолжительность: {self.seconds_to_hh_mm_ss(total_duration)}"
            )
            if unsupported_files:
                QMessageBox.warning(self, "Некоторые файлы не были загружены",
                                    "Не удалось загрузить следующие файлы:\n" + "\n".join(unsupported_files))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при загрузке треков: {e}")
        finally:
            self.save_listbox_paths()
            if self.sound_mx and self.sound_mx.is_playing():
                if self.ui.listbox.count() > 1:
                    self.calculate_next_track_index()
            else:
                if self.ui.listbox.count() > 0:
                    self.play_track(track_index=0, start_offset=0)

    def add_tracks_to_listbox(self, tracks):
        for numbered, name, path, duration_str, _ in tracks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, path)
            widget = TrackWidget(numbered, name, duration_str)
            item.setSizeHint(widget.sizeHint())
            self.ui.listbox.addItem(item)
            self.ui.listbox.setItemWidget(item, widget)

    def prepare_track_entries(self, files, start_index=1, existing_paths=None):
        total_duration = 0
        unsupported_files = []
        tracks = []
        for i, path in enumerate(files, start=start_index):
            if existing_paths and path in existing_paths:
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            if len(name) > 50:
                name = name[:30] + "..."
            numbered = f"{i}"
            name = f"{name}"
            duration = self.get_track_duration(path)
            if duration is not None:
                duration_str = self.seconds_to_mm_ss(duration)
                total_duration += duration
            else:
                duration_str = "??:??"
                unsupported_files.append(path)
            tracks.append((numbered, name, path, duration_str, duration))
        return tracks, total_duration, unsupported_files

    def collect_tracks(self, rootpath):
        files = []
        if isinstance(rootpath, str) and os.path.exists(rootpath) and os.path.isdir(rootpath):
            formats = [
                "*.mp3", "*.wav", "*.flac", "*.ogg", "*.aac",
                "*.m4a", "*.wma", "*.opus", "*.alac", "*.aiff",
                "*.amr", "*.ape", "*.wv", "*.mpc", "*.spx", 
                "*.cached", "*.mp4","*.mkv"
            ]
            for pattern in formats:
                files.extend(glob.glob(os.path.join(rootpath, pattern)))
        elif isinstance(rootpath, list) and all(os.path.isfile(path) for path in rootpath):
            files = rootpath
        else:
            return None
        return files if files else None
            
    def get_track_duration(self, track_path):
        try:
            audio = File(track_path)
            if audio is None or not hasattr(audio, 'info') or not hasattr(audio.info, 'length'):
                return None
            return int(audio.info.length)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при обработке файла {track_path}:\n{e}")
            return None
        
    def save_listbox_paths(self):
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
            
    def clear_listbox(self):
        self.ui.listbox.clear()
        self.rootpath = ""
        self.ui.track_info_label.clear()
        self.ui.track_info_label.setText("♫ 0 | 00:00:00")
        self.ui.pos_label_right.setText("00:00")
        self.ui.track_info_label.setToolTip("Список треков пуст")
        self.current_index = None 
        self.stop()
        self.add_choose_item()
       
    def add_choose_item(self):
        choose_item = QListWidgetItem("Выберите 📂 или ♫♫♫")
        self.ui.listbox.addItem(choose_item)
        self.ui.listbox.itemClicked.connect(self.handle_item_click)
        
    def handle_item_click(self, item):
        if item.text() == "Выберите 📂 или ♫♫♫": 
            menu = QMenu(self.ui)
            choose_folder_action = menu.addAction("Выбрать 📂")
            choose_files_action = menu.addAction("Выбрать ♫♫♫")
            action = menu.exec_(self.ui.listbox.mapToGlobal(self.ui.listbox.pos()))
            if action is None:
                return
            if action == choose_folder_action:
                self.browse_directory()
            elif action == choose_files_action:
                self.browse_files()
            self.ui.listbox.clearSelection()

    def play_selected_track(self, item):
        if item.text() == "Выберите 📂 или ♫♫♫":
            return
        selected_index = self.ui.listbox.row(item)
        if selected_index == self.current_index:
            if self.sound_mx.is_playing():
                self.play_pause_toggle()
            else:
                self.play_pause_toggle()
        else:
            self.current_index = selected_index
            self.play_track(self.current_index, start_offset=0)

    def play_track(self, track_index=None, start_offset=0):
        if track_index is None:
            track_index = self.current_index
        self._play_track_internal(track_index, start_offset)

    def _play_track_internal(self, track_index, start_offset):
        try:
            if track_index is None or track_index < 0 or track_index >= self.ui.listbox.count():
                return
            item = self.ui.listbox.item(track_index)
            if not item:
                self.play_prev_next("next")
                raise FileNotFoundError("Трек не найден в списке.")
            if item.text() == "Выберите 📂 или ♫♫♫":
                return
            track_path = item.data(Qt.UserRole)
            track_name = os.path.splitext(os.path.basename(track_path))[0]
            if self.sound_mx and self.sound_mx.is_playing():
                self.sound_mx.stop()
            self.run_watcher = False
            media = self.instance.media_new(track_path)
            self.ui.song_pos_slider_2.set_audio_file(track_path)
            #self.ui.analysis_manager.set_audio_file(track_path)
            self.sound_mx.set_media(media)
            self.sound_mx.play()
            self.run_watcher = True
            time.sleep(0.1)
            self.sound_mx.set_time(int(start_offset))
            self.current_index = track_index
            self.calculate_next_track_index()
            self.track_started.emit()
            self.ui.track_label.setToolTip(f"Сейчас играет - {track_name}")
            MAX_TEXT_LENGTH = 30
            if len(track_name) > MAX_TEXT_LENGTH:
                track_name = track_name[:MAX_TEXT_LENGTH] + '...'
            self.ui.track_label.setText(f"♫ {track_name}")
            self.track_duration = self.sound_mx.get_length()
            self.length = self.track_duration
            #self.ui.song_pos_slider.setMaximum(self.track_duration)
            self.ui.listbox.setCurrentRow(track_index)
            self.ui.pos_label_right.setText(self.milliseconds_to_mm_ss(self.track_duration))
            self.slider_moved = False
        except Exception as e:
            QMessageBox.critical(self, "Ошибка воспроизведения", f"Произошла ошибка: {str(e)}")
            self.play_prev_next("next")    
   
    def pause(self):
        try:
            if self.is_playing:
                if not self.is_paused:
                    self.paused_time = time.time() - self.start_time
                    self.is_paused = True
                    self.sound_mx.pause()
                    self.ui.play_pause_button.setIcon(IconPath.PLAY)
                    self.ui.play_pause_button.setToolTip("Воспроизведение")
                else:
                    self.start_time = time.time() - self.paused_time
                    self.is_paused = False
                    self.sound_mx.play()
                    self.ui.play_pause_button.setIcon(IconPath.PAUSE)
                    self.ui.play_pause_button.setToolTip("Пауза")
        except Exception as e:
            print("Произошла ошибка во время паузы:", str(e))

    def play_pause_toggle(self):
        if self.is_playing:
            self.pause()
        else:
            self.play_track()

    def stop(self):
        try:
            if self.is_playing:
                self.sound_mx.stop()
                self.track_stopped.emit()
                self.ui.song_pos_slider_2.set_position(0)
                self.ui.play_pause_button.setIcon(IconPath.PLAY)
        except Exception as e:
            print("Произошла ошибка при остановке:", str(e))

    def play_prev_next(self, direction):
        current_time = time.time()
        if current_time - self.last_click_time < self.click_delay:
            return
        self.last_click_time = current_time
        self.ui.pos_label_left.setText("00:00")
        self.manual_switch_requested = True
        try:
            if direction == "next":
                track_index = self.next_index
            elif direction == "prev":
                track_index = self.prev_index
            track_index = max(0, min(track_index, self.ui.listbox.count() - 1))
            #self.ui.song_pos_slider.setValue(0)
            self.start_time = 0
            self.paused_time = 0
            self.play_track(track_index)
        except Exception as e:
            QMessageBox.warning(self, f"Произошла ошибка при переключении на {'следующий' if direction == 'next' else 'предыдущий'} трек:", str(e))
        finally:
            self.manual_switch_requested = False

    def calculate_next_track_index(self):
        track_count = self.ui.listbox.count()
        if track_count == 0:
            self.next_index = None
            self.prev_index = None
            return
        if self.shuffle_mode and track_count > 2:
            self.next_index = random.randint(0, track_count - 1)
            options = [i for i in range(track_count) if i != self.next_index]
            self.prev_index = random.choice(options)
        else:
            if self.current_index is None or not (0 <= self.current_index < track_count):
                self.current_index = 0
            self.next_index = (self.current_index + 1) % track_count
            self.prev_index = (self.current_index - 1) % track_count
            
    def update_tooltip(self):
        if self.is_playing and not self.is_paused or self.is_paused:
            for direction in ["next", "prev"]:
                index = {"next": self.next_index, "prev": self.prev_index}[direction]
                item = self.ui.listbox.item(index)
                if item is None:
                    self.ui.next_button.setToolTip("Следующий: Список пуст")
                    self.ui.prev_button.setToolTip("Предыдущий: Список пуст")
                    return

                data = item.data(Qt.UserRole)
                if not isinstance(data, str) or not data:
                    tooltip_text = f"{'Следующий' if direction == 'next' else 'Предыдущий'}: неизвестно"
                else:
                    track_name = os.path.splitext(os.path.basename(data))[0]
                    tooltip_text = f"{'Следующий' if direction == 'next' else 'Предыдущий'}: {track_name}"

                getattr(self.ui, f"{direction}_button").setToolTip(tooltip_text)
        else:
            self.ui.next_button.setToolTip("Следующий: Список пуст")
            self.ui.prev_button.setToolTip("Предыдущий: Список пуст")

    def on_external_volume_changed(self, new_volume):
        self.ui.volume_slider.setValue(new_volume)

    def set_volume(self, volume):
        volume = max(0, min(volume, 100))
        if self.sound_mx:
            current_volume = self.sound_mx.audio_get_volume()
            if current_volume != volume:
                self.sound_mx.audio_set_volume(volume)
                self.saved_volume_watcher = volume
        if not self.mute_icon_priority:
            icon_vol = self.icon_vol(volume)
            self.ui.mute_button.setIcon(icon_vol)
        self.ui.mute_button.update()
        self.ui.volume_slider.setToolTip(f"🔊 {volume}%")

    def icon_vol(self, volume):
        if volume == 0:
            icon_vol = IconPath.VOL_1
        elif volume < 25:
            icon_vol = IconPath.VOL_2
        elif volume < 50:
            icon_vol = IconPath.VOL_3
        elif volume < 75:
            icon_vol = IconPath.VOL_4
        else:
            icon_vol = IconPath.VOL_4
        return icon_vol

    def handle_volume_change(self):
        volume = self.ui.volume_slider.value()
        self.set_volume(volume)
        self.ui.volume_slider.setToolTip(f"🔊 {volume}%")

    def increase_volume(self):
        if self.sound_mx:
            current_volume = self.sound_mx.audio_get_volume()
            new_volume = min(current_volume + 10, 100)
            self.set_volume(new_volume)
            self.ui.volume_slider.setValue(new_volume)

    def decrease_volume(self):
        if self.sound_mx:
            current_volume = self.sound_mx.audio_get_volume()
            new_volume = max(current_volume - 10, 0)
            self.set_volume(new_volume)
            self.ui.volume_slider.setValue(new_volume)

    def toggle_mute(self):
        self.mute_icon_priority = True
        if not self.is_muted:
            if self.sound_mx:
                self.saved_volume = self.sound_mx.audio_get_volume()
                self.sound_mx.audio_set_volume(0)
            self.ui.mute_button.setIcon(IconPath.VOL_1)
            self.ui.volume_slider.setValue(0)
            self.ui.mute_button.setToolTip("Включить звук 🔊")
            self.is_muted = True
            self.run_watcher = False
        else:
            if self.sound_mx:
                self.sound_mx.audio_set_volume(self.saved_volume)
            self.ui.volume_slider.setValue(self.saved_volume)
            icon_vol = self.icon_vol(self.saved_volume)
            self.ui.mute_button.setIcon(icon_vol)
            self.ui.mute_button.setToolTip("Выключить звук 🔇")
            self.is_muted = False
            self.run_watcher = True
        self.mute_icon_priority = False
        self.ui.mute_button.update()

    def update_progress(self):
        if self.sound_mx and self.sound_mx.is_playing() and not self.is_paused and not self.slider_moved:
            elapsed_time = self.sound_mx.get_time()
            #self.ui.song_pos_slider.setValue(elapsed_time)
            self.ui.pos_label_left.setText(self.milliseconds_to_mm_ss(elapsed_time))
            self.ui.song_pos_slider_2.set_position(elapsed_time)
            # self.ui.analyzer.get_amplitude(elapsed_time)
            # self.ui.wave_time(elapsed_time)

    def save_playback_state(self):
        if self.sound_mx and self.sound_mx.is_playing():
            self.state_manager.save_state()
            self.update_tooltip()

    def handle_track_end(self):
        if self.mode == "repeat" or self.manual_switch_requested:
            self.play_track()
            self.manual_switch_requested = False
        else:
            self.play_prev_next("next")
                    
    def set_player_position(self, value):
        if self.sound_mx:
            self.sound_mx.set_time(int(value))
            #self.ui.song_pos_slider.setValue(int(value))
            self.ui.pos_label_left.setText(self.milliseconds_to_mm_ss(int(value)))
                
    # def slider_mouse_event(self, event):
    #     if not isinstance(event, QMouseEvent):
    #         return
    #     pos = event.pos()
    #     slider_min = self.ui.song_pos_slider.minimum()
    #     slider_max = self.ui.song_pos_slider.maximum()
    #     value = slider_min + (slider_max - slider_min) * pos.x() / self.ui.song_pos_slider.width()
    #     value = max(slider_min, min(value, slider_max))
    #     if value == slider_max:
    #         value -= 500
    #     value = max(slider_min, value)
    #     tooltip_text = self.milliseconds_to_mm_ss(int(value))
    #     QToolTip.showText(event.globalPos(), tooltip_text, self)
    #     if event.type() == QMouseEvent.MouseButtonPress:
    #         self.is_dragging = True
    #         self.slider_moved = True
    #         self.mouse_pressed = True
    #         self.ui.song_pos_slider.setValue(int(value))
    #     elif event.type() == QMouseEvent.MouseMove and self.is_dragging:
    #         self.ui.song_pos_slider.setValue(int(value))
    #         self.handle_mouse_move(value)
    #     elif event.type() == QMouseEvent.MouseButtonRelease:
    #         self.is_dragging = False
    #         if self.mouse_pressed:
    #             self.handle_mouse_press(value)
    #         self.mouse_pressed = False
    #         self.handle_mouse_release(value)
    #         self.slider_moved = False

    # def handle_mouse_press(self, value):
    #     self.is_dragging = True
    #     self.slider_moved = True
    #     self.set_player_position(value)

    # def handle_mouse_move(self, value):
    #     if self.is_dragging:
    #         slider_min = 0
    #         slider_max = self.ui.song_pos_slider.maximum()
    #         value = max(slider_min, min(value, slider_max))
    #         if value < slider_min or value > slider_max:
    #             return
    #         self.ui.song_pos_slider.setValue(int(value))
    #         self.ui.pos_label_left.setText(self.milliseconds_to_mm_ss(int(value)))

    # def handle_mouse_release(self, value):
    #     self.is_dragging = False
    #     if self.slider_moved:
    #         self.set_player_position(value)
    #         self.slider_moved = False

    def milliseconds_to_mm_ss(self, milliseconds):
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02}:{seconds:02}"

    def seconds_to_mm_ss(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes:02}:{seconds:02}"
    
    def seconds_to_hh_mm_ss(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def hh_mm_ss_to_seconds(self, hh_mm_ss):
        h, m, s = map(int, hh_mm_ss.split(":"))
        return h * 3600 + m * 60 + s
    
    def browse_menu(self):
        browse_menu = QMenu(self.ui)
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
        try:
            directory = QFileDialog.getExistingDirectory(
                self, "Выберите 📂", "",
                QFileDialog.ShowDirsOnly
            )
            if directory:
                audio_extensions = ('.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a', '.wma', '.opus', '.alac', '.aiff', '.amr', '.ape', '.wv', '.mpc', '.spx')
                track_files = []
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(audio_extensions):
                            track_files.append(os.path.join(root, file))
                if not track_files:
                    QMessageBox.information(self, "Нет треков", "В выбранной папке нет аудиофайлов.")
                    return
                self.rootpath = [os.path.normpath(path) for path in track_files]
                self.load_tracks(self.rootpath)
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Произошла ошибка при выборе 📂: {str(e)}"
            )
            
    def browse_files(self):
        try:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Выбрать файлы ♫♫♫",
                "",
                'Audio Files (*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma *.opus *.alac *.aiff *.amr *.ape *.wv *.mpc *.spx)'
            )
            if file_paths:
                self.rootpath = [os.path.normpath(path) for path in file_paths]
                self.load_tracks(self.rootpath)
            else:
                print("Файлы ♫♫♫ не выбраны.")
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Произошла ошибка при выборе ♫♫♫: {str(e)}"
            )
            
    def add_files(self):
        try:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Выбрать файлы ♫♫♫", "",
                'Audio Files (*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma *.opus *.alac *.aiff *.amr *.ape *.wv *.mpc *.spx)'
            )
            if file_paths:
                self.rootpath = [os.path.normpath(path) for path in file_paths]
                self.add_tracks(self.rootpath)
            else:
                print("Файлы ♫♫♫ не выбраны.")
        except Exception as e:
            QMessageBox.critical(
               self, "Ошибка", f"Произошла ошибка при выборе ♫♫♫: {str(e)}"
            )

    def toggle_play_mode(self):
        if self.mode == "sequential":
            self.set_play_mode("shuffle")
        elif self.mode == "shuffle":
            self.set_play_mode("repeat")
        elif self.mode == "repeat":
            self.set_play_mode("sequential")

    def set_play_mode(self, mode):
        self.mode = mode
        if mode == "sequential":
            self.ui.update_play_mode_icon(mode)
            self.shuffle_mode = False
            self.repeat_mode = False
            if self.is_playing and not self.is_paused:
                self.calculate_next_track_index()
            self.ui.mode_button.setToolTip("Обычный > Случайный")
        elif mode == "shuffle":
            self.ui.update_play_mode_icon(mode)
            self.shuffle_mode = True
            self.repeat_mode = False
            if self.is_playing and not self.is_paused:
                self.calculate_next_track_index()
            self.ui.mode_button.setToolTip("Случайный > Повтор")
        elif mode == "repeat":
            self.ui.update_play_mode_icon(mode)
            self.shuffle_mode = False
            self.repeat_mode = True
            if self.is_playing and not self.is_paused:
                self.calculate_next_track_index()
            self.ui.mode_button.setToolTip("Повтор > Обычный")
            
    def closeEvent(self, event):
        self.volume_watcher.stop()
        self.state_manager.save_state()
        QCoreApplication.quit()


class VolumeWatcher(QThread):
    volume_changed = pyqtSignal(int)

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.last_volume = self.player.sound_mx.audio_get_volume()
        self.e = 0

    def run(self):
        while True:
            if self.player.run_watcher:
                current_volume = self.player.sound_mx.audio_get_volume()
                if current_volume == -1:
                    # self.e += 1
                    # print(f"{self.e} значение: {current_volume}")
                    time.sleep(0.05)
                    continue
                if current_volume != self.last_volume:
                    self.last_volume = current_volume
                    self.volume_changed.emit(current_volume)
            time.sleep(1)