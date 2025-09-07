import os
import sys
from PyQt5.QtGui import QIcon, QPixmap

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    full_path = os.path.join(base_path, relative_path.replace("/", os.sep).replace("\\", os.sep))
    if not os.path.exists(full_path):
        print(f"Error: {full_path} does not exist!")
    return full_path

class IconPath:
    PREV = None
    PLAY = None
    PAUSE = None
    STOP = None
    NEXT = None
    BROWSE = None
    MUTE = None
    REPEAT = None
    SHUFFLE = None
    SEQUENTIAL = None
    CLEAR = None
    SEARCH = None
    FULLSCREEN = None
    NORMAL_SCREEN = None
    VOL_1 = None
    VOL_2 = None
    VOL_3 = None
    VOL_4 = None
    LOGO = None
    LOG = None
    MINIMIZE = None
    MAXIMIZE = None
    CLOSE = None
    RESTORE = None
    WAVE = None

    @classmethod
    def load_icons(cls):
        cls.PREV = QIcon(resource_path("Data\\Icon\\Blue\\prev_img2.png"))
        cls.PLAY = QIcon(resource_path("Data\\Icon\\Blue\\play_img2.png"))
        cls.PAUSE = QIcon(resource_path("Data\\Icon\\Blue\\pause_img2.png"))
        cls.STOP = QIcon(resource_path("Data\\Icon\\Blue\\stop_img2.png"))
        cls.NEXT = QIcon(resource_path("Data\\Icon\\Blue\\next_img2.png"))
        cls.BROWSE = QIcon(resource_path("Data\\Icon\\Blue\\media_img3.png"))
        cls.MUTE = QIcon(resource_path("Data\\Icon\\Blue\\sound1_2.png"))
        cls.REPEAT = QIcon(resource_path("Data\\Icon\\Blue\\repeat_one.png"))
        cls.SHUFFLE = QIcon(resource_path("Data\\Icon\\Blue\\shuffle2.png"))
        cls.SEQUENTIAL = QIcon(resource_path("Data\\Icon\\Blue\\repeat_all.png"))
        cls.CLEAR = QIcon(resource_path("Data\\Icon\\Blue\\clear4.png"))
        cls.SEARCH = QIcon(resource_path("Data\\Icon\\Blue\\search4.png"))
        cls.FULLSCREEN = QIcon(resource_path("Data\\Icon\\Blue\\Full_s.png"))
        cls.NORMAL_SCREEN = QIcon(resource_path("Data\\Icon\\Blue\\Normal_s.png"))
        cls.VOL_1 = QIcon(resource_path("Data\\Icon\\Blue\\sound1_1.png"))
        cls.VOL_2 = QIcon(resource_path("Data\\Icon\\Blue\\sound1_2.png"))
        cls.VOL_3 = QIcon(resource_path("Data\\Icon\\Blue\\sound1_3.png"))
        cls.VOL_4 = QIcon(resource_path("Data\\Icon\\Blue\\sound1_4.png"))
        cls.LOGO = QIcon(resource_path("Data\\Icon\\Blue\\logo.ico"))
        cls.LOG = QIcon(resource_path("Data\\Icon\\Blue\\log.png"))
        cls.MINIMIZE = QIcon(resource_path("Data\\Icon\\Blue\\minimize4.png"))
        cls.MAXIMIZE = QIcon(resource_path("Data\\Icon\\Blue\\maximize4.png"))
        cls.CLOSE = QIcon(resource_path("Data\\Icon\\Blue\\close4.png"))
        cls.RESTORE = QIcon(resource_path("Data\\Icon\\Blue\\restore4.png"))
        cls.WAVE = QPixmap(resource_path("Data\\Icon\\Other\\wave.png"))