import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from zed import ZedApp, get_preset, list_presets

app = ZedApp()

# List all presets
print(list_presets())  # ['audio_flac', 'audio_mp3', ...]

# Get YouTube preset and apply it
preset = get_preset('youtube_1080p')
print(preset.resolution)  # 1920x1080

# Concatenate videos
app.concat(['intro.mp4', 'main.mp4', 'outro.mp4'], 'final.mp4')

# Extract audio
app.extract_audio('video.mp4', 'audio.mp3', audio_codec='mp3')

# Inspect media file
info = app.quick_info('video.mp4')
print(info['duration'])  # 00:05:30
print(info['video'])     # h264, 1920x1080, 30.00 fps