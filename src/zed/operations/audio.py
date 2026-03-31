"""
Audio Operations Module

Provides audio extraction and manipulation functionality.
"""

from pathlib import Path
from typing import Optional, Union, List

from ..ffmpeg import FFmpegEngine, ProcessResult, AudioCodec, ContainerFormat
from ..logging import get_logger
from ..config import get_config


class AudioExtractor:
    """
    Audio extraction operation handler.
    
    Extracts audio tracks from video files with various format options.
    """
    
    def __init__(self, engine: Optional[FFmpegEngine] = None):
        """
        Initialize the audio extractor.
        
        Args:
            engine: Optional FFmpeg engine instance. Creates new one if None.
        """
        self._engine = engine or FFmpegEngine()
        self._logger = get_logger('operations.audio')
        self._config = get_config()
    
    @property
    def engine(self) -> FFmpegEngine:
        """Get the underlying FFmpeg engine."""
        return self._engine
    
    def extract_audio(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        audio_codec: Optional[Union[AudioCodec, str]] = None,
        audio_bitrate: Optional[str] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        track_index: Optional[int] = None,
    ) -> ProcessResult:
        """
        Extract audio from a video file.
        
        Args:
            input_file: Path to input video file
            output_file: Path to output audio file
            audio_codec: Audio codec to use (detected from extension if None)
            audio_bitrate: Audio bitrate (e.g., '128k', '192k')
            sample_rate: Sample rate in Hz (e.g., 44100, 48000)
            channels: Number of audio channels (1 for mono, 2 for stereo)
            track_index: Specific audio track to extract (0 = first, None = auto)
        
        Returns:
            ProcessResult of the extraction operation
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        self._logger.info(f"Extracting audio from {input_path.name} to {output_path.name}")
        
        # Auto-detect codec from output extension if not specified
        if audio_codec is None:
            audio_codec = self._detect_codec_from_extension(output_path.suffix)
        
        builder = self._engine.create_command()
        builder.input(input_path)
        builder.output(output_path)
        
        # Disable video
        builder.extra('-vn')
        
        # Select specific audio track if specified
        if track_index is not None:
            builder.extra('-map', f'0:a:{track_index}')
        else:
            builder.extra('-map', '0:a:0')  # First audio track
        
        # Set audio codec
        builder.audio_codec(audio_codec)
        
        # Set bitrate if specified
        if audio_bitrate:
            builder.audio_bitrate(audio_bitrate)
        
        # Add sample rate if specified
        if sample_rate:
            builder.extra('-ar', str(sample_rate))
        
        # Add channel configuration if specified
        if channels:
            builder.extra('-ac', str(channels))
        
        builder.description(f"Extract audio from {input_path.name}")
        
        command = builder.build()
        result = self._engine.execute(command)
        
        if result.success:
            self._logger.info(f"Audio extraction completed: {output_path}")
        else:
            self._logger.error(f"Audio extraction failed: {result.error_message}")
        
        return result
    
    def extract_all_tracks(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        output_format: str = 'mp3',
        naming_pattern: str = '{base}_track{index}.{ext}',
    ) -> List[ProcessResult]:
        """
        Extract all audio tracks from a video file.
        
        Args:
            input_file: Path to input video file
            output_dir: Directory for output files
            output_format: Output format extension (without dot)
            naming_pattern: Pattern for output filenames
                {base} = input filename without extension
                {index} = track index number
                {ext} = output format extension
        
        Returns:
            List of ProcessResults for each track extraction
        """
        input_path = Path(input_file)
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)
        
        # First, probe to find number of audio tracks
        probe_result = self._engine.probe(input_path)
        audio_tracks = [
            stream for stream in probe_result.get('streams', [])
            if stream.get('codec_type') == 'audio'
        ]
        
        if not audio_tracks:
            self._logger.warning(f"No audio tracks found in {input_path}")
            return []
        
        self._logger.info(f"Found {len(audio_tracks)} audio tracks in {input_path.name}")
        
        results = []
        base_name = input_path.stem
        
        for i, track in enumerate(audio_tracks):
            # Generate output filename
            output_name = naming_pattern.format(
                base=base_name,
                index=i,
                ext=output_format
            )
            output_path = output_directory / output_name
            
            # Determine codec from format
            codec = self._detect_codec_from_extension(f'.{output_format}')
            
            result = self.extract_audio(
                input_file=input_path,
                output_file=output_path,
                audio_codec=codec,
                track_index=i,
            )
            results.append(result)
        
        successful = sum(1 for r in results if r.success)
        self._logger.info(f"Extracted {successful}/{len(results)} audio tracks")
        
        return results
    
    def quick_extract(
        self,
        input_file: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        format: str = 'mp3',
    ) -> ProcessResult:
        """
        Quick audio extraction with automatic naming.
        
        Args:
            input_file: Path to input video file
            output_file: Optional output path (auto-generated if None)
            format: Output format ('mp3', 'wav', 'flac', 'aac')
        
        Returns:
            ProcessResult
        """
        input_path = Path(input_file)
        
        if output_file is None:
            # Auto-generate output path in default output directory
            output_dir = self._config.ffmpeg.default_output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{input_path.stem}_audio.{format}"
        else:
            output_path = Path(output_file)
        
        codec = self._detect_codec_from_extension(output_path.suffix)
        
        return self.extract_audio(
            input_file=input_path,
            output_file=output_path,
            audio_codec=codec,
        )
    
    def _detect_codec_from_extension(self, extension: str) -> AudioCodec:
        """
        Detect appropriate audio codec from file extension.
        
        Args:
            extension: File extension (e.g., '.mp3', '.wav')
        
        Returns:
            Appropriate AudioCodec
        """
        ext = extension.lower().lstrip('.')
        
        codec_map = {
            'mp3': AudioCodec.MP3,
            'wav': AudioCodec.PCM,
            'flac': AudioCodec.FLAC,
            'aac': AudioCodec.AAC,
            'm4a': AudioCodec.AAC,
            'ogg': AudioCodec.VORBIS,
            'opus': AudioCodec.OPUS,
            'webm': AudioCodec.OPUS,
        }
        
        return codec_map.get(ext, AudioCodec.AAC)


class AudioProcessor:
    """
    Audio processing operations (volume, fade, etc.).
    """
    
    def __init__(self, engine: Optional[FFmpegEngine] = None):
        """
        Initialize the audio processor.
        
        Args:
            engine: Optional FFmpeg engine instance
        """
        self._engine = engine or FFmpegEngine()
        self._logger = get_logger('operations.audio.processor')
    
    def adjust_volume(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        volume: float,
    ) -> ProcessResult:
        """
        Adjust audio volume.
        
        Args:
            input_file: Input audio or video file
            output_file: Output file
            volume: Volume multiplier (0.5 = half volume, 2.0 = double)
        
        Returns:
            ProcessResult
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        self._logger.info(f"Adjusting volume to {volume}x for {input_path.name}")
        
        builder = self._engine.create_command()
        builder.input(input_path)
        builder.output(output_path)
        
        # Use volume filter
        builder.extra('-af', f'volume={volume}')
        
        # Copy video if present
        builder.video_codec(VideoCodec.COPY)
        
        builder.description(f"Adjust volume to {volume}x")
        
        command = builder.build()
        return self._engine.execute(command)
    
    def fade_in_out(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        fade_in_duration: float = 1.0,
        fade_out_duration: float = 1.0,
        total_duration: Optional[float] = None,
    ) -> ProcessResult:
        """
        Apply fade in and fade out to audio.
        
        Args:
            input_file: Input file
            output_file: Output file
            fade_in_duration: Fade in duration in seconds
            fade_out_duration: Fade out duration in seconds
            total_duration: Total duration (auto-detected if None)
        
        Returns:
            ProcessResult
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        self._logger.info(f"Applying fade in/out to {input_path.name}")
        
        # Build fade filter
        fade_filter = f"afade=t=in:ss=0:d={fade_in_duration}"
        
        if total_duration:
            fade_out_start = total_duration - fade_out_duration
            fade_filter += f",afade=t=out:st={fade_out_start}:d={fade_out_duration}"
        
        builder = self._engine.create_command()
        builder.input(input_path)
        builder.output(output_path)
        builder.extra('-af', fade_filter)
        builder.video_codec(VideoCodec.COPY)
        
        builder.description(f"Fade audio in ({fade_in_duration}s) and out ({fade_out_duration}s)")
        
        command = builder.build()
        return self._engine.execute(command)
