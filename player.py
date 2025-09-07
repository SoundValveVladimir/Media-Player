import os
import sys
import time
import json
import socket
import atexit
import traceback
import datetime
import threading
from PyQt5.QtWidgets import QApplication
from default_styles import default_stylesheet

SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 54321


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

config_path = resource_path('Data\\config.json')

LOCK_FILE = os.path.expanduser(resource_path("sv.lock"))

def load_settings():
    if not os.path.exists(config_path):
        save_settings('basic')
    with open(config_path, 'r') as f:
        settings = json.load(f)
    return settings.get('mode', 'basic')

def save_settings(mode):
    with open(config_path, 'w') as f:
        json.dump({'mode': mode}, f)

def prepare_command_line_tracks(raw_args):
    if not raw_args:
        return None

    if raw_args[0] == '--filelist':
        if len(raw_args) == 2 and os.path.isfile(raw_args[1]):
            filelist_path = raw_args[1]
            try:
                with open(filelist_path, 'r', encoding='utf-8') as f:
                    tracks = [line.strip() for line in f if line.strip()]
                return tracks
            except Exception as e:
                print(f"Ошибка чтения списка треков из файла {filelist_path}:", e)
                return None
        else:
            tracks = raw_args[1:]
            return tracks if tracks else None

    if len(raw_args) == 1:
        path = raw_args[0]
        if os.path.isdir(path):
            return path
        return [path]

    return raw_args

def try_send_to_running_instance(args):
    """Пытаемся подключиться к уже запущенному экземпляру."""
    if not args:
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SOCKET_HOST, SOCKET_PORT))
        s.sendall(json.dumps(args).encode('utf-8'))
        s.close()
        return True
    except Exception:
        return False

def wait_for_server_ready(timeout=3):
    """Ждём, пока появится сервер."""
    start = time.time()
    while time.time() - start < timeout:
        if try_send_to_running_instance(command_line_tracks):
            print("Отправили аргументы работающему экземпляру (после ожидания).")
            sys.exit(0)
        time.sleep(0.1)

def listen_for_commands(player):
    """Слушаем команды от новых экземпляров."""
    def server():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((SOCKET_HOST, SOCKET_PORT))
        s.listen(5)
        while True:
            conn, _ = s.accept()
            data = conn.recv(4096)
            if not data:
                conn.close()
                continue
            try:
                tracks = json.loads(data.decode('utf-8'))
                print("Получены новые треки:", tracks)
                player.add_tracks(tracks)
            except Exception as e:
                print("Ошибка обработки команды:", e)
            conn.close()

    threading.Thread(target=server, daemon=True).start()

def load_stylesheet(self):
        try:
           if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
           else:
                base_path = os.path.dirname(__file__)
           qss_file_path = os.path.join(base_path, 'Data', 'style_white_blue.qss')
           with open(qss_file_path, 'r', encoding='utf-8') as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            print(f"Файл {qss_file_path} не найден!")
            self.setStyleSheet(default_stylesheet)
        except Exception as e:
            print(f"Ошибка при загрузке стилей: {e}")

if __name__ == "__main__":
    raw_args = sys.argv[1:]
    command_line_tracks = prepare_command_line_tracks(raw_args)

    first_instance = False
    if not os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "w") as f:
                f.write("lock")
            first_instance = True
        except Exception:
            pass

    if not first_instance:
        print("Другой экземпляр запускается, ждём...")
        wait_for_server_ready()
    
    if try_send_to_running_instance(command_line_tracks):
        print("Отправили аргументы работающему экземпляру. Завершаемся.")
        sys.exit(0)

    def silent_exit():
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
    
    def suppress_final_exceptions(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, TypeError) and 'NoneType' in str(exc_value):
            print("[INFO] Игнорируем ошибку завершения:", exc_value)
            return
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def suppress_exit_warnings():
        sys.stderr = open(os.devnull, 'w')

    def dummy_del(self):
        pass

    try:
        threading._DummyThread.__del__ = dummy_del
    except Exception:
        pass

    atexit.register(suppress_exit_warnings)
    sys.excepthook = suppress_final_exceptions
    atexit.register(silent_exit)

    app = QApplication(sys.argv)

    load_stylesheet(app)

    from PyQt5.QtGui import QIcon
    app.setWindowIcon(QIcon(resource_path('Data\\Icon\\Logo.ico')))

    def remove_lock():
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    atexit.register(remove_lock)

    log_path = os.path.expanduser(resource_path("sv_args.log")).replace("/", "\\")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} ARGS = {sys.argv!r}\n")

    mode = load_settings()

    if mode == 'basic':
        from basic_player import BasicPlayer
        player = BasicPlayer(command_line_tracks)
    else:
        from advanced_player import AdvancedPlayer
        player = AdvancedPlayer()

    listen_for_commands(player)

    player.ui.show()
    sys.exit(app.exec_())
