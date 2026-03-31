"""
Metadata Inspector Module

Provides comprehensive media file metadata extraction and analysis.
Wraps ffprobe with structured data classes for easy access.
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import timedelta

from ..logging import get_logger


@dataclass
class VideoStreamInfo:
    """Information about a video stream."""
    index: int
    codec_name: str
    codec_long_name: str
    profile: str
    width: int
    height: int
    display_aspect_ratio: str
    pixel_aspect_ratio: str
    frame_rate: float
    bit_rate: Optional[int] = None
    duration: Optional[float] = None
    nb_frames: Optional[int] = None
    pix_fmt: Optional[str] = None
    color_space: Optional[str] = None
    
    @property
    def resolution(self) -> str:
        """Get resolution as 'WIDTHxHEIGHT'."""
        return f"{self.width}x{self.height}"
    
    @property
    def megapixels(self) -> float:
        """Get megapixel count."""
        return (self.width * self.height) / 1_000_000


@dataclass
class AudioStreamInfo:
    """Information about an audio stream."""
    index: int
    codec_name: str
    codec_long_name: str
    sample_rate: int
    channels: int
    channel_layout: str
    bit_rate: Optional[int] = None
    duration: Optional[float] = None
    
    @property
    def sample_rate_khz(self) -> float:
        """Get sample rate in kHz."""
        return self.sample_rate / 1000


@dataclass
class SubtitleStreamInfo:
    """Information about a subtitle stream."""
    index: int
    codec_name: str
    language: Optional[str] = None
    title: Optional[str] = None


@dataclass
class FormatInfo:
    """Information about the container format."""
    filename: str
    format_name: str
    format_long_name: str
    duration: Optional[float] = None
    size: Optional[int] = None
    bit_rate: Optional[int] = None
    start_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        if self.size:
            return self.size / (1024 * 1024)
        return 0.0
    
    @property
    def duration_timedelta(self) -> Optional[timedelta]:
        """Get duration as timedelta."""
        if self.duration:
            return timedelta(seconds=self.duration)
        return None
    
    @property
    def formatted_duration(self) -> str:
        """Get formatted duration string (HH:MM:SS)."""
        if self.duration:
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            seconds = int(self.duration % 60)
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return f"{minutes:02d}:{seconds:02d}"
        return "Unknown"


@dataclass
class MediaMetadata:
    """
    Complete metadata for a media file.
    
    This is the main data class returned by the MetadataInspector.
    """
    path: Path
    format: FormatInfo
    video_streams: List[VideoStreamInfo] = field(default_factory=list)
    audio_streams: List[AudioStreamInfo] = field(default_factory=list)
    subtitle_streams: List[SubtitleStreamInfo] = field(default_factory=list)
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def has_video(self) -> bool:
        """Check if file has video streams."""
        return len(self.video_streams) > 0
    
    @property
    def has_audio(self) -> bool:
        """Check if file has audio streams."""
        return len(self.audio_streams) > 0
    
    @property
    def has_subtitles(self) -> bool:
        """Check if file has subtitle streams."""
        return len(self.subtitle_streams) > 0
    
    @property
    def primary_video(self) -> Optional[VideoStreamInfo]:
        """Get the primary (first) video stream."""
        return self.video_streams[0] if self.video_streams else None
    
    @property
    def primary_audio(self) -> Optional[AudioStreamInfo]:
        """Get the primary (first) audio stream."""
        return self.audio_streams[0] if self.audio_streams else None
    
    @property
    def resolution(self) -> Optional[str]:
        """Get resolution of primary video stream."""
        if self.primary_video:
            return self.primary_video.resolution
        return None
    
    @property
    def frame_rate(self) -> Optional[float]:
        """Get frame rate of primary video stream."""
        if self.primary_video:
            return self.primary_video.frame_rate
        return None
    
    @property
    def codec_summary(self) -> str:
        """Get a summary of codecs used."""
        parts = []
        if self.primary_video:
            parts.append(f"Video: {self.primary_video.codec_name}")
        if self.primary_audio:
            parts.append(f"Audio: {self.primary_audio.codec_name}")
        return ", ".join(parts) if parts else "Unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'path': str(self.path),
            'format': {
                'name': self.format.format_name,
                'duration': self.format.duration,
                'size_mb': round(self.format.size_mb, 2),
                'bitrate': self.format.bit_rate,
            },
            'video': [
                {
                    'codec': v.codec_name,
                    'resolution': v.resolution,
                    'frame_rate': v.frame_rate,
                    'bit_rate': v.bit_rate,
                }
                for v in self.video_streams
            ],
            'audio': [
                {
                    'codec': a.codec_name,
                    'sample_rate': a.sample_rate,
                    'channels': a.channels,
                    'bit_rate': a.bit_rate,
                }
                for a in self.audio_streams
            ],
            'subtitles': len(self.subtitle_streams),
        }


class MetadataInspector:
    """
    Media file metadata inspector.
    
    Provides comprehensive metadata extraction using ffprobe.
    """
    
    def __init__(self, ffprobe_path: str = 'ffprobe'):
        """
        Initialize the metadata inspector.
        
        Args:
            ffprobe_path: Path to ffprobe executable
        """
        self._ffprobe_path = ffprobe_path
        self._logger = get_logger('operations.metadata')
    
    def inspect(self, file_path: Union[str, Path]) -> MediaMetadata:
        """
        Inspect a media file and return comprehensive metadata.
        
        Args:
            file_path: Path to media file
        
        Returns:
            MediaMetadata object with all extracted information
        
        Raises:
            RuntimeError: If ffprobe fails or file cannot be analyzed
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        self._logger.debug(f"Inspecting: {path}")
        
        # Run ffprobe
        cmd = [
            self._ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-show_chapters',
            str(path),
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            data = json.loads(result.stdout)
            
            return self._parse_metadata(path, data)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffprobe timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")
    
    def _parse_metadata(self, path: Path, data: Dict[str, Any]) -> MediaMetadata:
        """Parse ffprobe JSON output into MediaMetadata."""
        
        # Parse format info
        format_data = data.get('format', {})
        format_info = FormatInfo(
            filename=format_data.get('filename', str(path)),
            format_name=format_data.get('format_name', 'unknown'),
            format_long_name=format_data.get('format_long_name', 'Unknown'),
            duration=self._parse_float(format_data.get('duration')),
            size=self._parse_int(format_data.get('size')),
            bit_rate=self._parse_int(format_data.get('bit_rate')),
            start_time=self._parse_float(format_data.get('start_time')),
            tags=format_data.get('tags', {}),
        )
        
        # Parse streams
        video_streams = []
        audio_streams = []
        subtitle_streams = []
        
        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            
            if codec_type == 'video':
                video_streams.append(self._parse_video_stream(stream))
            elif codec_type == 'audio':
                audio_streams.append(self._parse_audio_stream(stream))
            elif codec_type == 'subtitle':
                subtitle_streams.append(self._parse_subtitle_stream(stream))
        
        # Parse chapters
        chapters = data.get('chapters', [])
        
        return MediaMetadata(
            path=path,
            format=format_info,
            video_streams=video_streams,
            audio_streams=audio_streams,
            subtitle_streams=subtitle_streams,
            chapters=chapters,
        )
    
    def _parse_video_stream(self, stream: Dict[str, Any]) -> VideoStreamInfo:
        """Parse video stream data."""
        # Parse frame rate (may be a fraction like "30000/1001")
        frame_rate_str = stream.get('r_frame_rate', '0/1')
        frame_rate = self._parse_frame_rate(frame_rate_str)
        
        return VideoStreamInfo(
            index=stream.get('index', 0),
            codec_name=stream.get('codec_name', 'unknown'),
            codec_long_name=stream.get('codec_long_name', 'Unknown'),
            profile=stream.get('profile', ''),
            width=stream.get('width', 0),
            height=stream.get('height', 0),
            display_aspect_ratio=stream.get('display_aspect_ratio', 'N/A'),
            pixel_aspect_ratio=stream.get('sample_aspect_ratio', 'N/A'),
            frame_rate=frame_rate,
            bit_rate=self._parse_int(stream.get('bit_rate')),
            duration=self._parse_float(stream.get('duration')),
            nb_frames=self._parse_int(stream.get('nb_frames')),
            pix_fmt=stream.get('pix_fmt'),
            color_space=stream.get('color_space'),
        )
    
    def _parse_audio_stream(self, stream: Dict[str, Any]) -> AudioStreamInfo:
        """Parse audio stream data."""
        return AudioStreamInfo(
            index=stream.get('index', 0),
            codec_name=stream.get('codec_name', 'unknown'),
            codec_long_name=stream.get('codec_long_name', 'Unknown'),
            sample_rate=self._parse_int(stream.get('sample_rate')) or 0,
            channels=stream.get('channels', 0),
            channel_layout=stream.get('channel_layout', 'unknown'),
            bit_rate=self._parse_int(stream.get('bit_rate')),
            duration=self._parse_float(stream.get('duration')),
        )
    
    def _parse_subtitle_stream(self, stream: Dict[str, Any]) -> SubtitleStreamInfo:
        """Parse subtitle stream data."""
        tags = stream.get('tags', {})
        return SubtitleStreamInfo(
            index=stream.get('index', 0),
            codec_name=stream.get('codec_name', 'unknown'),
            language=tags.get('language'),
            title=tags.get('title'),
        )
    
    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[float]:
        """Safely parse a float from string."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        """Safely parse an int from string."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_frame_rate(frame_rate_str: str) -> float:
        """Parse frame rate from fraction string."""
        try:
            if '/' in frame_rate_str:
                num, den = frame_rate_str.split('/')
                return float(num) / float(den)
            return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def quick_info(self, file_path: Union[str, Path]) -> Dict[str, str]:
        """
        Get quick summary info about a file.
        
        Args:
            file_path: Path to media file
        
        Returns:
            Dictionary with key information
        """
        metadata = self.inspect(file_path)
        
        info = {
            'filename': metadata.path.name,
            'format': metadata.format.format_name,
            'duration': metadata.format.formatted_duration,
            'size': f"{metadata.format.size_mb:.1f} MB",
        }
        
        if metadata.primary_video:
            video = metadata.primary_video
            info['video'] = f"{video.codec_name}, {video.resolution}, {video.frame_rate:.2f} fps"
        
        if metadata.primary_audio:
            audio = metadata.primary_audio
            info['audio'] = f"{audio.codec_name}, {audio.sample_rate_khz:.1f} kHz, {audio.channels}ch"
        
        return info


# Convenience function
def inspect_media(file_path: Union[str, Path]) -> MediaMetadata:
    """
    Quick convenience function to inspect a media file.
    
    Args:
        file_path: Path to media file
    
    Returns:
        MediaMetadata object
    """
    inspector = MetadataInspector()
    return inspector.inspect(file_path)
