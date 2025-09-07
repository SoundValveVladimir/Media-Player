import os
import numpy as np
import librosa
import asyncio
import subprocess
from moviepy import AudioFileClip
from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFileSystemWatcher, QObject

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(BASE_DIR, "Data", "ffmpeg", "bin", "ffmpeg.exe")


class FileCheckerThread(QThread):
    file_found = pyqtSignal(str)
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self._running = True

    def run(self):
        while self._running and (self.file_path is None or not os.path.exists(self.file_path)):
            QThread.msleep(500)
        if self._running:
            self.file_found.emit(self.file_path)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()

class AudioSyncManager(QObject):
    frameReady = pyqtSignal(int)  # позиция в ms

    def __init__(self, samples: np.ndarray, fps=44100, window_size=2048):
        super().__init__()
        self.samples = samples
        self.fps = fps
        self.window_size = window_size
        self.current_index = 0
        self.current_ms = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.advance)

    def start(self):
        self.timer.start(33)  # ~30FPS

    def stop(self):
        self.timer.stop()

    def advance(self):
        step = int(self.fps * 0.033)  # шаг ~33ms
        self.current_index += step
        if self.current_index >= len(self.samples):
            self.current_index = len(self.samples) - 1
            self.stop()
        self.current_ms = int(self.current_index / self.fps * 1000)
        self.frameReady.emit(self.current_ms)

    def get_samples(self):
        end = self.current_index + self.window_size
        chunk = self.samples[self.current_index:end]
        if len(chunk) < self.window_size:
            chunk = np.pad(chunk, (0, self.window_size - len(chunk)))
        return chunk

    def get_bass_amplitude(self):
        data = self.get_samples()
        fft = np.abs(np.fft.rfft(data * np.hanning(len(data))))
        freqs = np.fft.rfftfreq(len(data), 1.0/self.fps)
        bass_mask = (freqs >= 20) & (freqs <= 200)
        return np.mean(fft[bass_mask]) if np.any(bass_mask) else 0.0


class AudioAnalysisThread(QThread):
    chunkReady = pyqtSignal(np.ndarray)  # сигнал для каждой партии данных
    finished = pyqtSignal(int)           # сигнал о завершении, передаём длительность

    def __init__(self, file_path, chunk_seconds=5, fps=44100):
        super().__init__()
        self.file_path = file_path
        self.chunk_seconds = chunk_seconds
        self.fps = fps

    def run(self):
        try:
            chunk_size = self.chunk_seconds * self.fps
            cmd = [
                FFMPEG_PATH,
                "-i", self.file_path,
                "-f", "f32le",
                "-acodec", "pcm_f32le",
                "-ac", "1",
                "-ar", str(self.fps),
                "-"
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            bytes_per_sample = 4
            chunk_bytes = chunk_size * bytes_per_sample
            total_samples = 0
            while True:
                data = process.stdout.read(chunk_bytes)
                if not data:
                    break
                y_chunk = np.frombuffer(data, dtype=np.float32)
                total_samples += len(y_chunk)
                # RMS для этой партии
                hop_length = int(self.fps * 0.05)  # 50ms
                rms = librosa.feature.rms(y=y_chunk, frame_length=hop_length, hop_length=hop_length)[0]
                if np.max(rms) > 0:
                    rms /= np.max(rms)
                self.chunkReady.emit(rms)
            duration_ms = int(total_samples / self.fps * 1000)
            process.stdout.close()
            process.wait()
            self.finished.emit(duration_ms)
        except Exception as e:
            print(f"[Ошибка] Не удалось загрузить {self.file_path}: {e}")
            self.finished.emit(1)


class AudioSlider(QWidget):
    positionChanged = pyqtSignal(int)
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.file_path = file_path
        self.amplitude_data = []
        self.current_position_index = 0
        self.current_position_ms = 0
        self.is_dragging = False
        self.duration_ms = 1
        self.block_position_update = False
        self.file_checker_thread = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self.on_file_changed)
        if file_path:
            self.set_audio_file(file_path)

    def set_audio_file(self, new_path):
        if self.file_checker_thread:
            self.file_checker_thread.stop()
            self.file_checker_thread = None
        if self.file_path and self.file_path in self.watcher.files():
            self.watcher.removePath(self.file_path)
        self.file_path = new_path
        if not os.path.exists(new_path):
            self.wait_for_file()
        else:
            self.watcher.addPath(new_path)
            self.analyze_audio(new_path)

    def wait_for_file(self):
        self.file_checker_thread = FileCheckerThread(self.file_path)
        self.file_checker_thread.file_found.connect(self.on_file_available)
        self.file_checker_thread.start()

    def on_file_available(self, path):
        self.analyze_audio(path)
        self.watcher.addPath(path)

    def on_file_changed(self, path):
        print(f"[Слайдер] Файл изменился: {path}")
        QTimer.singleShot(100, lambda: self.watcher.addPath(path))
        self.analyze_audio(path)

    def analyze_audio(self, file_path):
        self.amplitude_data = np.array([])  # очищаем старые данные
        self.analysis_thread = AudioAnalysisThread(file_path)
        self.analysis_thread.chunkReady.connect(self.on_chunk_ready)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.start()

    def on_chunk_ready(self, chunk):
        self.amplitude_data = np.concatenate([self.amplitude_data, chunk])
        self.update()  # обновляем виджет по мере поступления данных

    def on_analysis_finished(self, duration_ms):
        self.duration_ms = duration_ms
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            if self.amplitude_data is None or len(self.amplitude_data) == 0:
                return

            # Ограничиваем количество точек для отображения
            MAX_DISPLAY_POINTS = 2000
            step = max(1, len(self.amplitude_data) // MAX_DISPLAY_POINTS)
            display_data = self.amplitude_data[::step]

            bar_width = self.width() / max(1, len(display_data))
            center_y = self.height() // 2

            for i, value in enumerate(display_data):
                bar_height = int((self.height() // 2) * value)
                x = int(i * bar_width)
                # Переводим индекс текущей позиции в индекс display_data
                display_index = int(self.current_position_index / max(1, len(self.amplitude_data)) * len(display_data))
                color = QColor("#61dafb") if i <= display_index else QColor("#444444")
                painter.setPen(QPen(color, 2))
                painter.drawLine(x, center_y, x, center_y - bar_height)
                painter.drawLine(x, center_y, x, center_y + bar_height)

            # # Отдельно рисуем ползунок текущей позиции
            # slider_x = int(self.current_position_index / max(1, len(self.amplitude_data)) * self.width())
            # painter.setPen(QPen(QColor("#ff5555"), 2))
            # painter.drawLine(slider_x, 0, slider_x, self.height())

        finally:
            painter.end()

    def set_duration(self, ms):
        self.duration_ms = max(ms, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.block_position_update = True
            self.jump_to_position(event)

    def mouseMoveEvent(self, event):
        if self.duration_ms > 0:
            x = event.pos().x()
            ratio = x / self.width()
            ratio = max(0, min(ratio, 1))
            position_ms = int(ratio * self.duration_ms)
            tooltip_text = self.milliseconds_to_mm_ss(position_ms)
            QToolTip.showText(event.globalPos(), tooltip_text, self)
        if self.is_dragging:
            self.jump_to_position(event)

    def milliseconds_to_mm_ss(self, milliseconds):
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02}:{seconds:02}"

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.jump_to_position(event)
            self.is_dragging = False
            self.positionChanged.emit(self.current_position_ms)
            self.block_position_update = False

    def jump_to_position(self, event):
        x = event.pos().x()
        ratio = x / self.width()
        ratio = max(0, min(ratio, 1))
        position_ms = int(ratio * self.duration_ms)
        self.current_position_ms = position_ms
        self.current_position_index = int(ratio * len(self.amplitude_data))
        self.update()

    def set_position(self, millis):
        if self.block_position_update:
            return
        if self.duration_ms > 0:
            self.current_position_ms = millis
            self.current_position_index = int(millis / self.duration_ms * len(self.amplitude_data))
            self.update()
