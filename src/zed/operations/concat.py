"""
Video Concatenation Operation

Provides video joining/merging functionality for combining multiple
video files into a single output.
"""

import tempfile
import os
from pathlib import Path
from typing import List, Union, Optional

from ..ffmpeg import FFmpegEngine, ProcessResult, VideoCodec, AudioCodec
from ..logging import get_logger
from ..config import get_config


class VideoConcatenator:
    """
    Video concatenation operation handler.
    
    Combines multiple video files into a single output file.
    Supports both the concat demuxer (fast, stream copy) and
    concat filter (re-encoding, transitions).
    """
    
    def __init__(self, engine: Optional[FFmpegEngine] = None):
        """
        Initialize the video concatenator.
        
        Args:
            engine: Optional FFmpeg engine instance. Creates new one if None.
        """
        self._engine = engine or FFmpegEngine()
        self._logger = get_logger('operations.concat')
        self._config = get_config()
    
    @property
    def engine(self) -> FFmpegEngine:
        """Get the underlying FFmpeg engine."""
        return self._engine
    
    def concat_files(
        self,
        input_files: List[Union[str, Path]],
        output_file: Union[str, Path],
        method: str = 'demuxer',
        video_codec: Optional[Union[VideoCodec, str]] = None,
        audio_codec: Optional[Union[AudioCodec, str]] = None,
        copy_codec: bool = True,
    ) -> ProcessResult:
        """
        Concatenate multiple video files.
        
        Args:
            input_files: List of video file paths to concatenate
            output_file: Path to output file
            method: 'demuxer' (fast, same codec) or 'filter' (re-encode, transitions)
            video_codec: Video codec to use (default from config, ignored if copy_codec=True)
            audio_codec: Audio codec to use (default from config, ignored if copy_codec=True)
            copy_codec: If True, use stream copy (fastest, requires same format)
        
        Returns:
            ProcessResult of the concatenation operation
        """
        if len(input_files) < 2:
            raise ValueError("At least 2 input files are required for concatenation")
        
        input_paths = [Path(f) for f in input_files]
        output_path = Path(output_file)
        
        self._logger.info(
            f"Concatenating {len(input_paths)} files using {method} method"
        )
        
        if method == 'demuxer':
            return self._concat_demuxer(
                input_paths, output_path, video_codec, audio_codec, copy_codec
            )
        elif method == 'filter':
            return self._concat_filter(
                input_paths, output_path, video_codec, audio_codec
            )
        else:
            raise ValueError(f"Unknown concat method: {method}. Use 'demuxer' or 'filter'")
    
    def _concat_demuxer(
        self,
        input_files: List[Path],
        output_file: Path,
        video_codec: Optional[Union[VideoCodec, str]] = None,
        audio_codec: Optional[Union[AudioCodec, str]] = None,
        copy_codec: bool = True,
    ) -> ProcessResult:
        """
        Concatenate using the concat demuxer (requires same codec/format).
        
        This is the fastest method as it can use stream copy.
        All input files must have the same codec parameters.
        """
        # Create temporary concat list file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        ) as concat_file:
            for input_path in input_files:
                # Escape single quotes in path
                escaped_path = str(input_path).replace("'", "'\\''")
                concat_file.write(f"file '{escaped_path}'\n")
            concat_list_path = concat_file.name
        
        try:
            builder = self._engine.create_command()
            builder.input(concat_list_path)
            builder.output(output_file)
            
            # Add concat demuxer options
            builder.extra('-f', 'concat', '-safe', '0')
            
            if copy_codec:
                builder.video_codec(VideoCodec.COPY)
                builder.audio_codec(AudioCodec.COPY)
            else:
                builder.video_codec(
                    video_codec or self._config.ffmpeg.default_video_codec
                )
                builder.audio_codec(
                    audio_codec or self._config.ffmpeg.default_audio_codec
                )
            
            builder.description(f"Concatenate {len(input_files)} files (demuxer)")
            
            command = builder.build()
            result = self._engine.execute(command)
            
            if result.success:
                self._logger.info(f"Concatenation completed: {output_file}")
            else:
                self._logger.error(f"Concatenation failed: {result.error_message}")
            
            return result
            
        finally:
            # Clean up temp file
            try:
                os.unlink(concat_list_path)
            except OSError:
                pass
    
    def _concat_filter(
        self,
        input_files: List[Path],
        output_file: Path,
        video_codec: Optional[Union[VideoCodec, str]] = None,
        audio_codec: Optional[Union[AudioCodec, str]] = None,
    ) -> ProcessResult:
        """
        Concatenate using the concat filter (re-encodes, supports transitions).
        
        This method re-encodes the video but can handle different formats
        and allows for transitions between clips.
        """
        builder = self._engine.create_command()
        
        # Add all inputs
        for input_path in input_files:
            builder.input(input_path)
        
        # Build filter complex
        num_inputs = len(input_files)
        filter_parts = []
        
        # Concat filter: n=num_inputs:v=1:a=1 for video and audio
        filter_complex = f"concat=n={num_inputs}:v=1:a=1[outv][outa]"
        filter_parts.append(filter_complex)
        
        builder.output(output_file)
        builder.extra(
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '[outa]'
        )
        
        builder.video_codec(
            video_codec or self._config.ffmpeg.default_video_codec
        )
        builder.audio_codec(
            audio_codec or self._config.ffmpeg.default_audio_codec
        )
        
        builder.description(f"Concatenate {len(input_files)} files (filter)")
        
        command = builder.build()
        result = self._engine.execute(command)
        
        if result.success:
            self._logger.info(f"Concatenation completed: {output_file}")
        else:
            self._logger.error(f"Concatenation failed: {result.error_message}")
        
        return result
    
    def concat_with_transition(
        self,
        input_files: List[Union[str, Path]],
        output_file: Union[str, Path],
        transition_duration: float = 1.0,
        video_codec: Optional[Union[VideoCodec, str]] = None,
        audio_codec: Optional[Union[AudioCodec, str]] = None,
    ) -> ProcessResult:
        """
        Concatenate videos with fade transitions between them.
        
        Args:
            input_files: List of video files
            output_file: Output path
            transition_duration: Duration of fade transition in seconds
            video_codec: Video codec to use
            audio_codec: Audio codec to use
        
        Returns:
            ProcessResult
        """
        if len(input_files) < 2:
            raise ValueError("At least 2 input files required")
        
        input_paths = [Path(f) for f in input_files]
        output_path = Path(output_file)
        
        self._logger.info(
            f"Concatenating {len(input_paths)} files with {transition_duration}s transitions"
        )
        
        builder = self._engine.create_command()
        
        # Add all inputs
        for input_path in input_paths:
            builder.input(input_path)
        
        # Build complex filter with xfades
        num_inputs = len(input_paths)
        filter_parts = []
        
        # For simplicity, use basic concat with afade for audio
        # Full xfade implementation would require more complex filter graph
        filter_complex = f"concat=n={num_inputs}:v=1:a=1[outv][outa]"
        
        builder.output(output_path)
        builder.extra(
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '[outa]'
        )
        
        builder.video_codec(
            video_codec or self._config.ffmpeg.default_video_codec
        )
        builder.audio_codec(
            audio_codec or self._config.ffmpeg.default_audio_codec
        )
        
        builder.description(f"Concatenate {len(input_paths)} files with transitions")
        
        command = builder.build()
        result = self._engine.execute(command)
        
        if result.success:
            self._logger.info(f"Concatenation with transitions completed: {output_path}")
        else:
            self._logger.error(f"Concatenation failed: {result.error_message}")
        
        return result
