"""
Export Presets Module

Provides predefined export configurations for common use cases.
Presets encapsulate codec, bitrate, resolution, and format settings.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum

from .command import VideoCodec, AudioCodec, ContainerFormat


class PresetCategory(str, Enum):
    """Categories for organizing presets."""
    GENERAL = 'general'
    SOCIAL_MEDIA = 'social_media'
    PROFESSIONAL = 'professional'
    WEB = 'web'
    AUDIO_ONLY = 'audio_only'


@dataclass
class ExportPreset:
    """
    A predefined export configuration.
    
    Attributes:
        name: Unique preset identifier
        display_name: Human-readable name
        description: Detailed description of the preset
        category: Preset category for organization
        video_codec: Video codec to use (None for audio-only)
        audio_codec: Audio codec to use
        container: Output container format
        video_bitrate: Video bitrate (e.g., '5M', '1000k')
        audio_bitrate: Audio bitrate (e.g., '128k', '192k')
        resolution: Target resolution (e.g., '1920x1080', '1280x720')
        frame_rate: Target frame rate (e.g., 30, 60)
        extra_args: Additional FFmpeg arguments
        estimated_file_size: Estimated MB per minute (for user guidance)
    """
    
    name: str
    display_name: str
    description: str
    category: PresetCategory
    video_codec: Optional[VideoCodec] = None
    audio_codec: AudioCodec = AudioCodec.AAC
    container: ContainerFormat = ContainerFormat.MP4
    video_bitrate: Optional[str] = None
    audio_bitrate: str = '128k'
    resolution: Optional[str] = None
    frame_rate: Optional[int] = None
    extra_args: List[str] = field(default_factory=list)
    estimated_file_size: Optional[str] = None
    
    def apply_to_builder(self, builder) -> None:
        """
        Apply this preset's settings to an FFmpegCommandBuilder.
        
        Args:
            builder: FFmpegCommandBuilder instance to configure
        """
        if self.video_codec:
            builder.video_codec(self.video_codec)
        builder.audio_codec(self.audio_codec)
        
        if self.video_bitrate:
            builder.video_bitrate(self.video_bitrate)
        if self.audio_bitrate:
            builder.audio_bitrate(self.audio_bitrate)
        
        # Add resolution scaling if specified
        if self.resolution:
            width, height = self.resolution.split('x')
            builder.extra('-vf', f'scale={width}:{height}')
        
        # Add frame rate if specified
        if self.frame_rate:
            builder.extra('-r', str(self.frame_rate))
        
        # Add any extra arguments
        if self.extra_args:
            builder.extra(*self.extra_args)
    
    def get_file_extension(self) -> str:
        """Get the file extension for this preset's container format."""
        return f".{self.container.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary for serialization."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category.value,
            'video_codec': self.video_codec.value if self.video_codec else None,
            'audio_codec': self.audio_codec.value,
            'container': self.container.value,
            'video_bitrate': self.video_bitrate,
            'audio_bitrate': self.audio_bitrate,
            'resolution': self.resolution,
            'frame_rate': self.frame_rate,
            'extra_args': self.extra_args,
            'estimated_file_size': self.estimated_file_size,
        }


class PresetRegistry:
    """
    Registry for managing export presets.
    
    Provides access to built-in presets and supports custom preset registration.
    """
    
    def __init__(self):
        """Initialize the preset registry with built-in presets."""
        self._presets: Dict[str, ExportPreset] = {}
        self._register_builtin_presets()
    
    def _register_builtin_presets(self) -> None:
        """Register all built-in export presets."""
        
        # General Purpose
        self.register(ExportPreset(
            name='original',
            display_name='Original Quality',
            description='Maintain original quality with minimal re-encoding',
            category=PresetCategory.GENERAL,
            video_codec=VideoCodec.COPY,
            audio_codec=AudioCodec.COPY,
            container=ContainerFormat.MP4,
            estimated_file_size='Same as source',
        ))
        
        self.register(ExportPreset(
            name='high_quality',
            display_name='High Quality (H.264)',
            description='High quality H.264 encoding for general use',
            category=PresetCategory.GENERAL,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='8M',
            audio_bitrate='192k',
            estimated_file_size='~60 MB/min',
        ))
        
        self.register(ExportPreset(
            name='balanced',
            display_name='Balanced Quality',
            description='Good balance between quality and file size',
            category=PresetCategory.GENERAL,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='5M',
            audio_bitrate='128k',
            estimated_file_size='~40 MB/min',
        ))
        
        # Social Media Presets
        self.register(ExportPreset(
            name='youtube_1080p',
            display_name='YouTube 1080p',
            description='Optimized for YouTube upload (1080p)',
            category=PresetCategory.SOCIAL_MEDIA,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='8M',
            audio_bitrate='192k',
            resolution='1920x1080',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'],
            estimated_file_size='~60 MB/min',
        ))
        
        self.register(ExportPreset(
            name='youtube_4k',
            display_name='YouTube 4K',
            description='Optimized for YouTube upload (4K)',
            category=PresetCategory.SOCIAL_MEDIA,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='35M',
            audio_bitrate='192k',
            resolution='3840x2160',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'],
            estimated_file_size='~260 MB/min',
        ))
        
        self.register(ExportPreset(
            name='instagram_feed',
            display_name='Instagram Feed',
            description='Square format for Instagram feed posts',
            category=PresetCategory.SOCIAL_MEDIA,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='3M',
            audio_bitrate='128k',
            resolution='1080x1080',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p'],
            estimated_file_size='~25 MB/min',
        ))
        
        self.register(ExportPreset(
            name='instagram_reels',
            display_name='Instagram Reels/TikTok',
            description='Vertical 9:16 format for short-form video',
            category=PresetCategory.SOCIAL_MEDIA,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='4M',
            audio_bitrate='128k',
            resolution='1080x1920',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p'],
            estimated_file_size='~30 MB/min',
        ))
        
        self.register(ExportPreset(
            name='twitter',
            display_name='Twitter/X',
            description='Optimized for Twitter/X upload',
            category=PresetCategory.SOCIAL_MEDIA,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='5M',
            audio_bitrate='128k',
            resolution='1280x720',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p'],
            estimated_file_size='~40 MB/min',
        ))
        
        # Web Presets
        self.register(ExportPreset(
            name='web_optimized',
            display_name='Web Optimized',
            description='Compressed for web streaming',
            category=PresetCategory.WEB,
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='2M',
            audio_bitrate='96k',
            resolution='1280x720',
            frame_rate=30,
            extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'],
            estimated_file_size='~15 MB/min',
        ))
        
        self.register(ExportPreset(
            name='webm_hd',
            display_name='WebM HD',
            description='WebM format for HTML5 video',
            category=PresetCategory.WEB,
            video_codec=VideoCodec.VP9,
            audio_codec=AudioCodec.OPUS,
            container=ContainerFormat.WEBM,
            video_bitrate='3M',
            audio_bitrate='128k',
            resolution='1280x720',
            estimated_file_size='~25 MB/min',
        ))
        
        # Professional Presets
        self.register(ExportPreset(
            name='prores',
            display_name='Apple ProRes',
            description='High-quality intermediate format for editing',
            category=PresetCategory.PROFESSIONAL,
            video_codec=VideoCodec.PRORES,
            audio_codec=AudioCodec.PCM,
            container=ContainerFormat.MOV,
            video_bitrate='150M',
            audio_bitrate='1536k',
            estimated_file_size='~1 GB/min',
        ))
        
        self.register(ExportPreset(
            name='h265',
            display_name='H.265/HEVC',
            description='High efficiency codec for 4K content',
            category=PresetCategory.PROFESSIONAL,
            video_codec=VideoCodec.H265,
            audio_codec=AudioCodec.AAC,
            container=ContainerFormat.MP4,
            video_bitrate='4M',
            audio_bitrate='192k',
            estimated_file_size='~30 MB/min (better quality than H.264 at same size)',
        ))
        
        # Audio-Only Presets
        self.register(ExportPreset(
            name='audio_mp3',
            display_name='MP3 Audio',
            description='Standard MP3 audio export',
            category=PresetCategory.AUDIO_ONLY,
            video_codec=None,
            audio_codec=AudioCodec.MP3,
            container=ContainerFormat.MP3,
            audio_bitrate='192k',
            extra_args=['-vn'],
            estimated_file_size='~1.5 MB/min',
        ))
        
        self.register(ExportPreset(
            name='audio_wav',
            display_name='WAV Audio',
            description='Uncompressed WAV audio',
            category=PresetCategory.AUDIO_ONLY,
            video_codec=None,
            audio_codec=AudioCodec.PCM,
            container=ContainerFormat.WAV,
            audio_bitrate='1536k',
            extra_args=['-vn'],
            estimated_file_size='~10 MB/min',
        ))
        
        self.register(ExportPreset(
            name='audio_flac',
            display_name='FLAC Audio',
            description='Lossless compressed audio',
            category=PresetCategory.AUDIO_ONLY,
            video_codec=None,
            audio_codec=AudioCodec.FLAC,
            container=ContainerFormat.FLAC,
            audio_bitrate='800k',
            extra_args=['-vn'],
            estimated_file_size='~5 MB/min',
        ))
        
        # GIF Preset
        self.register(ExportPreset(
            name='gif',
            display_name='Animated GIF',
            description='Animated GIF (best for short clips)',
            category=PresetCategory.WEB,
            video_codec=None,
            audio_codec=None,
            container=ContainerFormat.GIF,
            resolution='480x270',
            frame_rate=15,
            extra_args=[
                '-vf', 'fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
                '-loop', '0'
            ],
            estimated_file_size='Varies greatly',
        ))
    
    def register(self, preset: ExportPreset) -> None:
        """
        Register a preset.
        
        Args:
            preset: ExportPreset to register
        """
        self._presets[preset.name] = preset
    
    def get(self, name: str) -> Optional[ExportPreset]:
        """
        Get a preset by name.
        
        Args:
            name: Preset identifier
            
        Returns:
            ExportPreset or None if not found
        """
        return self._presets.get(name)
    
    def get_all(self) -> List[ExportPreset]:
        """Get all registered presets."""
        return list(self._presets.values())
    
    def get_by_category(self, category: PresetCategory) -> List[ExportPreset]:
        """
        Get presets filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of presets in the category
        """
        return [p for p in self._presets.values() if p.category == category]
    
    def get_categories(self) -> List[PresetCategory]:
        """Get all categories that have presets."""
        categories = set(p.category for p in self._presets.values())
        return sorted(categories, key=lambda c: c.value)
    
    def list_preset_names(self) -> List[str]:
        """Get list of all preset names."""
        return sorted(self._presets.keys())


# Global preset registry instance
_preset_registry: Optional[PresetRegistry] = None


def get_preset_registry() -> PresetRegistry:
    """Get the global preset registry instance."""
    global _preset_registry
    if _preset_registry is None:
        _preset_registry = PresetRegistry()
    return _preset_registry


def get_preset(name: str) -> Optional[ExportPreset]:
    """Convenience function to get a preset by name."""
    return get_preset_registry().get(name)


def list_presets() -> List[str]:
    """Convenience function to list all preset names."""
    return get_preset_registry().list_preset_names()
