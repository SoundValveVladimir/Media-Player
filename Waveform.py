import os
import subprocess
import numpy as np
import pyaudio
import colorsys
from PyQt5.QtCore import QFileSystemWatcher, QTimer, Qt, QRectF
from PyQt5.QtWidgets import QOpenGLWidget, QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QLinearGradient, QFont, QSurfaceFormat
from math import sin, cos, pi
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import gluOrtho2D

current_time_wave = None

def time_wave(_time=None):
    global current_time_wave
    if _time is not None:
        current_time_wave = int(_time)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    full_path = f"{base_path}\\{relative_path}"
    return full_path

# class FFmpegAudioAnalyzer:
#     def __init__(self, ffmpeg_path=resource_path("Data\\ffmpeg\\bin\\ffmpeg.exe"), sample_rate=44100):
#         self.ffmpeg_path = ffmpeg_path
#         self.sample_rate = sample_rate
#         self.samples_per_second = 1000
#         self.data = {}  # {секунда: [амплитуды]}
#         self.samples = np.array([], dtype=np.float32)  # ⬅️ Новый массив сэмплов
#         self.duration = 0

#     def load_and_analyze(self, file_path):
#         print(f"[INFO] Начинаю анализ: {file_path}")
#         self.data.clear()
#         self.samples = np.array([], dtype=np.float32)
#         self.duration = self.get_duration(file_path)
#         if self.duration == 0:
#             print("[ERROR] Не удалось получить продолжительность трека.")
#             return
#         cmd = [
#             self.ffmpeg_path,
#             "-i", file_path,
#             "-f", "f32le",
#             "-ac", "1",
#             "-ar", str(self.sample_rate),
#             "-"
#         ]
#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
#         raw_audio = process.stdout.read()
#         self.samples = np.frombuffer(raw_audio, dtype=np.float32)
#         total_seconds = int(len(self.samples) / self.sample_rate)
#         self.duration = total_seconds
#         for sec in range(total_seconds):
#             start = sec * self.sample_rate
#             end = start + self.sample_rate
#             chunk = self.samples[start:end]
#             if len(chunk) < self.sample_rate:
#                 chunk = np.pad(chunk, (0, self.sample_rate - len(chunk)), 'constant')
#             ms_chunks = np.array_split(chunk, self.samples_per_second)
#             amplitudes = [float(np.abs(c).mean()) for c in ms_chunks]
#             self.data[sec] = amplitudes
#         print(f"[INFO] Анализ завершен. Секунд: {len(self.data)}")

#     def get_duration(self, file_path):
#         cmd = [
#             os.path.join(os.path.dirname(self.ffmpeg_path), "ffprobe.exe"),
#             "-v", "error",
#             "-show_entries", "format=duration",
#             "-of", "default=noprint_wrappers=1:nokey=1",
#             file_path
#         ]
#         try:
#             output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
#             return int(float(output))
#         except Exception as e:
#             print(f"[FFPROBE ERROR] {e}")
#             return 0

#     def get_amplitude(self, milliseconds):
#         sec = int(milliseconds / 1000)
#         ms = int(milliseconds % 1000)
#         if sec in self.data and ms < len(self.data[sec]):
#             print(self.data[sec][ms])
#             return self.data[sec][ms]
#         return 0.0

#     def get_samples_for_time(self, milliseconds, width):
#         # Возвращает отрезок сэмплов нужной ширины (для визуализации на экране)
#         pos = int(milliseconds * self.sample_rate / 1000)
#         half_width = width // 2
#         start = max(0, pos - half_width)
#         end = min(len(self.samples), pos + half_width)
#         result = self.samples[start:end]
#         if len(result) < width:
#             result = np.pad(result, (0, width - len(result)), 'constant')
#         return result


# class AudioAnalyzerManager:
#     def __init__(self, audio_analyzer):
#         self.file_path = None
#         self.watcher = QFileSystemWatcher()
#         self.file_checker_timer = QTimer()
#         self.file_checker_timer.setInterval(1000)
#         self.file_checker_timer.timeout.connect(self.check_file_exists)
#         self.audio_analyzer = audio_analyzer
#         self.watcher.fileChanged.connect(self.on_file_changed)

#     def set_audio_file(self, new_path):
#         print(new_path)
#         if self.file_checker_timer.isActive():
#             self.file_checker_timer.stop()
#         if self.file_path and self.file_path in self.watcher.files():
#             self.watcher.removePath(self.file_path)
#         self.file_path = new_path
#         if not os.path.exists(new_path):
#             self.wait_for_file()
#         else:
#             self.watcher.addPath(new_path)
#             self.analyze_audio(new_path)

#     def wait_for_file(self):
#         self.file_checker_timer.start()

#     def check_file_exists(self):
#         if os.path.exists(self.file_path):
#             self.file_checker_timer.stop()
#             self.watcher.addPath(self.file_path)
#             self.analyze_audio(self.file_path)

#     def analyze_audio(self, path):
#         print(f"[INFO] Анализируем файл: {path}")
#         self.audio_analyzer.load_and_analyze(path)

#     def on_file_changed(self, path):
#         print(f"[INFO] Файл изменён: {path}")
#         self.analyze_audio(path)


class AudioManager:
    _instances = {}
    def __new__(cls, profile_id=0):
        if profile_id not in cls._instances:
            instance = super(AudioManager, cls).__new__(cls)
            instance.profile_id = profile_id
            instance.sample_rate = 44100
            if profile_id == 0:
                instance.frames_per_buffer = 1024
                instance.channels = 2
                instance.mode = 'raw'
            elif profile_id == 1:
                instance.frames_per_buffer = 1024
                instance.channels = 1
                instance.mode = 'raw'
            elif profile_id == 2:
                instance.frames_per_buffer = 512
                instance.channels = 2
                instance.mode = 'fft_abs'
            elif profile_id == 3:
                instance.frames_per_buffer = 2048
                instance.channels = 2
                instance.mode = 'fft_window'
            else:
                raise ValueError(f"Неизвестный профиль AudioManager: {profile_id}")

            instance.samples = np.zeros(instance.frames_per_buffer, dtype=np.float32)
            instance.pa = None
            instance.stream = None
            instance.setup_audio()
            cls._instances[profile_id] = instance
        return cls._instances[profile_id]

    def setup_audio(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.frames_per_buffer,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def audio_callback(self, in_data, frame_count, time_info, status):
        try:
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            if self.mode == 'raw':
                self.samples = audio_data
            elif self.mode == 'fft_abs':
                self.samples = np.abs(np.fft.rfft(audio_data))
            elif self.mode == 'fft_window':
                window = np.hanning(len(audio_data))
                fft_result = np.fft.rfft(audio_data * window)
                self.samples = np.abs(fft_result)
            else:
                self.samples = audio_data  # fallback
        except Exception as e:
            print(f"[Audio callback error]: {e}")
        return (in_data, pyaudio.paContinue)

    def get_samples(self):
        return np.array(self.samples, dtype=np.float32)

    def get_frequency_data(self):
        if len(self.samples) == 0:
            return np.zeros(self.frames_per_buffer // 2 + 1)

        # Окно Хэннинга для устранения резких краёв
        window = np.hanning(len(self.samples))
        windowed_samples = self.samples * window

        # Быстрое преобразование Фурье
        fft_result = np.fft.rfft(windowed_samples)

        # Модуль (амплитуда спектра)
        magnitude = np.abs(fft_result)

        # Логарифмическое усиление — чтобы низкие амплитуды были видны
        magnitude = np.log1p(magnitude)  # log(1 + x)

        # Нормализация
        magnitude /= np.max(magnitude) + 1e-6  # чтобы не делить на 0

        # Масштабирование до 0-100 для визуализации
        return magnitude * 100.0

    def get_bass_amplitude(self):
        freq_data = self.get_frequency_data()
        freqs = np.fft.rfftfreq(len(self.samples), d=1.0 / self.sample_rate)
        bass_mask = (freqs >= 20) & (freqs <= 200)
        if np.any(bass_mask):
            return np.mean(freq_data[bass_mask])
        return 0.0

    def close(self):
        if hasattr(self, "stream") and self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if hasattr(self, "pa"):
            self.pa.terminate()
            self.pa = None


class AudioManager_1:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager_1, cls).__new__(cls)
            cls._instance.samples = np.zeros(256, dtype=np.float32)
            cls._instance.stream = None
            cls._instance.setup_audio()
        return cls._instance
        
    def setup_audio(self):
        p = pyaudio.PyAudio()
        self.stream = p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.samples = np.frombuffer(in_data, dtype=np.float32)
        return (in_data, pyaudio.paContinue)
        
    def get_samples(self):
        return self.samples
        
    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

class AudioManager_2:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager_2, cls).__new__(cls)
            cls._instance.samples = np.zeros(256, dtype=np.float32)
            cls._instance.stream = None
            cls._instance.setup_audio()
        return cls._instance
        
    def setup_audio(self):
        p = pyaudio.PyAudio()
        self.stream = p.open(
            format=pyaudio.paFloat32,
            channels=2,
            rate=44100,
            input=True,
            frames_per_buffer=512,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def audio_callback(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        self.samples = np.abs(np.fft.rfft(audio_data))
        return (in_data, pyaudio.paContinue)
        
    def get_samples(self):
        return self.samples
        
    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

class AudioManager_3:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager_3, cls).__new__(cls)
            cls._instance.sample_rate = 44100
            cls._instance.frames_per_buffer = 2048
            cls._instance.samples = np.zeros(cls._instance.frames_per_buffer, dtype=np.float32)
            cls._instance.setup_audio()
        return cls._instance

    def setup_audio(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=2,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.frames_per_buffer,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.samples = np.frombuffer(in_data, dtype=np.float32)
        return (in_data, pyaudio.paContinue)

    def get_samples(self):
        return self.samples

    def get_frequency_data(self):
        if len(self.samples) == 0:
            return np.zeros(self.frames_per_buffer//2 + 1)
        window = np.hanning(len(self.samples))
        fft_result = np.fft.rfft(self.samples * window)
        magnitude = np.abs(fft_result)
        return magnitude

    def get_bass_amplitude(self):
        freq_data = self.get_frequency_data()
        freqs = np.fft.rfftfreq(len(self.samples), d=1.0 / self.sample_rate)
        bass_mask = (freqs >= 20) & (freqs <= 200)
        if np.any(bass_mask):
            return np.mean(freq_data[bass_mask])
        return 0.0

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()

class SoundRef(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.phase = 0.0
        self.height_scale = 1.0
        self.wave_scale = 1.0
        self.step_divider = 200
        self.line_width_base = 2.0
        self.colors = [
            (0.0, 0.3, 0.9, 1.0),
            (0.0, 0.5, 1.0, 0.8),
            (0.2, 0.6, 1.0, 0.6),
            (0.0, 0.2, 0.8, 0.7)
        ]
        self.timer = self.startTimer(33) if self.run else None
        self.prev_hash = None

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32/255.0, 35/255.0, 42/255.0, 1.0)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.height_scale = height / 800.0
        wave_height = max(40, height / 2)
        if height <= 100:
            wave_height = 40
            self.wave_scale = 0.3
            self.step_divider = 100
            self.line_width_base = 1.0
        else:
            self.wave_scale = min(1.0, self.height_scale)
            self.step_divider = 200
            self.line_width_base = min(3.0, 1.0 + self.height_scale)
        glOrtho(-width / 2, width / 2, -wave_height, wave_height, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def draw_wave_layer_fast(self, scale, color, phase_offset=0):
        width = self.width()
        samples = self.audio_manager.get_samples()
        if not samples.any():
            return
        samples_hash = hash(samples.tobytes())
        if samples_hash != self.prev_hash:
            self.cached_samples = samples
            self.prev_hash = samples_hash

        step = max(2, width // self.step_divider)
        x_vals = np.arange(-width // 2, width // 2, step)
        idx = ((x_vals + width // 2) * len(samples)) // width
        idx = np.clip(idx, 0, len(samples) - 1)
        y_vals = self.cached_samples[idx]

        wave_intensity = 0.3 * self.wave_scale
        current_scale = scale * self.wave_scale
        mod = (
            wave_intensity * np.sin(self.phase + phase_offset + x_vals * 0.005) +
            (wave_intensity * 0.6) * np.sin(self.phase * 1.5 + x_vals * 0.01)
        )
        y = (y_vals + mod) * current_scale

        glColor4fv(color)
        glBegin(GL_LINE_STRIP)
        for x, y_ in zip(x_vals, y):
            glVertex2f(x, y_)
        glEnd()

    def draw_symmetric_waves(self):
        glLineWidth(self.line_width_base)
        self.draw_wave_layer_fast(150, self.colors[0])
        for i in range(3):
            scale = 120 - i * 20
            phase = i * np.pi / 4
            glLineWidth(max(1.0, self.line_width_base * 0.7))
            self.draw_wave_layer_fast(scale, self.colors[i+1], phase)
            self.draw_wave_layer_fast(-scale, self.colors[i+1], -phase)

    def draw_glow_effect(self):
        glLineWidth(max(1.0, self.line_width_base * 1.2))
        for i in range(2):
            color = list(self.colors[0])
            color[3] = 0.1 - i * 0.03
            scale = 160 + i * 10
            self.draw_wave_layer_fast(scale, color)
            self.draw_wave_layer_fast(-scale, color)

    def paintGL(self):
        if not self.run:
            return
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        self.draw_glow_effect()
        self.draw_symmetric_waves()
        self.phase += 0.05
        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()

class SoundVeins(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.audio_manager = audio_manager
        self.run = run
        self.breath_phase = 0.0
        self.num_lines = 480  # В 4 раза меньше линий
        self.prev_values = np.zeros(self.num_lines, dtype=np.float32)
        if self.run:
            QTimer(self, interval=16, timeout=self.update).start()

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32 / 255, 35 / 255, 42 / 255, 1.0)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not self.run:
            return
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        width, height = self.width(), self.height()
        samples = self.audio_manager.get_samples()
        if len(samples) < 2:
            return

        step = len(samples) / self.num_lines
        max_height = height * 0.6
        breath = 1 + 0.03 * np.sin(self.breath_phase)
        edge_fade_max = (self.num_lines // 2) * 0.8
        base_color = self.hsv_to_rgb((0.5 + 0.1 * np.sin(self.breath_phase)) % 1.0, 0.7, 1.0)

        glColor4f(*base_color, 0.7)
        glLineWidth(1.5)
        glBegin(GL_LINES)

        for i in range(self.num_lines):
            x = i * width / self.num_lines
            idx = i * step
            i0 = int(idx)
            i1 = min(i0 + 1, len(samples) - 1)
            frac = idx - i0
            val = (1 - frac) * samples[i0] + frac * samples[i1]

            self.prev_values[i] = 0.9 * self.prev_values[i] + 0.1 * val
            val = self.prev_values[i]
            if abs(val) < 0.004:
                continue

            norm = min(abs(val), 1.0)
            dyn_height = max_height * norm * breath
            dyn_height *= 1 - min(i, self.num_lines - i) / edge_fade_max

            cy = height / 2
            glVertex2f(x, cy)
            glVertex2f(x, cy - dyn_height)
            glVertex2f(x, cy)
            glVertex2f(x, cy + dyn_height)

        glEnd()
        self.breath_phase += 0.01
        glFlush()

    def hsv_to_rgb(self, h, s, v):
        i = int(h * 6)
        f = h * 6 - i
        i %= 6
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        return [
            (v, t, p),
            (q, v, p),
            (p, v, t),
            (p, q, v),
            (t, p, v),
            (v, p, q),
        ][i]


class SoundColorRef(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.phase = 0.0
        self.last_hash = None

        self.colors = [
            (1.0, 0.0, 0.0, 0.8),  # Красный
            (1.0, 0.5, 0.0, 0.8),  # Оранжевый
            (1.0, 1.0, 0.0, 0.8),  # Жёлтый
            (0.0, 1.0, 0.0, 0.8),  # Зелёный
            (0.0, 0.5, 1.0, 0.8),  # Голубой
            (0.0, 0.0, 1.0, 0.8),  # Синий
            (0.5, 0.0, 1.0, 0.8)   # Фиолетовый
        ]

        self.wave_scale = 1.0
        self.line_width_base = 2.0
        self.height_scale = 1.0
        self.step_divider = 200

        if self.run:
            self.timer = QTimer()
            self.timer.timeout.connect(self._maybe_update)
            self.timer.start(33)  # 30 FPS

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.height_scale = height / 800.0
        self.wave_scale = min(1.0, self.height_scale)
        self.step_divider = 200 if height > 100 else 100
        self.line_width_base = min(3.0, 1.0 + self.height_scale)
        wave_height = max(40, height / 2)
        glOrtho(-width/2, width/2, -wave_height, wave_height, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def _maybe_update(self):
        samples = self.audio_manager.get_samples()
        sample_hash = hash(samples.tobytes())
        if sample_hash != self.last_hash:
            self.last_hash = sample_hash
            self.update()

    def draw_wave_layer(self, samples, scale, color, phase_offset=0, freq_mod=1.0):
        width = self.width()
        step = max(2, width // self.step_divider)
        glColor4fv(color)
        glBegin(GL_LINE_STRIP)

        x_vals = np.arange(-width//2, width//2, step)
        norm_idx = ((x_vals + width//2) * len(samples) // width).clip(0, len(samples)-1)
        values = samples[norm_idx]

        # Массив фаз — один раз
        phase_arr = (
            0.3 * self.wave_scale * np.sin(self.phase * freq_mod + phase_offset + x_vals * 0.005) +
            0.18 * self.wave_scale * np.sin(self.phase * freq_mod * 1.5 + x_vals * 0.01) +
            0.09 * self.wave_scale * np.sin(self.phase * freq_mod * 0.7 + x_vals * 0.02)
        )

        y_vals = (values + phase_arr) * scale * self.wave_scale

        for x, y in zip(x_vals, y_vals):
            glVertex2f(x, y)

        glEnd()

    def draw_rainbow_waves(self, samples):
        num_colors = len(self.colors)
        for i, color in enumerate(self.colors):
            scale = 100 + i * 15
            phase = (i * np.pi / num_colors) * 2
            freq_mod = 0.8 + i * 0.2
            glLineWidth(max(1.0, self.line_width_base * 0.8))
            self.draw_wave_layer(samples, scale, color, phase, freq_mod)
            self.draw_wave_layer(samples, -scale * 0.7, color, -phase, freq_mod * 1.2)

    def paintGL(self):
        if not self.run:
            return

        samples = self.audio_manager.get_samples()
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        for i in range(2):
            glLineWidth(self.line_width_base * (1.5 - i * 0.3))
            for color in self.colors:
                glow_color = list(color)
                glow_color[3] = 0.15 - i * 0.05
                self.draw_wave_layer(samples, 120 + i * 20, glow_color, i * np.pi / 4)

        self.draw_rainbow_waves(samples)
        self.phase += 0.03
        glFlush()

class SoundEchoGlow(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.phase = 0.0
        self.height_scale = 1.0
        self.wave_scale = 1.0
        self.step_divider = 200
        self.line_width_base = 2.0
        self.colors = [
            (1.0, 0.2, 0.2, 0.8),  # Красный
            (1.0, 0.6, 0.1, 0.8),  # Оранжевый
            (0.2, 0.7, 1.0, 0.8),  # Голубой
            (0.0, 0.5, 1.0, 0.8),  # Электрик синий
        ]
        self.timer = self.startTimer(33) if self.run else None

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.height_scale = height / 800.0
        wave_height = max(40, height / 2)

        if height <= 100:
            wave_height = 40
            self.wave_scale = 0.3
            self.step_divider = 100
            self.line_width_base = 1.0
        else:
            self.wave_scale = min(1.0, self.height_scale)
            self.step_divider = 200
            self.line_width_base = min(3.0, 1.0 + self.height_scale)

        glOrtho(-width / 2, width / 2, -wave_height, wave_height, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def draw_filled_wave(self, scale, color, phase_offset=0.0, freq_mod=1.0):
        width = self.width()
        samples = self.audio_manager.get_samples()
        sample_len = len(samples)
        step = max(2, width // self.step_divider)
        x_vals = np.arange(-width // 2, width // 2, step)

        # Предвычисления
        wave_intensity = 0.3 * self.wave_scale
        current_scale = scale * self.wave_scale
        rotation_speed = 2.0
        rotation = np.sin(self.phase * rotation_speed + phase_offset) * 0.5

        y_vals = np.zeros_like(x_vals, dtype=np.float32)

        for i, x in enumerate(x_vals):
            sample_idx = ((x + width // 2) * sample_len) // width
            sample_idx = min(sample_len - 1, sample_idx)
            value = samples[sample_idx]
            # modulation = (
            #     wave_intensity * np.sin(self.phase * freq_mod + x * 0.002) +
            #     (wave_intensity * 0.6) * np.sin(self.phase * freq_mod * 1.5 + x * 0.004)
            # )
            modulation = (
                wave_intensity * np.sin(self.phase * freq_mod + x * 0.005) +
                (wave_intensity * 0.6) * np.sin(self.phase * freq_mod * 1.5 + x * 0.01)
            )
            y = (value + modulation) * current_scale
            y_vals[i] = y * (1.0 + rotation * np.cos(x * 0.01))

        # Рисуем заливку
        fill_color = list(color)
        fill_color[3] = 0.2

        glBegin(GL_QUAD_STRIP)
        for x, y in zip(x_vals, y_vals):
            glColor4f(0, 0, 0, 0)
            glVertex2f(x, 0)
            glColor4fv(fill_color)
            glVertex2f(x, y)
        glEnd()

        # Рисуем линию
        glColor4fv(color)
        glBegin(GL_LINE_STRIP)
        for x, y in zip(x_vals, y_vals):
            glVertex2f(x, y)
        glEnd()

    def draw_waves(self):
        for i, color in enumerate(self.colors):
            scale = 80 + i * 20
            phase = i * np.pi / 3
            freq_mod = 1.0 + i * 0.2
            self.draw_filled_wave(scale, color, phase, freq_mod)

    def paintGL(self):
        if not self.run:
            return
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        self.draw_waves()
        self.phase += 0.03
        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()


class SoundBlueEchoes(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.phase = 0.0
        self.colors = [
            (0.0, 0.3, 0.9, 1.0),
            (0.0, 0.5, 1.0, 0.8),
            (0.2, 0.6, 1.0, 0.6),
            (0.0, 0.2, 0.8, 0.7)
        ]
        self.timer = self.startTimer(33) if self.run else None  # 30 FPS вместо 60

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-width/2, width/2, -height/2, height/2, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def draw_wave_layer(self, samples, scale, color, phase_offset=0, step=6):
        glBegin(GL_LINE_STRIP)
        glColor4fv(color)
        width = self.width()
        for x in range(-width//2, width//2, step):
            idx = int(((x + width//2) * len(samples)) / width)
            idx = min(idx, len(samples) - 1)
            value = samples[idx]
            modulation = (
                0.3 * np.sin(self.phase + phase_offset + x * 0.005) +
                0.2 * np.sin(self.phase * 1.5 + x * 0.01) +
                0.1 * np.sin(self.phase * 0.7 - x * 0.008))
            y = (value + modulation) * scale
            glVertex2f(x, y)
        glEnd()

    def draw_symmetric_waves(self, samples):
        glLineWidth(2.0)
        self.draw_wave_layer(samples, 140, self.colors[0], 0)
        for i in range(2):  # было 3 слоя — стало 2
            scale = 110 - i * 15
            phase = i * np.pi / 4
            self.draw_wave_layer(samples, scale, self.colors[i+1], phase)
            self.draw_wave_layer(samples, -scale, self.colors[i+1], -phase)

    def draw_glow_effect(self, samples):
        glDisable(GL_LINE_SMOOTH)  # Glow без сглаживания
        glLineWidth(3.0)
        for i in range(2):  # было 3 слоя — стало 2
            color = list(self.colors[0])
            color[3] = 0.08 - i * 0.02
            scale = 160 + i * 10
            self.draw_wave_layer(samples, scale, color)
            self.draw_wave_layer(samples, -scale, color)
        glEnable(GL_LINE_SMOOTH)

    def paintGL(self):
        if not self.run:
            return
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        samples = self.audio_manager.get_samples()
        if len(samples) == 0:
            return
        self.draw_glow_effect(samples)
        self.draw_symmetric_waves(samples)
        self.phase = (self.phase + 0.05) % (2 * np.pi)
        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()

class SoundRipple(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.bars = 128
        self.peak_levels = np.zeros(self.bars)
        self.decay_rate = 0.03
        self.smooth_data = np.zeros(self.bars)
        self.bar_width = 6
        self.timer = self.startTimer(33) if self.run else None  # ~30 FPS

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        self.bars = max(8, width // self.bar_width)
        self.peak_levels = np.zeros(self.bars)
        self.smooth_data = np.zeros(self.bars)

    def paintGL(self):
        if not self.run:
            return

        glClear(GL_COLOR_BUFFER_BIT)
        samples = self.audio_manager.get_samples()
        if np.max(np.abs(samples)) < 0.01:
            return

        bar_width = self.width() / self.bars
        max_height = self.height()

        interp_indices = np.linspace(0, len(samples), self.bars)
        freqs = np.interp(interp_indices, np.arange(len(samples)), samples)
        freqs = np.clip(freqs, 0, None)
        freqs = np.log1p(freqs * 10)

        max_val = np.max(freqs)
        if max_val > 0:
            freqs /= max_val

        glLoadIdentity()

        for i in range(self.bars):
            height = max_height * freqs[i]
            self.smooth_data[i] = self.smooth_data[i] * 0.8 + height * 0.2
            x = i * bar_width

            # Пиковая линия
            if self.smooth_data[i] > self.peak_levels[i]:
                self.peak_levels[i] = self.smooth_data[i]
            else:
                self.peak_levels[i] -= self.decay_rate * max_height
                self.peak_levels[i] = max(self.peak_levels[i], 0)

            # Цвет градиента — от голубого к синему
            r = 0.0
            g = 0.5 + 0.5 * freqs[i]
            b = 0.8 + 0.2 * freqs[i]
            glColor4f(r, g, b, 1.0)

            # Основной столбец
            glBegin(GL_QUADS)
            glVertex2f(x, 0)
            glVertex2f(x + bar_width * 0.8, 0)
            glVertex2f(x + bar_width * 0.8, self.smooth_data[i])
            glVertex2f(x, self.smooth_data[i])
            glEnd()

            # Линия пика
            peak_alpha = 0.6 if self.peak_levels[i] > 0 else 0.0
            glColor4f(1.0, 0.2, 0.2, peak_alpha)
            glBegin(GL_QUADS)
            glVertex2f(x, self.peak_levels[i] - 1)
            glVertex2f(x + bar_width * 0.8, self.peak_levels[i] - 1)
            glVertex2f(x + bar_width * 0.8, self.peak_levels[i] + 1)
            glVertex2f(x, self.peak_levels[i] + 1)
            glEnd()

        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()


class SoundDNK(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.timer = self.startTimer(33) if self.run else None

    def initializeGL(self):
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, 0, h, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not self.run:
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        width, height = self.width(), self.height()
        cx, cy = width / 2, height / 2
        radius_inner = min(width, height) * 0.2
        radius_outer = min(width, height) * 0.35

        samples = self.audio_manager.get_samples()
        if len(samples) == 0:
            return

        # Применим окно и FFT
        window = np.hanning(len(samples))
        fft = np.fft.rfft(samples * window)
        spectrum = np.abs(fft)

        # Разделим на два кольца
        bins = len(spectrum)
        num_lines = 180  # по 2 на каждый градус (внутр. + внеш.)
        low_bins = spectrum[:bins // 2]
        high_bins = spectrum[bins // 2:]

        # Нормализация
        def normalize(array):
            max_val = np.max(array) or 1.0
            return np.clip(array / max_val, 0.0, 1.0)

        low_norm = normalize(low_bins)
        high_norm = normalize(high_bins)

        # Рисуем внутреннее кольцо (низкие частоты)
        glBegin(GL_LINES)
        for i in range(num_lines):
            angle = 2 * pi * i / num_lines
            idx = int(i / num_lines * len(low_norm))
            amp = low_norm[idx]

            r1 = radius_inner
            r2 = r1 + amp * 50
            x1 = cx + r1 * cos(angle)
            y1 = cy + r1 * sin(angle)
            x2 = cx + r2 * cos(angle)
            y2 = cy + r2 * sin(angle)
            glColor4f(0.2, amp, 1.0 - amp, 0.8)
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)
        glEnd()

        # Рисуем внешнее кольцо (высокие частоты)
        glBegin(GL_LINES)
        for i in range(num_lines):
            angle = 2 * pi * i / num_lines
            idx = int(i / num_lines * len(high_norm))
            amp = high_norm[idx]

            r1 = radius_outer
            r2 = r1 + amp * 70
            x1 = cx + r1 * cos(angle)
            y1 = cy + r1 * sin(angle)
            x2 = cx + r2 * cos(angle)
            y2 = cy + r2 * sin(angle)
            glColor4f(1.0 - amp, 0.2 + 0.8 * amp, 0.1, 0.7)
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)
        glEnd()

        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()

class SoundSpectrumRing(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.bars = 360
        if self.run:
            self.timer = self.startTimer(16) if self.run else None  # ~30 FPS
        self.breath_phase = 0.0
        self.bass_phase = 0.0
        self.mid_phase = 0.0
        self.high_phase = 0.0
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def initializeGL(self):
        glClearColor(32 / 255, 35 / 255, 42 / 255, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, 0, h, -1, 1)
        glMatrixMode(GL_MODELVIEW)

    # def paintGL(self):
    #     if not self.run:
    #         return
    #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #     glLoadIdentity()
    #     samples = self.audio_manager.get_samples()
    #     if len(samples) == 0:
    #         return
    #     # Применяем окно и FFT
    #     window = np.hanning(len(samples))
    #     spectrum = np.abs(np.fft.rfft(samples * window))
    #     spectrum = spectrum[:self.bars]
    #     max_val = np.max(spectrum)
    #     if max_val < 1e-6:
    #         max_val = 1.0
    #     norm_spec = spectrum / max_val
    #     w, h = self.width(), self.height()
    #     cx, cy = w / 2, h / 2
    #     base_radius = min(w, h) * 0.1
    #     max_length = min(w, h) * 0.5
    #     glLineWidth(2.0)
    #     glBegin(GL_LINES)
    #     for i in range(self.bars):
    #         angle = 2 * pi * (i / self.bars)
    #         log_i = np.log10(1 + 9 * (i / self.bars))
    #         bin_idx = int(log_i * len(norm_spec))
    #         bin_idx = np.clip(bin_idx, 0, len(norm_spec) - 1)
    #         amp = norm_spec[bin_idx] ** 0.5
    #         low_boost = 1.0 - (i / self.bars)
    #         #amp *= 0.6 + 0.4 * low_boost
    #         length = base_radius + amp * max_length
    #         x1 = cx + cos(angle) * base_radius
    #         y1 = cy + sin(angle) * base_radius
    #         x2 = cx + cos(angle) * length
    #         y2 = cy + sin(angle) * length
    #         # Цвет по частоте
    #         hue = i / self.bars
    #         r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    #         glColor4f(r, g, b, 0.9)
    #         glVertex2f(x1, y1)
    #         glVertex2f(x2, y2)
    #     glEnd()
    #     glFlush()

    # def paintGL(self):
    #     if not self.run:
    #         return
    #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #     glLoadIdentity()
    #     samples = self.audio_manager.get_samples()
    #     if len(samples) == 0:
    #         return
    #     # FFT
    #     window = np.hanning(len(samples))
    #     spectrum = np.abs(np.fft.rfft(samples * window))
    #     spectrum = spectrum[:self.bars]
    #     max_val = np.max(spectrum)
    #     if max_val < 1e-6:
    #         max_val = 1.0
    #     norm_spec = spectrum / max_val
    #     norm_spec = norm_spec ** 0.6  # сглаживание пиков
    #     # Центр и параметры кольца
    #     w, h = self.width(), self.height()
    #     cx, cy = w / 2, h / 2
    #     base_radius = min(w, h) * 0.2
    #     wave_strength = min(w, h) * 0.2  # амплитуда волн
    #     glLineWidth(2.0)
    #     glBegin(GL_LINE_LOOP)  # соединяем все точки в кольцо
    #     for i in range(self.bars):
    #         angle = 2 * pi * (i / self.bars)
    #         # логарифмическое распределение спектра
    #         log_i = np.log10(1 + 9 * (i / self.bars))
    #         bin_idx = int(log_i * len(norm_spec))
    #         bin_idx = np.clip(bin_idx, 0, len(norm_spec) - 1)
    #         amp = norm_spec[bin_idx]
    #         radius = base_radius + amp * wave_strength
    #         x = cx + cos(angle) * radius
    #         y = cy + sin(angle) * radius
    #         # цвет по частоте
    #         hue = i / self.bars
    #         r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    #         glColor4f(r, g, b, 0.8)
    #         glVertex2f(x, y)
    #     glEnd()
    #     glFlush()

    # def paintGL(self):
    #     if not self.run:
    #         return
    #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #     glLoadIdentity()
    #     samples = self.audio_manager.get_samples()
    #     if len(samples) == 0:
    #         return
    #     # FFT
    #     window = np.hanning(len(samples))
    #     spectrum = np.abs(np.fft.rfft(samples * window))
    #     spectrum = spectrum[:self.bars]
    #     max_val = np.max(spectrum)
    #     if max_val < 1e-6:
    #         max_val = 1.0
    #     norm_spec = (spectrum / max_val) ** 0.6  # сглаживание пиков
    #     # Центр и параметры
    #     w, h = self.width(), self.height()
    #     cx, cy = w / 2, h / 2
    #     base_radius = min(w, h) * 0.2
    #     wave_strength = min(w, h) * 0.25  # насколько раздувается внешняя граница
    #     glBegin(GL_TRIANGLE_STRIP)
    #     for i in range(self.bars + 1):  # +1 чтобы замкнуть круг
    #         idx = i % self.bars
    #         angle = 2 * pi * (idx / self.bars)
    #         log_i = np.log10(1 + 9 * (idx / self.bars))
    #         bin_idx = int(log_i * len(norm_spec))
    #         bin_idx = np.clip(bin_idx, 0, len(norm_spec) - 1)
    #         amp = norm_spec[bin_idx]
    #         outer_radius = base_radius + amp * wave_strength
    #         # координаты на базовом и внешнем кольце
    #         x_base = cx + cos(angle) * base_radius
    #         y_base = cy + sin(angle) * base_radius
    #         x_outer = cx + cos(angle) * outer_radius
    #         y_outer = cy + sin(angle) * outer_radius
    #         hue = idx / self.bars
    #         r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    #         glColor4f(r, g, b, 0.6)
    #         glVertex2f(x_base, y_base)
    #         glVertex2f(x_outer, y_outer)
    #     glEnd()
    #     glFlush()
    #     painter = QPainter(self)
    #     painter.setRenderHint(QPainter.Antialiasing)
    #     painter.setPen(QColor("#61dafb"))
    #     w, h = self.width(), self.height()
    #     cx, cy = w / 2, h / 2
    #     # Пропорции
    #     vw, vh = w * 0.4, h * 0.3  # ширина и высота для "V"
    #     sw, sh = w * 0.16, h * 0.12  # ширина и высота для "S"
    #     # Смещение от центра — в долях высоты
    #     v_offset_y = h * 0.05   # опустить V чуть вниз
    #     s_offset_y = -h * 0.08  # поднять S чуть вверх
    #     # "V"
    #     font_v = QFont("Arial", int(min(w, h) * 0.25))
    #     font_v.setBold(True)
    #     painter.setFont(font_v)
    #     rect_v = QRectF(cx - vw / 2, cy - vh / 2 + v_offset_y, vw, vh)
    #     painter.drawText(rect_v, Qt.AlignCenter, "V")
    #     # "S"
    #     font_s = QFont("Arial", int(min(w, h) * 0.1))
    #     font_s.setBold(True)
    #     painter.setFont(font_s)
    #     rect_s = QRectF(cx - sw / 2, cy - sh / 2 + s_offset_y, sw, sh)
    #     painter.drawText(rect_s, Qt.AlignCenter, "S")
    #     painter.end()

    # def paintGL(self):
    #     if not self.run:
    #         return
    #     samples = self.audio_manager.get_samples()
    #     if len(samples) < 2:
    #         return

    #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #     glLoadIdentity()

    #     # FFT спектр
    #     window = np.hanning(len(samples))
    #     spectrum = np.abs(np.fft.rfft(samples * window))
    #     norm_spec = spectrum[:self.bars]

    #     # делим на 3 диапазона: низы, середина, верха
    #     n = len(norm_spec)
    #     minlow   = np.mean(norm_spec[:n // 24])       # самые низкие
    #     low      = np.mean(norm_spec[n // 24:n // 12])
    #     minmid   = np.mean(norm_spec[n // 12:n // 6])
    #     mid      = np.mean(norm_spec[n // 6:n // 3])
    #     minhigh  = np.mean(norm_spec[n // 3:n // 2])
    #     high     = np.mean(norm_spec[n // 2:])

    #     # нормировка
    #     max_val = np.max(spectrum) + 1e-6
    #     def norm(val): return min(val / max_val, 1.0)
    #     minlow, low, minmid, mid, minhigh, high = map(norm, [
    #         minlow, low, minmid, mid, minhigh, high
    #     ])

    #     # дыхание
    #     self.breath_phase += 0.05
    #     breath = 1 + 0.05 * np.sin(self.breath_phase)

    #     # размеры и центр
    #     w, h = self.width(), self.height()
    #     cx, cy = w / 2, h / 2
    #     base_radius = min(w, h) * 0.2 * breath
    #     wave_strength = min(w, h) * 0.3

    #     if not hasattr(self, 'phases'):
    #         self.phases = [0.0] * 6
    #     self.phases = [(p + spd) for p, spd in zip(self.phases, [0.02, -0.015, 0.01, -0.008, 0.012, -0.018])]

    #     # рисуем кольцо
    #     glBegin(GL_TRIANGLE_STRIP)
    #     for i in range(self.bars + 1):
    #         angle = 2 * pi * (i / self.bars)

    #         # смещения радиуса от "трех лун"
    #         wave = (
    #             abs(minlow  * sin(angle * 1 + self.phases[0])) +
    #             abs(low     * sin(angle * 2 + self.phases[1])) +
    #             abs(minmid  * sin(angle * 3 + self.phases[2])) +
    #             abs(mid     * sin(angle * 4 + self.phases[3])) +
    #             abs(minhigh * sin(angle * 7 + self.phases[4])) +
    #             abs(high    * sin(angle * 11 + self.phases[5]))
    #         )

    #         outer_radius = base_radius + wave * wave_strength

    #         # координаты
    #         x_base = cx + cos(angle) * base_radius
    #         y_base = cy + sin(angle) * base_radius
    #         x_outer = cx + cos(angle) * outer_radius
    #         y_outer = cy + sin(angle) * outer_radius

    #         # цвет от угла
    #         hue = i / self.bars
    #         r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    #         glColor4f(r, g, b, 0.7)
    #         glVertex2f(x_base, y_base)
    #         glVertex2f(x_outer, y_outer)
    #     glEnd()
    #     glFlush()

    def paintGL(self):
        if not self.run:
            return
        samples = self.audio_manager.get_samples()
        if len(samples) < 2:
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # FFT спектр
        window = np.hanning(len(samples))
        spectrum = np.abs(np.fft.rfft(samples * window))
        norm_spec = spectrum[:self.bars]

        # делим на 3 диапазона: низы, середина, верха
        n = len(norm_spec)
        minlow   = np.mean(norm_spec[:n // 24])       # самые низкие
        low      = np.mean(norm_spec[n // 24:n // 12])
        minmid   = np.mean(norm_spec[n // 12:n // 6])
        mid      = np.mean(norm_spec[n // 6:n // 3])
        minhigh  = np.mean(norm_spec[n // 3:n // 2])
        high     = np.mean(norm_spec[n // 2:])

        # нормировка
        max_val = np.max(spectrum) + 1e-6
        def norm(val): return min(val / max_val, 1.0)
        minlow, low, minmid, mid, minhigh, high = map(norm, [
            minlow, low, minmid, mid, minhigh, high
        ])

        # дыхание
        self.breath_phase += 0.05
        breath = 1 + 0.05 * np.sin(self.breath_phase)

        # размеры и центр
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_radius = min(w, h) * 0.2 * breath
        wave_strength = min(w, h) * 0.3

        if not hasattr(self, 'phases'):
            self.phases = [0.0] * 6
        self.phases = [(p + spd) for p, spd in zip(self.phases, [0.02, -0.015, 0.01, -0.008, 0.012, -0.018])]

        # ---- добавляем "шлейф" ----
        if not hasattr(self, "trails"):
            self.trails = []

        # массив текущего кольца
        radii = []
        for i in range(self.bars + 1):
            angle = 2 * pi * (i / self.bars)
            wave = (
                abs(minlow  * sin(angle * 1 + self.phases[0])) +
                abs(low     * sin(angle * 2 + self.phases[1])) +
                abs(minmid  * sin(angle * 3 + self.phases[2])) +
                abs(mid     * sin(angle * 4 + self.phases[3])) +
                abs(minhigh * sin(angle * 7 + self.phases[4])) +
                abs(high    * sin(angle * 11 + self.phases[5]))
            )
            outer_radius = base_radius + wave * wave_strength
            radii.append(outer_radius)

        # раз в кадр добавляем новый след
        self.trails.append({
            "radii": radii.copy(),
            "alpha": 0.5,
            "scale": 1.0
        })

        # рисуем следы (туман)
        for trail in list(self.trails):
            glBegin(GL_TRIANGLE_STRIP)
            for i in range(self.bars + 1):
                angle = 2 * pi * (i / self.bars)
                r = trail["radii"][i] * trail["scale"]

                x_outer = cx + cos(angle) * r
                y_outer = cy + sin(angle) * r
                x_base = cx + cos(angle) * base_radius
                y_base = cy + sin(angle) * base_radius

                glColor4f(1.0, 1.0, 1.0, trail["alpha"])  # белый туман
                glVertex2f(x_base, y_base)
                glVertex2f(x_outer, y_outer)
            glEnd()

            # обновляем параметры следа
            trail["alpha"] *= 0.92
            trail["scale"] *= 1.01
            if trail["alpha"] < 0.05:
                self.trails.remove(trail)

        # ---- ядро в центре ----
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(0.2, 0.8, 1.0, 0.35)  # яркое ядро (голубое) в центре
        glVertex2f(cx, cy)  # центр

        core_radius = base_radius * 0.9
        num_segments = 100
        for i in range(num_segments + 1):
            angle = 2 * pi * i / num_segments
            x = cx + cos(angle) * core_radius
            y = cy + sin(angle) * core_radius
            glColor4f(0.2, 0.8, 1.0, 0.0)  # на краях ядро растворяется
            glVertex2f(x, y)
        glEnd()

        # ---- основное текущее кольцо ----
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(self.bars + 1):
            angle = 2 * pi * (i / self.bars)
            outer_radius = radii[i]

            x_base = cx + cos(angle) * base_radius
            y_base = cy + sin(angle) * base_radius
            x_outer = cx + cos(angle) * outer_radius
            y_outer = cy + sin(angle) * outer_radius

            hue = i / self.bars
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            glColor4f(r, g, b, 0.7)
            glVertex2f(x_base, y_base)
            glVertex2f(x_outer, y_outer)
        glEnd()

        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()

class SoundGlowing(QOpenGLWidget):
    def __init__(self, audio_manager, run=False, parent=None):
        super().__init__(parent)
        self.run = run
        self.audio_manager = audio_manager
        self.timer = self.startTimer(33) if self.run else None

        # Настройки визуала
        self.layers = 3
        self.line_color = (0.38, 0.85, 0.98)  # бирюзовый
        self.base_alpha = 0.5
        self.fade_exponent = 1.2  # насколько быстро затухает к краям

    def initializeGL(self):
        glClearColor(32 / 255.0, 35 / 255.0, 42 / 255.0, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, w, 0, h)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not self.run:
            return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        width, height = self.width(), self.height()
        center_y = height / 2
        max_height = height * 0.4

        samples = self.audio_manager.get_samples()
        if np.max(np.abs(samples)) < 0.01:
            return

        # Нормализация
        max_val = np.max(np.abs(samples))
        norm_samples = samples / max_val if max_val > 0 else samples
        norm_samples = np.interp(np.linspace(0, len(samples), width), np.arange(len(samples)), norm_samples)

        for layer in range(self.layers):
            depth = layer * 2
            scale = 1.0 - layer * 0.1
            alpha_offset = layer * 0.12

            glBegin(GL_LINES)
            for x in range(width):
                sample_val = norm_samples[x]
                line_height = abs(sample_val) * max_height * scale
                top_y = center_y + line_height
                bottom_y = center_y - line_height

                # Расчёт альфа-затухания от центра
                distance = abs(x - width / 2) / (width / 2)
                fade = pow(1.0 - distance, self.fade_exponent)
                alpha = max(0.0, self.base_alpha * fade - alpha_offset)

                glColor4f(*self.line_color, alpha)
                glVertex2f(x, bottom_y - depth)
                glVertex2f(x, top_y - depth)
            glEnd()

        glFlush()

    def timerEvent(self, event):
        if self.run:
            self.update()