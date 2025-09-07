# The hobbyist SoundValve Project
# Python media player with visualization

## Description
This is a media player project.  
It requires **FFmpeg** for audio and video processing.

## Requirements
- Python 3.10+
- FFmpeg installed in the project directory

## FFmpeg Setup
You must download FFmpeg manually, because the binary files are not included in the repository.  
Download from the official website:

- Official FFmpeg: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)  
- Windows builds: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

After downloading, place `ffmpeg.exe` into this path inside the project:
Data/ffmpeg/bin/ffmpeg.exe


The project will automatically use it via:
```python
FFMPEG_PATH = os.path.join(BASE_DIR, "Data", "ffmpeg", "bin", "ffmpeg.exe")
