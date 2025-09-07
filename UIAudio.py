import os, sys, re, humanize, mimetypes
from PyQt5.QtWidgets import (QApplication, QToolTip, QWidget, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QSlider, QMessageBox,
    QListWidget, QLabel, QMenu, QGraphicsDropShadowEffect, QStackedWidget,
    QStyledItemDelegate, QListWidgetItem, QSizePolicy, QFrame, QInputDialog
)
from PyQt5.QtGui import QColor, QDragEnterEvent, QDropEvent, QFontMetrics, QPixmap, QGuiApplication
from PyQt5.QtCore import  Qt, QPropertyAnimation, QRect, QSettings, Qt, QTimer, QSize, QEvent, QPoint
from CustomTitleBar import *
from Waveform import *
from Test import OutputSettings
from default_styles import default_stylesheet
from Icon_Path import IconPath
from Progress import AudioSlider


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    full_path = f"{base_path}\\{relative_path}"
    return full_path


class AudioUI(QWidget, MouseEventHandler):
    def __init__(self, player):
        super().__init__()
        MouseEventHandler.__init__(self)
        self.player = player
        self.audio_managers = {}
        self.created_waveforms = {}
        self.waveform_actions = []
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowState(Qt.WindowNoState)
        self.setMouseTracking(True)
        self.init_ui()
        self.sw_wf = None
        self.is_fullscreen = False
        self.previous_geometry = None
        self.new_waveform_height = 90
        self.settings = QSettings('SoundValve', 'WindowState')
        self.restore_window_state()
        self.file_path = None

    def restore_window_state(self):
        geometry = self.settings.value('window_geometry')
        if geometry:
            self.setGeometry(geometry)

    def init_ui(self):
        self.setWindowTitle("SoundValve")
        window_width = 460
        window_height = 600
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        center_x = (screen_rect.width() - window_width) // 2
        center_y = (screen_rect.height() - window_height) // 2
        self.setGeometry(center_x, center_y, window_width, window_height)
        self.setMinimumSize(460, 600)
        self.setAcceptDrops(True)
        IconPath.load_icons()
        
        self.title_bar = CustomTitleBar(self)
        
        self.listbox = TrackListWidget(self)
        
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Введите текст для поиска...")
        self.search_field.textChanged.connect(self.highlight_items)
        self.search_field.setVisible(False)
        
        self.track_info_label = QLabel(f"♫ 0 | 00:00:00", self)
        self.track_info_label.setAlignment(Qt.AlignTop)
        self.track_info_label.setObjectName("track_info_label")
        
        self.wave_form = QStackedWidget(self)
        self.wave_form.setFixedHeight(90)
        self.wave_form.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wave_form.customContextMenuRequested.connect(self.show_waveform_menu)

        self.placeholder_label = QLabel(self)
        self.placeholder_label.setPixmap(IconPath.WAVE)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.wave_form.addWidget(self.placeholder_label)

        self.forms = {
            1: lambda: SoundRef(self.get_audio_manager(3), run=True),
            2: lambda: SoundVeins(self.get_audio_manager(3), run=True),
            3: lambda: SoundColorRef(self.get_audio_manager(3), run=True),
            4: lambda: SoundEchoGlow(self.get_audio_manager(3), run=True),
            5: lambda: SoundBlueEchoes(self.get_audio_manager(3), run=True),
            6: lambda: SoundRipple(self.get_audio_manager(3), run=True),
            7: lambda: SoundSpectrumRing(self.get_audio_manager(3), run=True),
            8: lambda: SoundGlowing(self.get_audio_manager(3), run=True),
        }
        # for key, form_factory in self.forms.items():
        #     widget = form_factory()
        #     self.forms[key] = widget
        #     self.wave_form.addWidget(widget)
        
        self.track_label = QLabel("Трек не выбран", self)
        self.track_label.setFixedHeight(20)
        self.track_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.track_label.setObjectName("track_label")

        self.pos_label_left = QLabel("00:00", self)
        self.pos_label_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.pos_label_left.setObjectName("position_label_left")
        self.pos_label_left.setFixedWidth(50)
        self.pos_label_right = QLabel("00:00", self)
        self.pos_label_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pos_label_right.setObjectName("position_label_right")
        self.pos_label_right.setFixedWidth(50)
        
        # self.song_pos_slider = QSlider(Qt.Horizontal, self)
        # self.song_pos_slider.setMouseTracking(True)

        self.song_pos_slider_2 = AudioSlider(self.player.audio_file)
        self.song_pos_slider_2.setFixedHeight(20)
        self.song_pos_slider_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.slider_container = QWidget(self)
        self.slider_container.setFixedSize(14, 100)
        self.slider_container.setVisible(False)

        self.slider_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.slider_container.setStyleSheet("background: transparent;")

        self.volume_slider = QSlider(Qt.Vertical, self.slider_container)
        self.volume_slider.setGeometry(-3, 0, 20, 100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(10)
        self.volume_slider.setAttribute(Qt.WA_TranslucentBackground, True)
        self.volume_slider.setStyleSheet("background: transparent;")
        
        self.prev_button = QPushButton(self)
        self.prev_button.setFixedSize(25, 25)
        self.prev_button.setIconSize(QSize(16, 16))
        self.prev_button.setIcon(IconPath.PREV)
        self.prev_button.setToolTip("Предыдущий трек")
        
        self.play_pause_button = QPushButton(self)
        self.play_pause_button.setFixedSize(32, 32)
        self.play_pause_button.setIconSize(QSize(27, 27))
        self.play_pause_button.setIcon(IconPath.PLAY)
        self.play_pause_button.setToolTip("Воспроизведение")
        
        self.stop_button = QPushButton(self)
        self.stop_button.setFixedSize(25, 25)
        self.stop_button.setIconSize(QSize(16, 16))
        self.stop_button.setIcon(IconPath.STOP)
        self.stop_button.setToolTip("Остановить")
        
        self.next_button = QPushButton(self)
        self.next_button.setFixedSize(25, 25)
        self.next_button.setIconSize(QSize(16, 16))
        self.next_button.setIcon(IconPath.NEXT)
        self.next_button.setToolTip("Следующий трек")
        
        self.browse_button = QPushButton(self)
        self.browse_button.setFixedSize(25, 25)
        self.browse_button.setIconSize(QSize(18, 18))
        self.browse_button.setIcon(IconPath.BROWSE)
        self.browse_button.setToolTip("Выбрать папку/треки")
        
        self.mute_button = QPushButton(self)
        self.mute_button.setFixedSize(25, 25)
        self.mute_button.setIconSize(QSize(16, 16))
        self.mute_button.setIcon(IconPath.MUTE)
        self.mute_button.setToolTip("Выключить звук 🔇")
        self.installEventFilter(self)
        self.mute_button.installEventFilter(self)
        self.volume_slider.installEventFilter(self)
        self.slider_container.installEventFilter(self)
        
        self.mode_button = QPushButton(self)
        self.mode_button.setFixedSize(25, 25)
        self.mode_button.setIconSize(QSize(16, 16))
        self.mode_button.setIcon(IconPath.SEQUENTIAL)
        self.mode_button.setToolTip("Обычный > Случайный")
        
        self.clear_button = QPushButton(self)
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.setIconSize(QSize(16, 16))
        self.clear_button.setIcon(IconPath.CLEAR)
        self.clear_button.setToolTip("Очистить список треков")
        
        self.search_button = QPushButton()
        self.search_button.setFixedSize(25,25)
        self.search_button.setIconSize(QSize(16,16))
        self.search_button.setIcon(IconPath.SEARCH)
        self.search_button.clicked.connect(self.toggle_search_field)
        self.search_button.setToolTip("Показать поиск")

        self.fulls_btn = QPushButton()
        self.fulls_btn.setFixedSize(25, 25)
        self.fulls_btn.setIcon(IconPath.FULLSCREEN)
        self.fulls_btn.clicked.connect(self.toggle_fullscreen)
        self.fulls_btn.setToolTip("Полноэкранный режим")
        
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(10)
        shadow_effect.setOffset(0, 0)
        shadow_effect.setColor(QColor(0, 0, 0, 160))
        self.slider_container.setGraphicsEffect(shadow_effect)
      
        title_bar_hbox = QVBoxLayout()
        title_bar_hbox.addWidget(self.title_bar)
        
        searchbox = QHBoxLayout()
        searchbox.addWidget(self.search_field)
        searchbox.addStretch()
        searchbox.addWidget(self.search_button)

        vbox = QVBoxLayout()
        vbox.addLayout(searchbox)
        vbox.addWidget(self.listbox)
        title_bar_hbox.addLayout(vbox)
        
        tilbox = QHBoxLayout()
        tilbox.addWidget(self.track_info_label)
        tilbox.addStretch()
        tilbox.addWidget(self.clear_button)
        vbox.addLayout(tilbox)
        
        lbox = QHBoxLayout()
        lbox.addWidget(self.wave_form)
        vbox.addLayout(lbox)

        tbox = QHBoxLayout()
        tbox.addWidget(self.track_label)
        vbox.addLayout(tbox)

        hbox = QHBoxLayout()
        hbox.addWidget(self.pos_label_left)
        hbox.addWidget(self.song_pos_slider_2)
        hbox.addWidget(self.pos_label_right)
        vbox.addLayout(hbox)

        control_hbox = QHBoxLayout()
        control_hbox.addWidget(self.browse_button)
        control_hbox.addWidget(self.prev_button)
        control_hbox.addWidget(self.play_pause_button)
        control_hbox.addWidget(self.stop_button)
        control_hbox.addWidget(self.next_button)
        control_hbox.addWidget(self.mode_button)
        control_hbox.addWidget(self.mute_button)
        control_hbox.addWidget(self.fulls_btn)
        vbox.addLayout(control_hbox)
        self.setLayout(title_bar_hbox)

        self.progress_timer = QTimer()
        self.progress_timer.start(500)

        self.save_state_timer = QTimer()
        self.save_state_timer.start(1000)

    def get_audio_manager(self, id):
        if id not in self.audio_managers:
            if id == 1:
                self.audio_managers[1] = AudioManager_1()
            elif id == 2:
                self.audio_managers[2] = AudioManager_2()
            elif id == 3:
                self.audio_managers[3] = AudioManager(profile_id=0)
        return self.audio_managers[id]

    def switch_waveform(self, waveform_type):
        if waveform_type == "off":
            self.wave_form.setCurrentWidget(self.placeholder_label)
            self.sw_wf = waveform_type
            return

        if waveform_type not in self.created_waveforms:
            if waveform_type not in self.forms:
                print(f"Форма {waveform_type} не найдена!")
                return
            # Создание и добавление в стек
            widget = self.forms[waveform_type]()
            if widget is None:
                print(f"Не удалось создать визуализацию {waveform_type}")
                return
            self.created_waveforms[waveform_type] = widget
            self.wave_form.addWidget(widget)

        self.wave_form.setCurrentWidget(self.created_waveforms[waveform_type])
        self.sw_wf = waveform_type
        self.update_waveform_menu()

    def create_waveform_menu(self):
        waveform_menu = QMenu(self)
        items = [
            ("SoundOff", "off"),
            ("SoundRef", 1),
            ("SoundVeins", 2),
            ("SoundColorRef", 3),
            ("SoundEchoGlow", 4),
            ("SoundBlueEchoes", 5),
            ("SoundRipple", 6),
            ("SoundSpectrumRing", 7),
            ("SoundGlowing", 8)
        ]
        for name, val in items:
            action = waveform_menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, v=val: self.switch_waveform(v))
            self.waveform_actions.append((action, val))
        self.update_waveform_menu()
        return waveform_menu

    def update_waveform_menu(self):
        for action, val in self.waveform_actions:
            if val == self.sw_wf:
                action.setChecked(True)
            else:
                action.setChecked(False)

    def show_waveform_menu(self, position):
        waveform_menu = self.create_waveform_menu()
        global_pos = self.wave_form.mapToGlobal(position)

        if self.isFullScreen():
            waveform_menu.raise_()
            waveform_menu.activateWindow()
            
        waveform_menu.exec_(global_pos)
        
    def highlight_items(self):
        search_text = self.search_field.text().lower()
        self.listbox.clearSelection()
        if search_text.isdigit():
            index = int(search_text) - 1
            if 0 <= index < self.listbox.count():
                self.listbox.setCurrentRow(index)
        else:
            for i in range(self.listbox.count()):
                item = self.listbox.item(i)
                if search_text in item.text().lower():
                    item.setSelected(True)
                    self.listbox.scrollToItem(item)
                    
    def toggle_search_field(self):
        if self.search_field.isVisible():
            self.search_field.setVisible(False)
            self.search_button.setToolTip("Показать поиск")
            if self.player.current_index is not None:
                self.listbox.setCurrentRow(self.player.current_index)
        else:
            self.search_field.setVisible(True)
            self.search_button.setToolTip("Скрыть поиск")
        
    def eventFilter(self, obj, event):
        try:
            if obj == self.mute_button:
                if event.type() == QEvent.Enter:
                    self.slider_container.setVisible(True)
                    self.slider_container.raise_()
                    self.update_slider_position()
                elif event.type() == QEvent.Leave:
                    QTimer.singleShot(500, self.hide_slider_if_not_hovered)
            elif obj == self.slider_container or obj == self.volume_slider:
                if event.type() == QEvent.Enter:
                    self.slider_container.setVisible(True)
                elif event.type() == QEvent.Leave:
                    QTimer.singleShot(500, self.hide_slider_if_not_hovered)
            return super().eventFilter(obj, event)
        except Exception as e:
            print(f"Ошибка в eventFilter: {e}")
            return False
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
        
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if not file_paths:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить треки !!!")
            return
        files = []
        folders = []
        for path in file_paths:
            norm_path = os.path.normpath(path)
            if os.path.isdir(norm_path):
                folders.append(norm_path)
            elif os.path.isfile(norm_path):
                files.append(norm_path)
        if files or folders:
            msg_box = QMessageBox(self)
            msg_box.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
            msg_box.setWindowTitle("Выбор действия")
            msg_box.setText("Что вы хотите сделать?")
            msg_box.setInformativeText("Загрузить треки или добавить к уже существующим?")
            load_button = msg_box.addButton("Загрузить", QMessageBox.AcceptRole)
            add_button = msg_box.addButton("Добавить", QMessageBox.AcceptRole)
            cancel_button = msg_box.addButton("Отмена", QMessageBox.RejectRole)
            msg_box.setMinimumSize(300, 100)
            msg_box.setWindowOpacity(0.90)
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            if clicked_button == load_button:
                if files:
                    self.player.load_tracks(files)
                if folders:
                    for folder in folders:
                        self.player.load_tracks(folder)
            elif clicked_button == add_button:
                if files:
                    self.player.add_tracks(files)
                if folders:
                    for folder in folders:
                        self.player.add_tracks(folder)
            elif clicked_button == cancel_button:
                pass

    def listbox_hover_event(self, event):
        item = self.listbox.itemAt(event.pos())
        if item:
            track_path = self.player.playlist[self.listbox.row(item)]
            self.show_preview_tooltip(track_path)

    def show_preview_tooltip(self, track_path):
        duration = self.audio_manager.get_duration(track_path)
        size = os.path.getsize(track_path) / (1024*1024)
        tooltip = f"Длительность: {duration}\nРазмер: {size:.1f} MB"
        QToolTip.showText(QCursor.pos(), tooltip)      

    def hide_slider_if_not_hovered(self):
        if not self.slider_container.underMouse() and not self.mute_button.underMouse():
            self.slider_container.setVisible(False)
            
    def update_slider_position(self):
        button_rect = self.mute_button.rect()
        global_button_pos = self.mute_button.mapToGlobal(button_rect.topLeft())
        parent_rect = self.mute_button.parentWidget().rect()
        parent_global_pos = self.mute_button.parentWidget().mapToGlobal(parent_rect.topLeft())
        local_button_pos = global_button_pos - parent_global_pos
        container_x = local_button_pos.x() + (button_rect.width() - self.slider_container.width()) // 2
        container_y = local_button_pos.y() - self.slider_container.height()
        container_x = max(0, container_x)
        container_y = max(0, container_y)
        container_x = min(self.width() - self.slider_container.width(), container_x)
        container_y = min(self.height() - self.slider_container.height(), container_y)
        self.slider_container.move(container_x, container_y)

    def update_play_mode_icon(self, mode):
        if mode == "sequential": self.mode_button.setIcon(IconPath.SEQUENTIAL)
        elif mode == "shuffle": self.mode_button.setIcon(IconPath.SHUFFLE)
        elif mode == "repeat": self.mode_button.setIcon(IconPath.REPEAT)

    def show_outset(self):
        self.player.hotkey_manager.open_settings_window()

    def resizeEvent(self, event):
        self.update_waveform_height()

    def update_waveform_height(self):
        window_height = self.height()
        wave_h = max(90, int(window_height * 0.2 + 10))
        song_h = int(window_height / 10) * 0.4
        self.wave_form.setFixedHeight(wave_h)
        self.song_pos_slider_2.setFixedHeight(int(song_h))

    def update_waveform_height_f(self):
        window_height = self.height()
        wave_h = max(90, int(window_height * 0.8))
        song_h = int(window_height * 0.1)
        self.wave_form.setFixedHeight(wave_h)
        self.song_pos_slider_2.setFixedHeight(int(song_h))

    def click_full_screen(self):
        if self.isActiveWindow():
            self.fulls_btn.click()

    def fake_fullscreen(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        self.previous_geometry = self.geometry()
        self.setGeometry(screen_geometry)
        self.show()

    def exit_fake_fullscreen(self):
        self.setGeometry(self.previous_geometry)
        self.show()

    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            screen = QGuiApplication.screenAt(self.frameGeometry().center())
            if screen:
                self.window().windowHandle().setScreen(screen)

            self.previous_geometry = self.geometry()
            self.showFullScreen()
            self.fullscreen_mode_elements()
            self.fulls_btn.setIcon(IconPath.NORMAL_SCREEN)
            self.update_waveform_height_f()
            self.fulls_btn.setToolTip("Выход из полноэкранного режима")
        else:
            self.showNormal()
            if hasattr(self, 'previous_geometry'):
                self.setGeometry(self.previous_geometry)
            self.restore_ui_elements() 
            self.update_waveform_height()
            self.fulls_btn.setIcon(IconPath.FULLSCREEN)
            self.fulls_btn.setToolTip("Полноэкранный режим")
        self.is_fullscreen = not self.is_fullscreen

    def fullscreen_mode_elements(self):
        self.title_bar.setVisible(False)
        self.listbox.setVisible(False)
        self.search_button.setVisible(False)
        self.search_field.setVisible(False)
        self.track_info_label.setVisible(False)
        self.browse_button.setVisible(False)
        self.clear_button.setVisible(False)
        self.update()

    def restore_ui_elements(self):
        self.title_bar.setVisible(True)
        self.listbox.setVisible(True)
        self.search_button.setVisible(True)
        self.track_info_label.setVisible(True)
        self.browse_button.setVisible(True)
        self.clear_button.setVisible(True)
        self.update()

    def closeEvent(self, event):
        self.settings.setValue('window_geometry', self.geometry())
        for manager in self.audio_managers.values():
            if hasattr(manager, "close") and callable(manager.close):
                manager.close()
        event.accept

class TrackWidget(QWidget):
    def __init__(self, numbered, track_name, track_duration):
        super().__init__()
        self.numbered_widget = QListWidget(self)
        self.numbered_widget.setFixedSize(60, 23)
        self._make_passthrough(self.numbered_widget)

        self.track_name_widget = QListWidget(self)
        self.track_name_widget.setFixedHeight(23)
        self._make_passthrough(self.track_name_widget)

        self.track_duration_widget = QListWidget(self)
        self.track_duration_widget.setFixedSize(60, 23)
        self._make_passthrough(self.track_duration_widget)

        self.numbered_widget.addItem(numbered)
        self.track_name_widget.addItem(track_name)
        self.track_duration_widget.addItem(track_duration)

        layout = QHBoxLayout(self)
        layout.addWidget(self.numbered_widget)
        layout.addWidget(self.track_name_widget)
        layout.addWidget(self.track_duration_widget)
        self.setLayout(layout)

    def _make_passthrough(self, lw: QListWidget):
        lw.setFrameShape(QFrame.NoFrame)
        lw.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lw.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lw.setFocusPolicy(Qt.NoFocus)
        lw.setSelectionMode(QListWidget.NoSelection)
        lw.setAttribute(Qt.WA_TransparentForMouseEvents)

class TrackListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setMouseTracking(True)


    def event(self, event):
        if event.type() == QEvent.ToolTip:
            item = self.itemAt(event.pos())
            if item:
                path = item.data(Qt.UserRole)
                if not path or not os.path.exists(path):
                    QToolTip.showText(event.globalPos(), "Файл не найден")
                    return True
                try:
                    size_bytes = os.path.getsize(path)
                    size_str = humanize.naturalsize(size_bytes, binary=True)
                except Exception:
                    size_str = "Неизвестно"
                format_guess, _ = mimetypes.guess_type(path)
                file_format = format_guess or os.path.splitext(path)[1][1:].upper()
                duration_str = "Неизвестно"
                widget = self.itemWidget(item)
                if widget and hasattr(widget, "track_duration_widget"):
                    try:
                        duration_str = widget.track_duration_widget.item(0).text()
                    except Exception:
                        pass
                tooltip = (
                    f"Путь: {path}\n"
                    f"Размер: {size_str}\n"
                    f"Формат: {file_format}\n"
                    f"Длительность: {duration_str}")
                QToolTip.showText(event.globalPos(), tooltip)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)

    def show_context_menu(self, position: QPoint, ):
        item = self.itemAt(position)
        menu = QMenu(self)
        if item:
            rename_action = QAction("Переименовать", self)
            delete_from_list_action = QAction("Удалить из списка", self)
            delete_local_action = QAction("Удалить файл с диска", self)
            rename_action.triggered.connect(lambda: self.rename_item(item))
            delete_from_list_action.triggered.connect(lambda: self.remove_item_from_list(item))
            delete_local_action.triggered.connect(lambda: self.delete_local_file(item))
            menu.addAction(rename_action)
            menu.addAction(delete_from_list_action)
            menu.addAction(delete_local_action)
        add_tracks_action = QAction("Добавить треки", self)
        clear_playlist_action = QAction("Очистить плейлист", self)
        add_tracks_action.triggered.connect(self.parent.player.browse_files)
        clear_playlist_action.triggered.connect(self.clear)
        menu.addSeparator()
        menu.addAction(add_tracks_action)
        menu.addAction(clear_playlist_action)
        menu.exec_(self.mapToGlobal(position))

    def remove_item_from_list(self, item):
        row = self.parent.listbox.row(item)
        self.parent.listbox.takeItem(row)
        self.parent.player.calculate_next_track_index()
        self.recalculate_track_info()
        self.parent.player.save_listbox_paths()

    def recalculate_track_info(self):
        total_tracks = self.parent.listbox.count()
        total_seconds = 0
        for i in range(total_tracks):
            item = self.parent.listbox.item(i)
            widget = self.parent.listbox.itemWidget(item)
            if widget:
                duration_str = widget.track_duration_widget.item(0).text()
                total_seconds += self.hh_mm_ss_to_seconds(duration_str)
        duration_formatted = self.seconds_to_hh_mm_ss(total_seconds)
        self.parent.track_info_label.setText(f"♫ {total_tracks} | {duration_formatted}")

    def hh_mm_ss_to_seconds(self, time_str):
        parts = list(map(int, time_str.strip().split(":")))
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h, m, s = 0, *parts
        else:
            h, m, s = 0, 0, parts[0]
        return h * 3600 + m * 60 + s

    def seconds_to_hh_mm_ss(self, total_seconds):
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def sanitize_filename(self, name):
        return re.sub(r'[\\/:*?"<>|]', '', name)

    def rename_item(self, item):
        current_widget = self.itemWidget(item)
        old_name = current_widget.track_name_widget.item(0).text()
        new_name, ok = QInputDialog.getText(self, "Переименование", "Новое имя:", text=old_name)
        if not (ok and new_name.strip()):
            return
        new_name = self.sanitize_filename(new_name.strip())
        if new_name == old_name:
            return
        path = item.data(Qt.UserRole)
        ext = os.path.splitext(path)[1]
        new_path = os.path.join(os.path.dirname(path), new_name + ext)
        current_widget.track_name_widget.clear()
        current_widget.track_name_widget.addItem(new_name)
        is_current = (self.parent.listbox.row(item) == self.parent.player.current_index)
        position = 0
        if is_current:
            position = self.parent.player.sound_mx.get_time()
            self.parent.player.sound_mx.stop()
        try:
            os.rename(path, new_path)
            item.setData(Qt.UserRole, new_path)
            self.parent.player.save_listbox_paths()
            if is_current:
                self.parent.player.play_track(
                    track_index=self.parent.player.current_index,
                    start_offset=position)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось переименовать файл:\n{e}")
            current_widget.track_name_widget.clear()
            current_widget.track_name_widget.addItem(old_name)

    def delete_local_file(self, item):
        path = item.data(Qt.UserRole)
        if os.path.exists(path):
            confirm = QMessageBox.question(
                self, "Удаление файла",
                f"Удалить файл:\n{path} ?",
                QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                try:
                    is_current = (self.parent.listbox.row(item) == self.parent.player.current_index)
                    if is_current:
                        self.parent.next_button.click()
                    os.remove(path)
                    self.takeItem(self.row(item))
                    self.recalculate_track_info()
                    index = self.parent.player.current_index - 1
                    self.parent.player.current_index = index
                    self.parent.player.calculate_next_track_index()
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось удалить файл:\n{e}")
