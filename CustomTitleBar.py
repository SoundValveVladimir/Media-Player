import os
import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenu, 
     QAction, QTabWidget, QWidget, QVBoxLayout, QSlider, QLabel, 
     QHBoxLayout, QPushButton, QDialog, QAbstractItemView, QListWidget, 
     QMessageBox, QSpacerItem, QSizePolicy, QCheckBox, QComboBox, QLineEdit
)
from PyQt5.QtGui import QCursor, QDoubleValidator
from PyQt5.QtCore import Qt, QSize
from Icon_Path import IconPath


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    full_path = f"{base_path}\\{relative_path}"
    return full_path

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_active = False
        self._drag_position = None
        self.normal_geometry = None
        self.init_ui()

    def init_ui(self):
        self.menu_button = QPushButton(self)
        self.menu_button.setFixedSize(25, 25)
        self.menu_button.setIconSize(QSize(25, 25))
        self.menu_button.setIcon(IconPath.LOG)
        self.menu_button.clicked.connect(self.show_menu)
        self.menu_button.setToolTip("Меню")
        
        self.minimize_button = QPushButton(self)
        self.minimize_button.setFixedSize(25, 25)
        self.minimize_button.setIconSize(QSize(15, 15))
        self.minimize_button.setIcon(IconPath.MINIMIZE)
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)
        self.minimize_button.setToolTip("Свернуть")
        
        self.maximize_button = QPushButton(self)
        self.maximize_button.setFixedSize(25, 25)
        self.maximize_button.setIcon(IconPath.MAXIMIZE)
        self.maximize_button.clicked.connect(self.toggle_maximize_restore)
        self.maximize_button.setToolTip("Развернуть")
        
        self.close_button = QPushButton(self)
        self.close_button.setFixedSize(25, 25)
        self.close_button.setIcon(IconPath.CLOSE)
        self.close_button.clicked.connect(self.parent_window.close)
        self.close_button.setToolTip("Закрыть")
        
        self.title_label = QLabel("SoundValve", self)
        self.title_label.setObjectName("title_label")
        
        hbox = QHBoxLayout(self)
        hbox.addWidget(self.menu_button)
        hbox.addWidget(self.title_label)
        hbox.addStretch()
        hbox.addWidget(self.minimize_button)
        hbox.addWidget(self.maximize_button)
        hbox.addWidget(self.close_button)
        
        self.setLayout(hbox)
        self.setFixedHeight(40)

    def show_menu(self):
        menu = QMenu(self)
        settings = menu.addAction("Настройки горячих клавиш")
        settings.triggered.connect(self.parent_window.show_outset)
        effects_action = menu.addAction("Регулировки и эффекты")
        effects_action.triggered.connect(self.open_audio_effects_window)
        about_action = menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)
        menu.exec_(QCursor.pos())

    def open_audio_effects_window(self):
        audio_effects_window = AudioEffectsWindow(self)
        audio_effects_window.exec_()

    def show_about(self):
        msg_box = QMessageBox(self)
        msg_box.setText("Название: SoundValve\n"
                        "Версия: 1.0\n"
                        "Описание: Это простой медиа-плеер.")
        msg_box.setWindowTitle("О программе")
        msg_box.setWindowOpacity(0.90)
        msg_box.exec_()

    def toggle_maximize_restore(self):
        if self.parent_window.isMaximized() or self.parent_window.isFullScreen():
            self.parent_window.showNormal()
            if self.normal_geometry:
                self.parent_window.setGeometry(self.normal_geometry)
            self.maximize_button.setIcon(IconPath.MAXIMIZE)
            self.maximize_button.setToolTip("Развернуть")
        else:
            self.normal_geometry = self.parent_window.geometry()
            self.parent_window.showMaximized()
            self.maximize_button.setIcon(IconPath.RESTORE)
            self.maximize_button.setToolTip("Восстановить")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPos() - self.parent_window.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_active:
            self.parent_window.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            event.accept()


class MouseEventHandler:
    def __init__(self):
        self.resize_origin = None
        self.start_geometry = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resize_origin = event.globalPos()
            self.start_geometry = self.frameGeometry()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.resize_origin is not None and event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.resize_origin
            new_width = max(self.minimumWidth(), self.start_geometry.width() + delta.x())
            new_height = max(self.minimumHeight(), self.start_geometry.height() + delta.y())
            screen = QApplication.screenAt(self.pos())
            if screen is None:
                screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            if self.x() + new_width > screen_geometry.right():
                new_width = screen_geometry.right() - self.x()
            if self.y() + new_height > screen_geometry.bottom():
                new_height = screen_geometry.bottom() - self.y()
            self.resize(new_width, new_height)
            self.update_waveform_height()
            self.title_bar.maximize_button.setIcon(IconPath.MAXIMIZE)
            self.title_bar.maximize_button.setToolTip("Развернуть")
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resize_origin = None
            event.accept()


class DraggableListWidget(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)


class AudioEffectsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регулировки и эффекты")
        self.setGeometry(100, 100, 900, 400)
        self.tab_menu = QTabWidget()

        self.audio_effects_tab = QWidget()
        self.video_effects_tab = QWidget()
        self.sync_tab = QWidget()

        self.tab_menu.addTab(self.audio_effects_tab, "Аудиоэффекты")
        self.tab_menu.addTab(self.video_effects_tab, "Видеоэффекты")
        self.tab_menu.addTab(self.sync_tab, "Синхронизация")

        self.equalizer_tab = EqualizerTab()
        self.comprission_tab = CompressionTab()
        self.surround_tab = SurroundTab()
        self.stereobase_tab = StereoBaseTab()
        self.additionally_tab = AdditionallyTab()

        self.tab_audio_effects = QTabWidget()

        self.tab_audio_effects.addTab(self.equalizer_tab, "Эквалайзер")
        self.tab_audio_effects.addTab(self.comprission_tab, "Сжатие")
        self.tab_audio_effects.addTab(self.surround_tab, "Объемное звучание")
        self.tab_audio_effects.addTab(self.stereobase_tab, "Расширение стереобазы")
        self.tab_audio_effects.addTab(self.additionally_tab, "Дополнительно")

        audio_layout = QVBoxLayout()
        audio_layout.addWidget(self.tab_audio_effects)
        self.audio_effects_tab.setLayout(audio_layout)

        self.button_save = QPushButton("Сохранить")
        self.button_close = QPushButton("Закрыть")
        self.button_save.clicked.connect(self.save_settings)
        self.button_close.clicked.connect(self.close)

        bottom_bar = QHBoxLayout()
        bottom_bar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        bottom_bar.addWidget(self.button_save)
        bottom_bar.addWidget(self.button_close)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tab_menu)
        main_layout.addLayout(bottom_bar)

        self.load_settings()

    def save_settings(self):
        self.equalizer_tab.save_eq_settings()
    
    def load_settings(self):
        self.equalizer_tab.load_eq_settings()


class EqualizerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_enabled = False
        self.slider_values = {}
        self.sliders = []
        self.save_index = None

        equalizer_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()

        self.enable_checkbox = QCheckBox("Включить")
        self.enable_checkbox.setChecked(self.set_enabled)
        self.enable_checkbox.toggled.connect(self.toggle_enable)
        top_bar_layout.addWidget(self.enable_checkbox)

        top_bar_layout.addStretch()

        preset_label = QLabel("Предустановка:")
        top_bar_layout.addWidget(preset_label)

        preset_combo = QComboBox()
        preset_combo.addItems([
            "По умолчанию", 
            "Поп", 
            "Рок", 
            "Клубная", 
            "Классика", 
            "Низкие", 
            "Низкие и Высокие",
            "Танцевальная",
            "Наушники",
            "Большой зал",
            "Концерт",
            "Вечеринка",
            "Регги",
            "СКА",
            "Легкая",
            "Легкий рок",
            "Техно"
        ])
        top_bar_layout.addWidget(preset_combo)

        equalizer_layout.addLayout(top_bar_layout)

        slider_layout = QHBoxLayout()
        min_val = -200
        max_val = 200
        float_step = 0.1
        num_sliders = 11
        frequencies = [
            "Предусилитель", "60Hz", 
            "170Hz", "310Hz", 
            "600Hz", "1kHz", 
            "3kHz", "6kHz", 
            "12kHz", "14kHz", "16kHz"
        ]

        for i in range(num_sliders):
            slider_col = QVBoxLayout()

            slider = QSlider(Qt.Vertical)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setFixedHeight(200)
            slider.setEnabled(self.set_enabled)
            slider.setValue(0)

            value_label = QLabel("0.0 db")
            value_label.setAlignment(Qt.AlignCenter)

            freq_label = QLabel(frequencies[i] if i < len(frequencies) else f"{i+1}")
            freq_label.setAlignment(Qt.AlignCenter)

            def make_handler(sl, lbl):
                def handler(val):
                    if -1 <= val <= 1:
                        val = 0
                        sl.blockSignals(True)
                        sl.setValue(val)
                        sl.blockSignals(False)
                    lbl.setText(f"{val * float_step:.1f} db")
                return handler

            slider.valueChanged.connect(make_handler(slider, value_label))
            slider_col.addWidget(value_label)
            slider_col.addWidget(slider, alignment=Qt.AlignCenter)
            slider_col.addWidget(freq_label)
            slider_layout.addLayout(slider_col)
            self.sliders.append(slider)

        equalizer_layout.addLayout(slider_layout)

        def on_preset_change(index):
            self.save_index = index
            presets = {
                "По умолчанию": [0] * num_sliders,
                "Поп": [6.0, -1.6, 4.8, 7.2, 8.0, 5.6, 0, -2.4, -2.4, -1.6, -1.6],
                "Рок": [5.0, 8.0, 4.8, -5.6, -8.0, -3.2, 4.0, 8.8, 11.2, 11.2, 11.2],
                "Клубная": [6.0, 0, 0, 8.0, 5.6, 5.6, 5.6, 3.2, 0, 0, 0],
                "Классика": [12.0, 0, 0, 0, 0, 0, 0, -7.2, -7.2, -7.2, -9.6],
                "Низкие": [5.0, -8.0, 9.6, 9.6, 5.6, 1.6, -4.0, -8.0, -10.3, -11.2, -11.2],
                "Низкие и Высокие": [4.0, 7.2, 5.6, 0, -7.2, -4.8, 1.6, 8.0, 11.2, 12.0, 12.0],
                "Высокие": [3.0, -9.6, -9.6, -9.6, -4.0, 2.4, 11.2, 16.0, 16.0, 16.0, 16.7],
                "Танцевальная": [5.0, 9.6, 7.2, 2.4, 0, 0, -5.6, -7.2, -7.2, 0, 0],
                "Наушники": [4.0, 4.8, 11.2, 5.6, -3.2, -2.4, 1.6, 4.8, 9.6, 12.8, 14.4],
                "Большой зал": [5.0, 10.3, 10.3, 5.6, 5.6, 0, -4.8, -4.8, -4.8, 0, 0],
                "Концерт": [7.0, -4.8, 0, 4.0, 5.6, 5.6, 5.6, 4.0, 2.4, 2.4, 2.4],
                "Вечеринка": [6.0, 7.2, 7.2, 0, 0, 0, 0, 0, 0, 7.2, 7.2],
                "Регги": [8.0, 0, 0, 0, -5.6, 0, 6.4, 6.4, 0, 0, 0],
                "СКА": [6.0, -2.4, -4.8, -4.0, 0, 4.0, 5.6, 8.8, 9.6, 11.2, 9.6],
                "Легкая": [5.0, 4.8, 1.6, 0, -2.4, 0, 4.0, 8.0, 9.6, 11.2, 12.0],
                "Легкий рок": [7.0, 4.0, 4.0, 2.4, 0, -4.0, -5.6, -3.2, 0, 2.4, 8.8],
                "Техно": [5.0, 8.0, 5.6, 0, -5.6, -4.8, 0, 8.0, 9.6, 9.6, 8.8]
            }

            preset_values = presets.get(preset_combo.currentText(), [0] * num_sliders)
            for i, slider in enumerate(self.sliders):
                value = preset_values[i] * 10
                slider.setValue(int(value))
                self.slider_values[f'slider_{i}'] = int(value)
            #print(self.slider_values)

        preset_combo.currentIndexChanged.connect(on_preset_change)

        def toggle_sliders(enabled):
            for s in self.sliders:
                s.setEnabled(enabled)
                self.set_enabled = enabled

        self.enable_checkbox.toggled.connect(toggle_sliders)
    
    def toggle_enable(self):
        """Обработчик для изменения состояния чекбокса"""
        self.set_enabled = self.enable_checkbox.isChecked()
        self.enable_checkbox.setText("Выключить" if self.set_enabled else "Включить")

    def save_eq_settings(self, filename=resource_path("\\Data\\eq_settings.json")):
        try:
            state = {
                "eq_settings": self.slider_values,
                "set_enabled": self.set_enabled,
                "save_index": self.save_index
            }
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)
            print("Сохранено")
        except Exception as e:
            QMessageBox.warning(None, "Ошибка при сохранении состояния эквалайзера:", str(e))

    def load_eq_settings(self, filename=resource_path("\\Data\\eq_settings.json")):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.set_enabled = state.get("set_enabled", False)
            self.slider_values = state.get("eq_settings", {})
            self.save_index = state.get("save_index", 0)

            for i, slider in enumerate(self.sliders):
                slider_value = self.slider_values.get(f'slider_{i}', 0)
                slider.setValue(slider_value)
            self.enable_checkbox.setChecked(self.set_enabled)
        except Exception as e:
            QMessageBox.warning(None, "Ошибка при загрузке состояния эквалайзера:", str(e))


class CompressionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_enabled = False
        self.slider_values = {}

        self.compressor_names = [
            "RMS/пик", "Время атаки", 
            "Время спада", "Порог", 
            "Коэффицент", "Радиус\nперегиб", 
            "Подъём\nуровня"
        ]

        sliders_config = [
            (0.0, 1.0, 0.01, "", "0.0"),               # RMS/пик
            (1.5, 400.0, 1.0, " мс", "1.5 мс"),        # Время атаки
            (2.0, 800.0, 1.0, " мс", "2.0 мс"),        # Время спада
            (-30.0, 0.0, 0.1, " dB", "-30 dB"),        # Порог
            (1.0, 20.0, 0.1, " :1", "1.0 : 1"),        # Коэффицент
            (1.0, 10.0, 0.1, " dB", "1.0 dB"),         # Радиус перегиб
            (0.0, 24.0, 0.1, " dB", "0.0 dB")          # Подъём уровня
        ]

        main_layout = QVBoxLayout(self)

        top_bar_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("Включить")
        self.enable_checkbox.setChecked(self.set_enabled)
        self.enable_checkbox.toggled.connect(self.toggle_enable)
        top_bar_layout.addWidget(self.enable_checkbox)
        top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)

        slider_layout = QHBoxLayout()
        self.sliders = []

        for i, (min_val, max_val, step, unit, default_label) in enumerate(sliders_config):
            layout = QVBoxLayout()

            value_label = QLabel(default_label)
            value_label.setAlignment(Qt.AlignCenter)

            slider = QSlider(Qt.Vertical)
            slider.setEnabled(self.set_enabled)
            slider.setFixedHeight(200)
            slider.setMinimum(0)
            slider.setMaximum(int((max_val - min_val) / step))
            slider.setValue(0)

            name_label = QLabel(self.compressor_names[i])
            name_label.setAlignment(Qt.AlignCenter)

            def make_handler(lbl, mn, stp, u, idx):
                return lambda val: self.update_slider_value(idx, mn + val * stp, lbl, u)

            slider.valueChanged.connect(
                make_handler(value_label, min_val, step, unit, i)
            )

            layout.addWidget(value_label)
            layout.addWidget(slider, alignment=Qt.AlignCenter)
            layout.addWidget(name_label)

            slider_layout.addLayout(layout)
            self.sliders.append(slider)

            self.slider_values[self.compressor_names[i]] = min_val

        main_layout.addLayout(slider_layout)

        def toggle_sliders(enabled):
            for s in self.sliders:
                s.setEnabled(enabled)
            self.set_enabled = enabled

        self.enable_checkbox.toggled.connect(toggle_sliders)

    def update_slider_value(self, idx, value, label, unit):
        label.setText(f"{value:.1f}{unit}")
        param_name = self.compressor_names[idx]
        self.slider_values[param_name] = value
        print(self.slider_values)

    def toggle_enable(self):
        self.set_enabled = self.enable_checkbox.isChecked()
        self.enable_checkbox.setText("Выключить" if self.set_enabled else "Включить")


class SurroundTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_enabled = False
        self.sliders = []
        self.slider_values = {}

        surround_names = [
            "Размер", 
            "Ширина", 
            "Сырой", 
            "Сухой", 
            "Влажный"
        ]

        sliders_config = [
            (0.0, 11.0, 1.0, "0.0"),    # Размер: от 0.0 до 11.0, шаг 1.0
            (0.0, 10.0, 1.0, "0.0"),    # Ширина: от 0.0 до 10.0
            (0.0, 10.0, 1.0, "0.0"),    # Сырой: от 0.0 до 10.0
            (0.0, 10.0, 1.0, "0.0"),    # Сухой: от 0.0 до 10.0
            (0.0, 10.0, 1.0, "0.0")     # Влажный: от 0.0 до 10.0
        ]

        main_layout = QVBoxLayout(self)

        top_bar_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("Включить")
        self.enable_checkbox.setChecked(self.set_enabled)
        self.enable_checkbox.toggled.connect(self.toggle_enable)
        top_bar_layout.addWidget(self.enable_checkbox)
        top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)

        slider_layout = QHBoxLayout()

        for i in range(len(sliders_config)):
            min_val, max_val, step, default_text = sliders_config[i]
            col_layout = QVBoxLayout()

            value_label = QLabel(default_text)
            value_label.setAlignment(Qt.AlignCenter)

            slider = QSlider(Qt.Vertical)
            slider.setFixedHeight(200)
            slider.setMinimum(int(min_val))
            slider.setMaximum(int(max_val))
            slider.setValue(int(float(default_text)))
            slider.setEnabled(self.set_enabled)

            name_label = QLabel(surround_names[i])
            name_label.setAlignment(Qt.AlignCenter)

            def make_handler(sl, lbl, mn, stp, idx):
                return lambda val: self.update_slider_value(idx, val, lbl, mn, stp)

            slider.valueChanged.connect(make_handler(slider, value_label, min_val, step, i))

            col_layout.addWidget(value_label)
            col_layout.addWidget(slider, alignment=Qt.AlignCenter)
            col_layout.addWidget(name_label)

            slider_layout.addLayout(col_layout)
            self.sliders.append(slider)

        main_layout.addLayout(slider_layout)

    def update_slider_value(self, idx, val, lbl, mn, stp):
        self.slider_values[self.sliders[idx].objectName()] = mn + val * stp
        lbl.setText(f"{mn + val * stp:.1f}")

    def toggle_enable(self):
        self.set_enabled = self.enable_checkbox.isChecked()
        self.enable_checkbox.setText("Выключить" if self.set_enabled else "Включить")
        for s in self.sliders:
            s.setEnabled(self.set_enabled)


class StereoBaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_enabled = False
        self.sliders = []
        stereobase_names = [
            "Время задержки", 
            "Усиление отзвука", 
            "Перекрещивание", 
            "Сухой звук"
        ]

        sliders_config = [
            (1.0, 100.0, 1.0, " мс", "0.0"),    # Время задержки
            (0.0, 0.9, 0.1, " %", "0.0"),        # Усиление отзвука
            (0.0, 0.8, 0.1, " %", "0.0"),        # Перекрещивание
            (0.0, 1.0, 0.1, " %", "0.0")         # Сухой звук
        ]

        main_layout = QVBoxLayout(self)

        top_bar_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("Включить")
        self.enable_checkbox.setChecked(self.set_enabled)
        self.enable_checkbox.toggled.connect(self.toggle_enable)
        top_bar_layout.addWidget(self.enable_checkbox)
        top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)

        slider_layout = QHBoxLayout()

        for i, config in enumerate(sliders_config):
            min_val, max_val, step, unit, default_text = config
            col_layout = QVBoxLayout()
            value_label = QLabel(default_text)
            value_label.setAlignment(Qt.AlignCenter)

            factor = 10 if step < 1 else 1
            slider = QSlider(Qt.Vertical)
            slider.setFixedHeight(200)
            slider.setMinimum(int(min_val * factor))
            slider.setMaximum(int(max_val * factor))
            slider.setValue(int(float(default_text) * factor))
            slider.setEnabled(self.set_enabled)

            name_label = QLabel(stereobase_names[i] if i < len(stereobase_names) else f"{i+1}")
            name_label.setAlignment(Qt.AlignCenter)

            def make_handler(lbl, mn, stp, u):
                return lambda val, lbl=lbl, mn=mn, stp=stp, u=u: lbl.setText(f"{mn + val * stp:.1f}{u}")
            slider.valueChanged.connect(make_handler(value_label, min_val, step, unit))

            col_layout.addWidget(value_label)
            col_layout.addWidget(slider, alignment=Qt.AlignCenter)
            col_layout.addWidget(name_label)

            slider_layout.addLayout(col_layout)
            self.sliders.append(slider)

        main_layout.addLayout(slider_layout)

    def toggle_enable(self):
        self.set_enabled = self.enable_checkbox.isChecked()
        self.enable_checkbox.setText("Выключить" if self.set_enabled else "Включить")
        for s in self.sliders:
            s.setEnabled(self.set_enabled)


class AdditionallyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_enabled = False
        self.slider_values = {}
        equalizer_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()

        self.enable_checkbox = QCheckBox("Включить")
        self.enable_checkbox.setChecked(self.set_enabled)
        self.enable_checkbox.toggled.connect(self.toggle_enable)
        top_bar_layout.addWidget(self.enable_checkbox)

        top_bar_layout.addStretch()

        equalizer_layout.addLayout(top_bar_layout)

        slider_layout = QHBoxLayout()
        min_val = -120
        max_val = 120
        float_step = 0.1
        sliders = []

        slider_col = QVBoxLayout()

        slider = QSlider(Qt.Vertical)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setFixedHeight(200)
        slider.setEnabled(self.set_enabled)
        slider.setValue(0)

        value_label = QLabel("semitones")
        value_label.setAlignment(Qt.AlignCenter)

        value_input = QLineEdit("0.0")
        value_input.setAlignment(Qt.AlignCenter)
        value_input.setFixedWidth(60)
        #value_input.setValidator(QDoubleValidator(-12.0, 12.0, 1))  # Ограничиваем ввод

        semitones_label = QLabel("Изменение высоты звука")
        semitones_label.setAlignment(Qt.AlignCenter)

        def slider_to_text_handler(sl, line_edit):
            def handler(val):
                float_val = val * float_step
                if -0.05 <= float_val <= 0.05:
                    float_val = 0.0
                    sl.blockSignals(True)
                    sl.setValue(0)
                    sl.blockSignals(False)
                line_edit.setText(f"{float_val:.1f}")
            return handler

        def text_to_slider_handler(sl):
            def handler():
                try:
                    float_val = float(value_input.text())
                    float_val = max(-12.0, min(12.0, float_val))
                    sl.setValue(int(round(float_val / float_step)))
                except ValueError:
                    pass
            return handler

        slider.valueChanged.connect(slider_to_text_handler(slider, value_input))
        value_input.editingFinished.connect(text_to_slider_handler(slider))

        slider_col.addWidget(value_input, alignment=Qt.AlignCenter)
        slider_col.addWidget(value_label)
        slider_col.addWidget(slider, alignment=Qt.AlignCenter)
        slider_col.addWidget(semitones_label)

        slider_layout.addLayout(slider_col)
        sliders.append(slider)

        equalizer_layout.addLayout(slider_layout)

        def toggle_sliders(enabled):
            for s in sliders:
                s.setEnabled(enabled)
                self.set_enabled = enabled

        self.enable_checkbox.toggled.connect(toggle_sliders)
    
    def toggle_enable(self):
        self.set_enabled = self.enable_checkbox.isChecked()
        self.enable_checkbox.setText("Выключить" if self.set_enabled else "Включить")