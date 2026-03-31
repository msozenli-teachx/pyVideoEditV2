"""
Metadata Panel

Widget for displaying media file metadata information.
Shows video, audio, and format details.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...operations.metadata import MediaMetadata


class MetadataPanelWidget(QWidget):
    """
    Metadata Panel - Displays detailed media file information.
    
    Shows:
    - File format and container info
    - Video stream details
    - Audio stream details
    - Duration and file size
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._metadata: MediaMetadata = None
        self._setup_ui()
        self._apply_styles()
        self._show_placeholder()
    
    def _setup_ui(self):
        """Build the metadata panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Media Info")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        
        # Placeholder label (shown when no metadata)
        self.placeholder_label = QLabel("Import a video to see metadata")
        self.placeholder_label.setObjectName("PlaceholderLabel")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setMinimumHeight(200)
        self.content_layout.addWidget(self.placeholder_label)
        
        # Format info group
        self.format_group = QGroupBox("File Information")
        self.format_group.setObjectName("InfoGroup")
        self.format_group.setVisible(False)
        format_layout = QVBoxLayout(self.format_group)
        format_layout.setContentsMargins(12, 16, 12, 12)
        format_layout.setSpacing(6)
        
        self.filename_label = self._create_info_label("Filename: -")
        self.format_label = self._create_info_label("Format: -")
        self.duration_label = self._create_info_label("Duration: -")
        self.size_label = self._create_info_label("Size: -")
        self.bitrate_label = self._create_info_label("Bitrate: -")
        
        format_layout.addWidget(self.filename_label)
        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.duration_label)
        format_layout.addWidget(self.size_label)
        format_layout.addWidget(self.bitrate_label)
        
        self.content_layout.addWidget(self.format_group)
        
        # Video info group
        self.video_group = QGroupBox("Video Stream")
        self.video_group.setObjectName("InfoGroup")
        self.video_group.setVisible(False)
        video_layout = QVBoxLayout(self.video_group)
        video_layout.setContentsMargins(12, 16, 12, 12)
        video_layout.setSpacing(6)
        
        self.video_codec_label = self._create_info_label("Codec: -")
        self.video_resolution_label = self._create_info_label("Resolution: -")
        self.video_framerate_label = self._create_info_label("Frame Rate: -")
        self.video_pixfmt_label = self._create_info_label("Pixel Format: -")
        self.video_bitrate_label = self._create_info_label("Bitrate: -")
        
        video_layout.addWidget(self.video_codec_label)
        video_layout.addWidget(self.video_resolution_label)
        video_layout.addWidget(self.video_framerate_label)
        video_layout.addWidget(self.video_pixfmt_label)
        video_layout.addWidget(self.video_bitrate_label)
        
        self.content_layout.addWidget(self.video_group)
        
        # Audio info group
        self.audio_group = QGroupBox("Audio Stream")
        self.audio_group.setObjectName("InfoGroup")
        self.audio_group.setVisible(False)
        audio_layout = QVBoxLayout(self.audio_group)
        audio_layout.setContentsMargins(12, 16, 12, 12)
        audio_layout.setSpacing(6)
        
        self.audio_codec_label = self._create_info_label("Codec: -")
        self.audio_samplerate_label = self._create_info_label("Sample Rate: -")
        self.audio_channels_label = self._create_info_label("Channels: -")
        self.audio_bitrate_label = self._create_info_label("Bitrate: -")
        
        audio_layout.addWidget(self.audio_codec_label)
        audio_layout.addWidget(self.audio_samplerate_label)
        audio_layout.addWidget(self.audio_channels_label)
        audio_layout.addWidget(self.audio_bitrate_label)
        
        self.content_layout.addWidget(self.audio_group)
        
        # Subtitle info
        self.subtitle_label = self._create_info_label("Subtitles: None")
        self.subtitle_label.setVisible(False)
        self.content_layout.addWidget(self.subtitle_label)
        
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
    
    def _create_info_label(self, text: str) -> QLabel:
        """Create a standardized info label."""
        label = QLabel(text)
        label.setObjectName("InfoLabel")
        label.setWordWrap(True)
        return label
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
            }
            #PlaceholderLabel {
                color: #6a6a6a;
                font-size: 13px;
                font-style: italic;
            }
            #InfoGroup {
                color: #e0e0e0;
                font-weight: bold;
                border: 1px solid #3a3a3f;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            #InfoGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #a0a0a0;
                font-size: 11px;
            }
            #InfoLabel {
                color: #c0c0c0;
                font-size: 12px;
                font-family: "Consolas", monospace;
                padding: 2px 0;
            }
        """)
    
    def _show_placeholder(self):
        """Show placeholder, hide metadata groups."""
        self.placeholder_label.setVisible(True)
        self.format_group.setVisible(False)
        self.video_group.setVisible(False)
        self.audio_group.setVisible(False)
        self.subtitle_label.setVisible(False)
    
    def set_metadata(self, metadata: MediaMetadata):
        """
        Set and display metadata.
        
        Args:
            metadata: MediaMetadata object to display
        """
        self._metadata = metadata
        
        if not metadata:
            self._show_placeholder()
            return
        
        self.placeholder_label.setVisible(False)
        
        # Update format info
        self._update_format_info(metadata)
        
        # Update video info
        if metadata.has_video:
            self._update_video_info(metadata.primary_video)
            self.video_group.setVisible(True)
        else:
            self.video_group.setVisible(False)
        
        # Update audio info
        if metadata.has_audio:
            self._update_audio_info(metadata.primary_audio)
            self.audio_group.setVisible(True)
        else:
            self.audio_group.setVisible(False)
        
        # Update subtitle info
        if metadata.has_subtitles:
            self.subtitle_label.setText(f"Subtitles: {len(metadata.subtitle_streams)} track(s)")
            self.subtitle_label.setVisible(True)
        else:
            self.subtitle_label.setVisible(False)
    
    def _update_format_info(self, metadata: MediaMetadata):
        """Update format information display."""
        fmt = metadata.format
        
        self.filename_label.setText(f"Filename: {metadata.path.name}")
        self.format_label.setText(f"Format: {fmt.format_long_name}")
        self.duration_label.setText(f"Duration: {fmt.formatted_duration}")
        self.size_label.setText(f"Size: {fmt.size_mb:.1f} MB")
        
        if fmt.bit_rate:
            bitrate_mbps = fmt.bit_rate / 1_000_000
            self.bitrate_label.setText(f"Bitrate: {bitrate_mbps:.2f} Mbps")
        else:
            self.bitrate_label.setText("Bitrate: Unknown")
        
        self.format_group.setVisible(True)
    
    def _update_video_info(self, video):
        """Update video stream information."""
        self.video_codec_label.setText(f"Codec: {video.codec_name.upper()}")
        self.video_resolution_label.setText(f"Resolution: {video.resolution}")
        self.video_framerate_label.setText(f"Frame Rate: {video.frame_rate:.2f} fps")
        
        if video.pix_fmt:
            self.video_pixfmt_label.setText(f"Pixel Format: {video.pix_fmt}")
        else:
            self.video_pixfmt_label.setText("Pixel Format: -")
        
        if video.bit_rate:
            vbr_mbps = video.bit_rate / 1_000_000
            self.video_bitrate_label.setText(f"Bitrate: {vbr_mbps:.2f} Mbps")
        else:
            self.video_bitrate_label.setText("Bitrate: -")
    
    def _update_audio_info(self, audio):
        """Update audio stream information."""
        self.audio_codec_label.setText(f"Codec: {audio.codec_name.upper()}")
        self.audio_samplerate_label.setText(f"Sample Rate: {audio.sample_rate_khz:.1f} kHz")
        self.audio_channels_label.setText(f"Channels: {audio.channels} ({audio.channel_layout})")
        
        if audio.bit_rate:
            abr_kbps = audio.bit_rate / 1000
            self.audio_bitrate_label.setText(f"Bitrate: {abr_kbps:.0f} kbps")
        else:
            self.audio_bitrate_label.setText("Bitrate: -")
    
    def clear(self):
        """Clear all metadata display."""
        self._metadata = None
        self._show_placeholder()
