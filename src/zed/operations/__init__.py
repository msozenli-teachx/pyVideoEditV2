"""
Zed Operations Module

Media operations that use the FFmpeg engine.
Provides extensible operation handlers for video editing.
"""

from .clip import VideoClipper
from .concat import VideoConcatenator
from .audio import AudioExtractor, AudioProcessor
from .metadata import (
    MetadataInspector,
    MediaMetadata,
    VideoStreamInfo,
    AudioStreamInfo,
    FormatInfo,
    inspect_media,
)

__all__ = [
    'VideoClipper',
    'VideoConcatenator',
    'AudioExtractor',
    'AudioProcessor',
    'MetadataInspector',
    'MediaMetadata',
    'VideoStreamInfo',
    'AudioStreamInfo',
    'FormatInfo',
    'inspect_media',
]
