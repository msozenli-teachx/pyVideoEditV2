"""
Enhanced Timeline Widget

Main timeline widget with:
- Multi-track support with clip visualization
- Interactive playhead that can be dragged
- Zoom controls
- Time ruler with markers
- Clip selection and trimming
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSlider, QPushButton, QScrollArea, QFrame,
    QGraphicsView, QGraphicsScene, QGraphicsLineItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QMouseEvent, QDragEnterEvent, QDropEvent

from .timeline_track import TimelineTrackWidget


class TimelineRuler(QFrame):
    """Time ruler with second markers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 60.0
        self.pixels_per_second = 50
        self.setFixedHeight(30)
        self.setStyleSheet("background-color: #222226;")
    
    def set_duration(self, duration: float):
        self.duration = duration
        self.update()
    
    def set_zoom(self, pixels_per_second: float):
        self.pixels_per_second = pixels_per_second
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(34, 34, 38))
        
        # Draw time markers
        pen = QPen(QColor(150, 150, 150))
        pen.setWidth(1)
        painter.setPen(pen)
        
        font = QFont("Consolas", 9)
        painter.setFont(font)
        
        # Major markers every second
        for second in range(int(self.duration) + 1):
            x = second * self.pixels_per_second
            if x > self.width():
                break
            
            # Draw tick
            painter.drawLine(int(x), 20, int(x), 30)
            
            # Draw label every 5 seconds
            if second % 5 == 0:
                time_str = f"{second // 60:02d}:{second % 60:02d}"
                painter.drawText(int(x) + 4, 16, time_str)
        
        # Minor markers every 0.5 seconds
        pen.setColor(QColor(100, 100, 100))
        painter.setPen(pen)
        for half_second in range(int(self.duration * 2) + 1):
            if half_second % 2 == 0:
                continue
            x = half_second * self.pixels_per_second / 2
            if x > self.width():
                break
            painter.drawLine(int(x), 25, int(x), 30)
        
        painter.end()


class EnhancedTimelineWidget(QWidget):
    """
    Enhanced Timeline with clip visualization and editing.
    
    Signals:
        position_changed: Playhead position changed (float seconds)
        clip_selected: A clip was selected (str clip_name)
        clip_trimmed: A clip was trimmed (str clip_name, float new_start, float new_duration)
        duration_changed: Total duration changed
        clip_dropped: A clip was dropped from media pool (str path, float time, int track_index)
    """
    
    position_changed = pyqtSignal(float)
    clip_selected = pyqtSignal(str)
    clip_trimmed = pyqtSignal(str, float, float)
    duration_changed = pyqtSignal(float)
    clip_dropped = pyqtSignal(str, float, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._duration = 60.0
        self._position = 0.0
        self._pixels_per_second = 50
        self._is_playing = False
        self._is_dragging_playhead = False
        
        # Tracks
        self.tracks: list[TimelineTrackWidget] = []
        
        self._setup_ui()
        self._apply_styles()
        
        # Playback timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_playback_tick)
        self._timer.setInterval(33)  # ~30fps
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with title and zoom
        header = QHBoxLayout()
        
        title = QLabel("Timeline")
        title.setObjectName("TimelineTitle")
        header.addWidget(title)
        
        header.addStretch()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setObjectName("ZoomLabel")
        header.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 200)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        header.addWidget(self.zoom_slider)
        
        layout.addLayout(header)
        
        # Ruler
        self.ruler = TimelineRuler()
        layout.addWidget(self.ruler)
        
        # Tracks container with scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(2)
        
        # Create default tracks
        self.video_track = TimelineTrackWidget("Video 1", "video")
        self.video_track.clip_trimmed.connect(self._on_clip_trimmed)
        self.add_track(self.video_track)
        
        self.audio_track = TimelineTrackWidget("Audio 1", "audio")
        self.audio_track.clip_trimmed.connect(self._on_clip_trimmed)
        self.add_track(self.audio_track)
        
        self.scroll_area.setWidget(self.tracks_container)
        layout.addWidget(self.scroll_area)
        
        # Playhead overlay (drawn on top)
        self.playhead = QFrame(self)
        self.playhead.setObjectName("Playhead")
        self.playhead.setFixedWidth(2)
        self.playhead.setStyleSheet("background-color: #ff4444;")
        self.playhead.raise_()
        
        # Transport controls
        controls = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setObjectName("TransportButton")
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("TransportButton")
        self.stop_btn.clicked.connect(self.stop)
        
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setObjectName("TimeLabel")
        
        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()
        controls.addWidget(self.time_label)
        
        layout.addLayout(controls)
        
        # Enable mouse tracking for playhead dragging
        self.setMouseTracking(True)
        self.scroll_area.viewport().setMouseTracking(True)
        
        # Enable drag-drop for adding clips
        self.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)
        self.tracks_container.setAcceptDrops(True)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            #TimelineTitle {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
            }
            #ZoomLabel {
                color: #a0a0a0;
                font-size: 11px;
            }
            #TransportButton {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 16px;
                font-size: 12px;
            }
            #TransportButton:hover {
                background-color: #3a3a3f;
            }
            #TimeLabel {
                color: #a0a0a0;
                font-family: "Consolas", monospace;
                font-size: 12px;
                padding-right: 12px;
            }
        """)
    
    def add_track(self, track: TimelineTrackWidget):
        """Add a track to the timeline."""
        self.tracks.append(track)
        self.tracks_layout.addWidget(track)
    
    def add_clip_to_track(self, track_index: int, name: str, 
                          start_time: float, duration: float):
        """Add a clip to a specific track."""
        if 0 <= track_index < len(self.tracks):
            self.tracks[track_index].add_clip(name, start_time, duration)
    
    def add_waveform_to_track(self, track_index: int, duration: float):
        """Add audio waveform to a track."""
        if 0 <= track_index < len(self.tracks):
            self.tracks[track_index].add_waveform(duration)
    
    def set_duration(self, duration: float):
        """Set timeline duration."""
        self._duration = duration
        self.ruler.set_duration(duration)
        self.duration_changed.emit(duration)
        self._update_time_label()
    
    def set_position(self, position: float):
        """Set playhead position."""
        self._position = max(0, min(position, self._duration))
        self._update_playhead_position()
        self._update_time_label()
        self.position_changed.emit(self._position)
    
    def _update_playhead_position(self):
        """Update playhead visual position."""
        x = self._position * self._pixels_per_second
        # Account for ruler height and header
        self.playhead.setGeometry(int(x) + 120, 60, 2, 
                                  self.scroll_area.height() - 30)
    
    def _update_time_label(self):
        """Update time display."""
        current = self._format_time(self._position)
        total = self._format_time(self._duration)
        self.time_label.setText(f"{current} / {total}")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        m = int(seconds // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 100)
        return f"{m:02d}:{s:02d}:{ms:02d}"
    
    def _on_zoom_changed(self, value: int):
        """Handle zoom slider change."""
        self._pixels_per_second = value
        self.ruler.set_zoom(value)
        for track in self.tracks:
            track.set_zoom(value)
        self._update_playhead_position()
    
    def _on_clip_trimmed(self, name: str, start: float, duration: float):
        """Handle clip trim event."""
        self.clip_trimmed.emit(name, start, duration)
    
    def toggle_playback(self):
        """Toggle play/pause."""
        if self._is_playing:
            self.pause()
        else:
            self.play()
    
    def play(self):
        """Start playback."""
        self._is_playing = True
        self.play_btn.setText("⏸ Pause")
        self._timer.start()
    
    def pause(self):
        """Pause playback."""
        self._is_playing = False
        self.play_btn.setText("▶ Play")
        self._timer.stop()
    
    def stop(self):
        """Stop playback."""
        self._is_playing = False
        self.play_btn.setText("▶ Play")
        self._timer.stop()
        self.set_position(0)
    
    def _on_playback_tick(self):
        """Update position during playback."""
        self._position += 0.033  # ~30fps
        if self._position >= self._duration:
            self.stop()
        else:
            self._update_playhead_position()
            self._update_time_label()
            self.position_changed.emit(self._position)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for playhead dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is in timeline area
            pos = event.pos()
            if pos.y() > 60:  # Below ruler
                # Calculate time from x position
                track_x = pos.x() - 120  # Account for track header
                if track_x >= 0:
                    time = track_x / self._pixels_per_second
                    self._is_dragging_playhead = True
                    self.set_position(time)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for playhead dragging."""
        if self._is_dragging_playhead:
            track_x = event.pos().x() - 120
            if track_x >= 0:
                time = track_x / self._pixels_per_second
                self.set_position(time)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging_playhead = False
        super().mouseReleaseEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize."""
        super().resizeEvent(event)
        self._update_playhead_position()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter - accept media files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop - add clip to timeline at drop position."""
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        
        # Get drop position
        drop_pos = event.position()
        local_pos = self.tracks_container.mapFrom(self, drop_pos.toPoint())
        
        # Calculate time from x position (account for track header width)
        track_x = local_pos.x() - 120  # 120px header width
        if track_x < 0:
            track_x = 0
        drop_time = track_x / self._pixels_per_second
        
        # Determine track from y position
        track_height = 80  # Approximate track height
        track_index = local_pos.y() // track_height
        track_index = max(0, min(track_index, len(self.tracks) - 1))
        
        # Emit signal for each dropped file
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                self.clip_dropped.emit(path, drop_time, int(track_index))
        
        event.acceptProposedAction()
