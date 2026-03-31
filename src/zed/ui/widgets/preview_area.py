"""
Preview Area Widget

Central panel for video playback preview.
Integrates QMediaPlayer for real-time video playback, synchronized
with PlaybackController and Timeline via signals.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QStackedLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# QMediaPlayer for real video playback
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False


class PreviewAreaWidget(QWidget):
    """
    Preview Area - Central video playback display.
    
    Features:
    - Real-time video playback via QMediaPlayer (when available)
    - Placeholder display when no video loaded
    - Transport controls (play, pause, stop)
    - Timecode display
    - Timeline scrubber
    - Position/duration signals for synchronization
    
    Signals:
        play_requested: User clicked play
        pause_requested: User clicked pause
        stop_requested: User clicked stop
        seek_requested: User scrubbed to position (float 0-1)
        position_changed: Playback position updated (float seconds)
        duration_changed: Media duration changed (float seconds)
    """
    
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    
    # New signals for video playback synchronization
    position_changed = pyqtSignal(float)  # Current time in seconds
    duration_changed = pyqtSignal(float)  # Total duration in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_playing = False
        self._duration = 0.0
        self._current_video_path: str = None
        self._media_player: QMediaPlayer = None
        self._video_widget: QVideoWidget = None
        self._setup_ui()
        self._setup_media_player()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the preview area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()
        
        # Resolution indicator (placeholder)
        resolution = QLabel("1920 × 1080")
        resolution.setObjectName("ResolutionLabel")
        header.addWidget(resolution)
        
        layout.addLayout(header)
        
        # Video display frame - uses stacked layout for video/placeholder
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("PreviewFrame")
        self.preview_frame.setFrameShape(QFrame.Shape.Box)
        self.preview_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.preview_frame.setMinimumSize(640, 360)
        
        # Stacked layout: video widget on top, placeholder label beneath
        self._stacked_layout = QStackedLayout(self.preview_frame)
        
        # Placeholder text (shown when no video)
        self.preview_label = QLabel("▶\n\nVIDEO PREVIEW\n\nImport a video to begin")
        self.preview_label.setObjectName("PreviewLabel")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stacked_layout.addWidget(self.preview_label)
        
        # QVideoWidget (for real video playback, added in _setup_media_player)
        self._video_widget_placeholder = QLabel("Loading video...")
        self._video_widget_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_widget_placeholder.setStyleSheet("color: #6a6a6a; background: #0d0d10;")
        self._stacked_layout.addWidget(self._video_widget_placeholder)
        
        layout.addWidget(self.preview_frame, stretch=1)
        
        # Timeline scrubber
        scrubber_layout = QHBoxLayout()
        self.timecode_label = QLabel("00:00:00 / 00:00:00")
        self.timecode_label.setObjectName("TimecodeLabel")
        self.timecode_label.setFixedWidth(140)
        
        self.scrubber = QSlider(Qt.Orientation.Horizontal)
        self.scrubber.setRange(0, 1000)
        self.scrubber.setValue(0)
        self.scrubber.valueChanged.connect(self._on_scrubber_change)
        
        scrubber_layout.addWidget(self.timecode_label)
        scrubber_layout.addWidget(self.scrubber, stretch=1)
        
        layout.addLayout(scrubber_layout)
        
        # Transport controls container (ensures visibility)
        self.controls_container = QFrame()
        self.controls_container.setObjectName("ControlsContainer")
        controls_layout = QHBoxLayout(self.controls_container)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.setSpacing(12)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        
        # Stop button
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("TransportButton")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self._on_stop)
        
        # Previous frame button (placeholder)
        self.prev_frame_btn = QPushButton("⏮")
        self.prev_frame_btn.setObjectName("TransportButton")
        self.prev_frame_btn.setToolTip("Previous Frame")
        
        # Play/Pause button
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("TransportButton")
        self.play_btn.setToolTip("Play")
        self.play_btn.clicked.connect(self._on_play_pause)
        
        # Next frame button (placeholder)
        self.next_frame_btn = QPushButton("⏭")
        self.next_frame_btn.setObjectName("TransportButton")
        self.next_frame_btn.setToolTip("Next Frame")
        
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.prev_frame_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_frame_btn)
        
        layout.addWidget(self.controls_container)
    
    def _setup_media_player(self):
        """Initialize QMediaPlayer for real video playback with audio."""
        if not HAS_QT_MULTIMEDIA:
            # PyQt6 multimedia not available - fallback to placeholder only
            return
        
        # Create media player
        self._media_player = QMediaPlayer(self)
        
        # Create audio output for sound
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(1.0)  # Full volume
        self._media_player.setAudioOutput(self._audio_output)
        
        # Create video widget and add to stacked layout
        self._video_widget = QVideoWidget()
        self._video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._video_widget.setStyleSheet("background-color: black;")
        self._stacked_layout.insertWidget(1, self._video_widget)  # Index 1 = above placeholder
        
        # Set video output
        self._media_player.setVideoOutput(self._video_widget)
        
        # Connect signals for synchronization
        self._media_player.positionChanged.connect(self._on_media_position_changed)
        self._media_player.durationChanged.connect(self._on_media_duration_changed)
        self._media_player.playbackStateChanged.connect(self._on_media_state_changed)
        self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        # When video loaded, show video widget instead of placeholder
        self._media_player.mediaStatusChanged.connect(self._update_display_mode)
        
        # Setup timer for smooth scrubber updates
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._on_timer_update)
        self._update_timer.start(50)  # Update every 50ms
    
    def _on_media_position_changed(self, position_ms: int):
        """QMediaPlayer position changed → emit position_changed signal."""
        time_sec = position_ms / 1000.0
        self.position_changed.emit(time_sec)
        
        # Update timecode
        if self._duration > 0:
            current_str = self._format_time(time_sec)
            total_str = self._format_time(self._duration)
            self.timecode_label.setText(f"{current_str} / {total_str}")
    
    def _on_media_duration_changed(self, duration_ms: int):
        """QMediaPlayer duration changed → emit duration_changed signal."""
        self._duration = duration_ms / 1000.0
        self.duration_changed.emit(self._duration)
        
        # Update timecode display
        total_str = self._format_time(self._duration)
        self.timecode_label.setText(f"00:00:00 / {total_str}")
    
    def _on_media_state_changed(self, state):
        """QMediaPlayer state changed → update internal state and emit."""
        from PyQt6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_playing = True
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("Pause")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
    
    def _on_media_status_changed(self, status):
        """Handle media loading status - auto-play when loaded."""
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # Video loaded, set duration and auto-play
            duration_ms = self._media_player.duration()
            if duration_ms > 0:
                self._duration = duration_ms / 1000.0
                self.duration_changed.emit(self._duration)
            # Auto-play with audio
            self._media_player.play()
    
    def _update_display_mode(self, status):
        """Switch between placeholder and video widget based on media status."""
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._video_widget:
            # Show video widget (index 1 in stacked layout)
            self._stacked_layout.setCurrentIndex(1)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Loop video when it ends
            self._media_player.setPosition(0)
            self._media_player.play()
        else:
            # Show placeholder (index 0)
            self._stacked_layout.setCurrentIndex(0)
    
    def _on_timer_update(self):
        """Timer-based update for smooth scrubber movement."""
        if self._media_player and self._is_playing:
            position_ms = self._media_player.position()
            time_sec = position_ms / 1000.0
            # Update scrubber without triggering seek
            if self._duration > 0:
                frac = time_sec / self._duration
                self.scrubber.blockSignals(True)
                self.scrubber.setValue(int(frac * 1000))
                self.scrubber.blockSignals(False)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #ResolutionLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding: 2px 8px;
                background-color: #222226;
                border-radius: 4px;
            }
            #PreviewFrame {
                background-color: #0d0d10;
                border: 1px solid #2d2d32;
                border-radius: 8px;
            }
            #PreviewLabel {
                color: #3a3a3f;
                font-size: 14px;
                font-weight: 500;
            }
            #TimecodeLabel {
                color: #a0a0a0;
                font-family: "Consolas", monospace;
                font-size: 12px;
            }
            #ControlsContainer {
                background-color: #1e1e22;
                border-top: 1px solid #2d2d32;
                border-radius: 0 0 6px 6px;
            }
            #TransportButton {
                background-color: #2d2d32;
                border: 1px solid #4a6fa5;
                border-radius: 20px;
                font-size: 16px;
                color: #e0e0e0;
                min-width: 44px;
                min-height: 44px;
            }
            #TransportButton:hover {
                background-color: #4a6fa5;
                border-color: #5a7fb5;
            }
            #TransportButton:pressed {
                background-color: #3a5f95;
            }
        """)
    
    def _on_play_pause(self):
        """Toggle play/pause - delegates to QMediaPlayer if available."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            # Let QMediaPlayer handle it
            if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media_player.pause()
                self.pause_requested.emit()
            else:
                self._media_player.play()
                self.play_requested.emit()
        else:
            # Fallback: just toggle state and emit signals
            self._is_playing = not self._is_playing
            if self._is_playing:
                self.play_btn.setText("⏸")
                self.play_btn.setToolTip("Pause")
                self.play_requested.emit()
            else:
                self.play_btn.setText("▶")
                self.play_btn.setToolTip("Play")
                self.pause_requested.emit()
    
    def _on_stop(self):
        """Stop playback - delegates to QMediaPlayer if available."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.stop()
            self.stop_requested.emit()
        else:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
            self.scrubber.setValue(0)
            self.stop_requested.emit()
    
    def _on_scrubber_change(self, value: int):
        """Handle scrubber movement - seeks QMediaPlayer if available."""
        position = value / 1000.0  # Normalize to 0-1
        self.seek_requested.emit(position)
        
        # Also seek QMediaPlayer directly with proper audio sync
        if self._media_player and HAS_QT_MULTIMEDIA and self._duration > 0:
            seek_ms = int(position * self._duration * 1000)
            was_playing = self._is_playing
            # Brief pause during seek for smoother scrubbing
            if was_playing:
                self._media_player.pause()
            self._media_player.setPosition(seek_ms)
            # Update timecode immediately
            time_sec = seek_ms / 1000.0
            current_str = self._format_time(time_sec)
            total_str = self._format_time(self._duration)
            self.timecode_label.setText(f"{current_str} / {total_str}")
            self.position_changed.emit(time_sec)
            # Resume if was playing
            if was_playing:
                self._media_player.play()
    
    def update_timecode(self, current: str, total: str):
        """Update timecode display."""
        self.timecode_label.setText(f"{current} / {total}")
    
    def set_playing(self, is_playing: bool):
        """Set play state from external source (e.g., PlaybackController)."""
        self._is_playing = is_playing
        self.play_btn.setText("⏸" if is_playing else "▶")
    
    def on_position_update(self, time: float):
        """
        Called by PlaybackController when position changes.
        
        Args:
            time: Current position in seconds
        """
        # Update timecode display
        # (In real app, this would also trigger frame decoding/rendering)
        if self._duration > 0:
            current_str = self._format_time(time)
            total_str = self._format_time(self._duration)
            self.timecode_label.setText(f"{current_str} / {total_str}")
        
        # Update scrubber position (0-1000 range)
        if self._duration > 0:
            frac = time / self._duration
            # Block signal to avoid re-emitting seek_requested
            self.scrubber.blockSignals(True)
            self.scrubber.setValue(int(frac * 1000))
            self.scrubber.blockSignals(False)
    
    def set_duration(self, duration: float):
        """Set the media duration (called when video is loaded)."""
        self._duration = duration
        self.update_timecode("00:00:00", self._format_time(duration))
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS or MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    
    # ===== Public API for video loading =====
    
    def load_video(self, path: str):
        """
        Load a video file for preview with auto-play.
        
        Args:
            path: Path to the video file
        """
        self._current_video_path = path
        
        if self._media_player and HAS_QT_MULTIMEDIA:
            # Load into QMediaPlayer
            url = QUrl.fromLocalFile(str(path))
            self._media_player.setSource(url)
            
            # Show video widget immediately and raise to top
            if self._video_widget:
                self._stacked_layout.setCurrentIndex(1)
                self._video_widget.raise_()
            
            # Note: duration_changed signal will fire when loaded, and auto-play will trigger
        else:
            # No multimedia support - just store path, use placeholder
            self._duration = 30.0  # Placeholder
            self.duration_changed.emit(self._duration)
            self.set_duration(30.0)
            # Show placeholder
            self._stacked_layout.setCurrentIndex(0)
    
    def play(self):
        """Start playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.play()
        self.play_requested.emit()
    
    def pause(self):
        """Pause playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.pause()
        self.pause_requested.emit()
    
    def stop(self):
        """Stop playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.stop()
        self.stop_requested.emit()
    
    def seek(self, time_seconds: float):
        """Seek to position - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.setPosition(int(time_seconds * 1000))
        self.seek_requested.emit(time_seconds / max(self._duration, 1))
