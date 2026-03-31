"""
Zed Video Editor - Core Package

A scalable foundation for video editing applications built with
Python, PyQt6, and FFmpeg.

This package provides:
- Core FFmpeg engine for process management
- Centralized task manager for concurrent operations
- Configurable logging system
- Extensible operation framework

Usage:
    from zed import ZedApp, FFmpegEngine, TaskManager
    
    # Initialize the application
    app = ZedApp()
    
    # Use the FFmpeg engine directly
    engine = app.ffmpeg
    result = engine.clip_video('input.mp4', 'output.mp4', 10, 30)
    
    # Or use the task manager for concurrent operations
    task_id = app.tasks.submit_media_operation(
        engine.clip_video, 'input.mp4', 'output.mp4', 10, 30
    )
"""

from .config import (
    ZedConfig,
    FFmpegConfig,
    TaskManagerConfig,
    LoggingConfig,
    get_config,
    set_config,
)

from .logging import (
    get_logger,
    configure_logging,
)

from .ffmpeg import (
    FFmpegEngine,
    FFmpegCommand,
    FFmpegCommandBuilder,
    VideoCodec,
    AudioCodec,
    ContainerFormat,
    ProcessResult,
    ProcessStatus,
    ExportPreset,
    PresetRegistry,
    PresetCategory,
    get_preset_registry,
    get_preset,
    list_presets,
)

from .tasks import (
    TaskManager,
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
)

from .operations import (
    VideoClipper,
    VideoConcatenator,
    AudioExtractor,
    AudioProcessor,
    MetadataInspector,
    MediaMetadata,
    VideoStreamInfo,
    AudioStreamInfo,
    FormatInfo,
    inspect_media,
)

__version__ = '0.1.0'

# Import for ZedApp class (must be at module level)
import logging
from typing import Optional, List


class ZedApp:
    """
    Main application class that ties together all components.
    
    Provides a unified interface to the FFmpeg engine, task manager,
    and configuration. This is the recommended entry point for
    building applications on top of zed-base.
    
    Example:
        app = ZedApp()
        
        # Quick video clip
        result = app.clip('input.mp4', 'output.mp4', 10, 30)
        
        # Or submit as a task for concurrent execution
        task_id = app.submit_clip('input.mp4', 'output.mp4', 10, 30)
        app.wait(task_id)
    """
    
    def __init__(self, config: Optional[ZedConfig] = None):
        """
        Initialize the Zed application.
        
        Args:
            config: Optional configuration. Uses defaults if None.
        """
        if config:
            set_config(config)
        
        self._config = get_config()
        self._logger = get_logger('core')
        
        # Initialize components lazily
        self._task_manager: Optional[TaskManager] = None
        self._ffmpeg_engine: Optional[FFmpegEngine] = None
        self._clipper: Optional[VideoClipper] = None
        self._concatenator: Optional[VideoConcatenator] = None
        self._audio_extractor: Optional[AudioExtractor] = None
        self._metadata_inspector: Optional[MetadataInspector] = None
        
        # Configure logging
        log_level = getattr(logging, self._config.logging.level.upper(), logging.INFO)
        configure_logging(
            level=log_level,
            log_file=self._config.logging.log_file,
            console_output=self._config.logging.console_output,
            file_output=self._config.logging.file_output,
        )
        
        self._logger.info(f"{self._config.app_name} v{self._config.app_version} initialized")
    
    @property
    def config(self) -> ZedConfig:
        """Get the application configuration."""
        return self._config
    
    @property
    def tasks(self) -> TaskManager:
        """Get the task manager."""
        if self._task_manager is None:
            self._task_manager = TaskManager()
        return self._task_manager
    
    @property
    def ffmpeg(self) -> FFmpegEngine:
        """Get the FFmpeg engine."""
        if self._ffmpeg_engine is None:
            self._ffmpeg_engine = FFmpegEngine()
        return self._ffmpeg_engine
    
    @property
    def clipper(self) -> VideoClipper:
        """Get the video clipper operation."""
        if self._clipper is None:
            self._clipper = VideoClipper(self.ffmpeg)
        return self._clipper
    
    @property
    def concatenator(self) -> VideoConcatenator:
        """Get the video concatenator operation."""
        if self._concatenator is None:
            self._concatenator = VideoConcatenator(self.ffmpeg)
        return self._concatenator
    
    @property
    def audio_extractor(self) -> AudioExtractor:
        """Get the audio extractor operation."""
        if self._audio_extractor is None:
            self._audio_extractor = AudioExtractor(self.ffmpeg)
        return self._audio_extractor
    
    @property
    def metadata_inspector(self) -> MetadataInspector:
        """Get the metadata inspector."""
        if self._metadata_inspector is None:
            self._metadata_inspector = MetadataInspector(
                self._config.ffmpeg.resolve_ffprobe_path()
            )
        return self._metadata_inspector
    
    # Convenience methods
    
    def clip(
        self,
        input_file: str,
        output_file: str,
        start_time: float,
        duration: Optional[float] = None,
        end_time: Optional[float] = None,
        **kwargs
    ) -> ProcessResult:
        """
        Clip a video segment.
        
        Args:
            input_file: Input video file
            output_file: Output file path
            start_time: Start time in seconds
            duration: Duration (alternative to end_time)
            end_time: End time (alternative to duration)
            **kwargs: Additional options (video_codec, audio_codec, copy_codec)
        
        Returns:
            ProcessResult
        """
        return self.clipper.clip(
            input_file, output_file, start_time,
            duration=duration, end_time=end_time, **kwargs
        )
    
    def submit_clip(
        self,
        input_file: str,
        output_file: str,
        start_time: float,
        duration: Optional[float] = None,
        end_time: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Submit a video clipping task for concurrent execution.
        
        Returns:
            Task ID
        """
        return self.tasks.submit_media_operation(
            self.clipper.clip,
            input_file, output_file, start_time,
            duration=duration, end_time=end_time,
            **kwargs
        )
    
    def wait(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Wait for a task to complete."""
        return self.tasks.wait(task_id, timeout=timeout)
    
    def concat(
        self,
        input_files: List[str],
        output_file: str,
        method: str = 'demuxer',
        **kwargs
    ) -> 'ProcessResult':
        """
        Concatenate multiple video files.
        
        Args:
            input_files: List of video files to concatenate
            output_file: Output file path
            method: 'demuxer' (fast, same format) or 'filter' (re-encode)
            **kwargs: Additional options
        
        Returns:
            ProcessResult
        """
        return self.concatenator.concat_files(
            input_files, output_file, method=method, **kwargs
        )
    
    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        **kwargs
    ) -> 'ProcessResult':
        """
        Extract audio from a video file.
        
        Args:
            input_file: Input video file
            output_file: Output audio file
            **kwargs: Additional options (audio_codec, audio_bitrate, etc.)
        
        Returns:
            ProcessResult
        """
        return self.audio_extractor.extract_audio(
            input_file, output_file, **kwargs
        )
    
    def inspect(self, file_path: str) -> 'MediaMetadata':
        """
        Inspect a media file and return comprehensive metadata.
        
        Args:
            file_path: Path to media file
        
        Returns:
            MediaMetadata object
        """
        return self.metadata_inspector.inspect(file_path)
    
    def quick_info(self, file_path: str) -> dict:
        """
        Get quick summary info about a media file.
        
        Args:
            file_path: Path to media file
        
        Returns:
            Dictionary with key information
        """
        return self.metadata_inspector.quick_info(file_path)
    
    def get_stats(self) -> dict:
        """Get application statistics."""
        return {
            'config': {
                'app_name': self._config.app_name,
                'app_version': self._config.app_version,
            },
            'tasks': self.tasks.get_stats(),
        }
    
    def shutdown(self) -> None:
        """Shutdown the application and cleanup resources."""
        self._logger.info("Shutting down application...")
        
        if self._task_manager:
            self._task_manager.shutdown(wait=True)
        
        if self._ffmpeg_engine:
            self._ffmpeg_engine.cancel_all()
        
        self._logger.info("Application shutdown complete")


__all__ = [
    # Config
    'ZedConfig',
    'FFmpegConfig',
    'TaskManagerConfig',
    'LoggingConfig',
    'get_config',
    'set_config',
    # Logging
    'get_logger',
    'configure_logging',
    # FFmpeg
    'FFmpegEngine',
    'FFmpegCommand',
    'FFmpegCommandBuilder',
    'VideoCodec',
    'AudioCodec',
    'ContainerFormat',
    'ProcessResult',
    'ProcessStatus',
    # Tasks
    'TaskManager',
    'Task',
    'TaskResult',
    'TaskStatus',
    'TaskPriority',
    # Operations
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
    # Presets
    'ExportPreset',
    'PresetRegistry',
    'PresetCategory',
    'get_preset_registry',
    'get_preset',
    'list_presets',
    # Application
    'ZedApp',
]
