import win32con
import win32gui
import win32api
import win32event
import pywintypes
import json
import os, sys
import ctypes
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent
from pynput import keyboard as pkb

VK_MAP = {
    "media_play_pause": 0xB3,
    "media_next": 0xB0,
    "media_previous": 0xB1,
    "media_stop": 0xB2,
    "page_up": 0x21,
    "page_down": 0x22,
    "f11": win32con.VK_F11,
}

MOD_NONE = 0x0000

def is_numlock_on():
    return ctypes.windll.user32.GetKeyState(0x90) & 1 == 1

def resource_path(relative_path):
    """Получение абсолютного пути до ресурса"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)

    full_path = f"{base_path}\\{relative_path}"
    return full_path

hotkey_file = resource_path("Data\\hotkeys.json")

class HotkeyListenerThread(QThread):
    hotkeyPressed = pyqtSignal(str)

    def __init__(self, hotkeys):
        super().__init__()
        self.hotkeys = hotkeys
        self.running = True
        self.hotkey_ids = {}

    def run(self):
        # Создаём невидимое окно для перехвата сообщений
        self.hwnd = win32gui.CreateWindowEx(
            0, "STATIC", "HotkeyListener", 0, 0, 0, 0, 0, 0, 0, 0, None
        )

        # Регистрируем горячие клавиши
        i = 1
        for action, keyname in self.hotkeys.items():
            vk = VK_MAP.get(keyname.lower())
            if vk:
                try:
                    win32gui.RegisterHotKey(self.hwnd, i, MOD_NONE, vk)
                    self.hotkey_ids[i] = action
                    i += 1
                except pywintypes.error as e:
                    if e.winerror == 1409:
                        print(f"Горячая клавиша {keyname} уже зарегистрирована, пропуск.")
                    else:
                        raise

        # Главный цикл обработки сообщений
        while self.running:
            msg = win32gui.GetMessage(self.hwnd, 0, 0)
            if msg:
                if msg[1][1] == win32con.WM_HOTKEY:
                    hotkey_id = msg[1][2]
                    action = self.hotkey_ids.get(hotkey_id)
                    if action:
                        self.hotkeyPressed.emit(action)

        # Очистка при завершении
        self.unregister_hotkeys()
        win32gui.DestroyWindow(self.hwnd)

    def unregister_hotkeys(self):
        for id in self.hotkey_ids.keys():
            try:
                win32gui.UnregisterHotKey(self.hwnd, id)
            except Exception:
                pass
        self.hotkey_ids.clear()

    def stop(self):
        self.running = False
        # Вызов PostQuitMessage, чтобы GetMessage вернулся и поток завершился
        win32gui.PostQuitMessage(0)
        self.wait()  # ждём полного завершения потока


class HotkeyManager:
    def __init__(self, player, cfg_path=hotkey_file):
        self.player = player
        self.cfg_path = cfg_path
        self.hotkeys = self.load_hotkeys()
        self.defaul_hotkeys = {
            "play_pause": "media_play_pause",
            "next_track": "media_next",
            "prev_track": "media_previous",
            "stop": "media_stop",
            "volume_up": "page_up",
            "volume_down": "page_down",
            "full_screen": "f11"
        }
        self.listener_thread = HotkeyListenerThread(self.hotkeys)
        self.listener_thread.hotkeyPressed.connect(self.execute_action)
        self.listener_thread.start()

    def load_hotkeys(self):
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self.defaul_hotkeys.copy()

    def save_hotkeys(self):
        os.makedirs(os.path.dirname(self.cfg_path), exist_ok=True)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.hotkeys, f, ensure_ascii=False, indent=4)

    def restart_listener(self):
        if self.listener_thread:
            self.listener_thread.stop()
        self.listener_thread = HotkeyListenerThread(self.hotkeys)
        self.listener_thread.hotkeyPressed.connect(self.execute_action)
        self.listener_thread.start()

    def open_settings_window(self):
        class SettingsWindow(QWidget):
            def __init__(self, manager):
                super().__init__(parent=None)
                self.manager = manager
                parent_widget = self.manager.player.ui
                if parent_widget:
                    self.setStyleSheet(parent_widget.styleSheet())
                self.setWindowTitle("Настройка горячих клавиш")
                self.layout = QVBoxLayout()
                self.inputs = {}
                self.listener = None
                self.current_input = None

                for action, key in self.manager.hotkeys.items():
                    hbox = QHBoxLayout()
                    label = QLabel(action)
                    line_edit = QLineEdit()
                    line_edit.setText(key)
                    line_edit.setReadOnly(True)
                    line_edit.setPlaceholderText("Нажмите для ввода")
                    line_edit.installEventFilter(self)
                    self.inputs[action] = line_edit
                    hbox.addWidget(label)
                    hbox.addWidget(line_edit)
                    self.layout.addLayout(hbox)

                btn_layout = QHBoxLayout()

                save_btn = QPushButton("Сохранить")
                save_btn.clicked.connect(self.save)
                btn_layout.addWidget(save_btn)

                reset_btn = QPushButton("Сбросить по умолчанию")
                reset_btn.clicked.connect(self.reset_defaults)
                btn_layout.addWidget(reset_btn)

                self.layout.addLayout(btn_layout)
                self.setLayout(self.layout)

            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseButtonPress and obj in self.inputs.values():
                    self.current_input = obj
                    obj.clear()
                    obj.setPlaceholderText("Ожидание нажатия клавиши...")
                    obj.setStyleSheet("color: gray;")
                    self.disable_inputs(except_this=obj)
                    self.start_listening()
                return super().eventFilter(obj, event)

            def disable_inputs(self, except_this=None):
                for input_field in self.inputs.values():
                    input_field.setEnabled(input_field is except_this)

            def enable_all_inputs(self):
                for input_field in self.inputs.values():
                    input_field.setEnabled(True)
                    input_field.setStyleSheet("")

            def start_listening(self):
                def on_press(key):
                    try:
                        name = key.char if hasattr(key, 'char') and key.char else str(key).replace("Key.", "")
                        if name:
                            self.current_input.setText(name)
                    except Exception as e:
                        self.current_input.setText("Ошибка")
                        print(f"Ошибка при обработке клавиши: {e}")
                    finally:
                        self.stop_listening()
                        self.enable_all_inputs()
                    return False

                self.listener = pkb.Listener(on_press=on_press)
                self.listener.start()

            def stop_listening(self):
                if self.listener:
                    self.listener.stop()
                    self.listener = None

            def save(self):
                for action, input_field in self.inputs.items():
                    new_key = input_field.text().strip()
                    if new_key:
                        self.manager.hotkeys[action] = new_key
                        self.manager.hk_names[action] = new_key.lower()
                self.manager.save_hotkeys()
                self.manager.restart_listener()
                QMessageBox.information(self, "Успех", "Настройки сохранены")

            def reset_defaults(self):
                msg = QMessageBox(self)
                msg.setWindowTitle("Подтверждение")
                msg.setText("Вы уверены, что хотите сбросить настройки?")
                yes_btn = msg.addButton("Да", QMessageBox.YesRole)
                no_btn = msg.addButton("Нет", QMessageBox.NoRole)
                msg.setIcon(QMessageBox.Question)
                msg.exec_()

                if msg.clickedButton() == yes_btn:
                    default_hotkeys = self.manager.defaul_hotkeys
                    self.manager.hotkeys = default_hotkeys
                    self.manager.hk_names = {a: k.lower() for a, k in default_hotkeys.items()}
                    for action, input_field in self.inputs.items():
                        input_field.setText(default_hotkeys.get(action, ""))
                    self.manager.save_hotkeys()
                    self.manager.restart_listener()
                    QMessageBox.information(self, "Сброс", "Горячие клавиши сброшены по умолчанию")

        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def execute_action(self, action):
        if action == "play_pause":
            self.player.ui.play_pause_button.click()
        elif action == "next_track":
            self.player.ui.next_button.click()
        elif action == "prev_track":
            self.player.ui.prev_button.click()
        elif action == "stop":
            self.player.ui.stop_button.click()
        elif action == "volume_up":
            self.player.increase_volume()
        elif action == "volume_down":
            self.player.decrease_volume()
        elif action == "full_screen":
            self.player.click_full_screen()

    def stop(self):
        if self.listener_thread:
            self.listener_thread.stop()
