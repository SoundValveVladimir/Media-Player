import sys
import sounddevice as sd
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QComboBox,
                             QSlider, QHBoxLayout, QPushButton, QSpinBox)
from PyQt5.QtCore import Qt

class OutputSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.active_devices = self.list_active_devices()
        self.device_1 = None
        self.device_2 = None
        self.active_device = False
        self.time_sleep = 150  # Значение по умолчанию

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Настройки вывода устройств"))

        # Первая настройка устройства
        self.device_1_combo = QComboBox()
        self.device_1_combo.setEnabled(False)  # Отключено по умолчанию
        self.device_1_slider = QSlider(Qt.Horizontal)
        self.device_1_slider.setFixedWidth(30)
        self.device_1_slider.setMinimum(0)
        self.device_1_slider.setMaximum(1)
        self.device_1_slider.setValue(0)  # По умолчанию выключено
        self.device_1_slider.valueChanged.connect(self.toggle_device_1)

        device_1_layout = QHBoxLayout()
        device_1_layout.addWidget(QLabel("Устройство 1:"))
        device_1_layout.addWidget(self.device_1_combo)
        device_1_layout.addWidget(self.device_1_slider)

        layout.addLayout(device_1_layout)

        # Вторая настройка устройства
        self.device_2_combo = QComboBox()
        self.device_2_combo.setEnabled(False)  # Отключено по умолчанию
        self.device_2_slider = QSlider(Qt.Horizontal)
        self.device_2_slider.setFixedWidth(30)
        self.device_2_slider.setMinimum(0)
        self.device_2_slider.setMaximum(1)
        self.device_2_slider.setValue(0)  # По умолчанию выключено
        self.device_2_slider.valueChanged.connect(self.toggle_device_2)

        device_2_layout = QHBoxLayout()
        device_2_layout.addWidget(QLabel("Устройство 2:"))
        device_2_layout.addWidget(self.device_2_combo)
        device_2_layout.addWidget(self.device_2_slider)

        layout.addLayout(device_2_layout)

        # Заполняем оба ComboBox списком активных устройств
        for index, name in self.active_devices:
            self.device_1_combo.addItem(name, index)
            self.device_2_combo.addItem(name, index)

        # Настройка задержки
        self.sleep_spinner = QSpinBox()
        self.sleep_spinner.setValue(self.time_sleep)
        self.sleep_spinner.setRange(0, 5000)
        layout.addWidget(QLabel("Настройка времени ожидания (мс):"))
        layout.addWidget(self.sleep_spinner)
        
        # Кнопка сохранения
        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.clicked.connect(self.save_settings)
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("Настройки вывода")

    def list_active_devices(self):
        # Пример использования sounddevice для получения списка устройств
        devices = sd.query_devices()
        active_devices = []
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                active_devices.append((i, device['name']))
        return active_devices

    def toggle_device_1(self, value):
        # Активировать/деактивировать QComboBox для устройства 1
        if value == 1:
            self.device_1_combo.setEnabled(True)
        else:
            self.device_1_combo.setEnabled(False)

        # Обновление статуса активного устройства
        self.update_active_device_status()

    def toggle_device_2(self, value):
        # Активировать/деактивировать QComboBox для устройства 2
        if value == 1:
            self.device_2_combo.setEnabled(True)
        else:
            self.device_2_combo.setEnabled(False)

        # Обновление статуса активного устройства
        self.update_active_device_status()

    def update_active_device_status(self):
        # Проверка, активированы ли оба устройства
        if self.device_1_slider.value() == 1 and self.device_2_slider.value() == 1:
            self.parent.player.active_device = True
        else:
            self.parent.player.active_device = False

    def save_settings(self):
        if self.device_1_slider.value() == 1:
            self.parent.player.device_1 = self.device_1_combo.currentData()

        if self.device_2_slider.value() == 1:
            self.parent.player.device_2 = self.device_2_combo.currentData()

        self.parent.player.time_sleep = self.sleep_spinner.value()

        print(f"Устройство 1: {self.parent.player.device_1 if self.device_1_slider.value() == 1 else 'не выбрано'}")
        print(f"Устройство 2: {self.parent.player.device_2 if self.device_2_slider.value() == 1 else 'не выбрано'}")
        print(f"Active Device: {self.parent.player.active_device}")
        print(f"Задержка между воспроизведением: {self.parent.player.time_sleep} мс")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    settings_window = OutputSettings()
    settings_window.show()
    sys.exit(app.exec_())
