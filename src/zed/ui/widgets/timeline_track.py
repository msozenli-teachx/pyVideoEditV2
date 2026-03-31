"""
Timeline Track Widget with Clip Visualization

Enhanced track widget that displays clips with:
- Visual clip segments with thumbnails/names
- Drag handles for trimming in/out points
- Audio waveform display
- Selection and interaction
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QAbstractGraphicsShapeItem
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QMimeData,
    QTimer
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, 
    QDrag, QCursor, QLinearGradient, QFontMetrics
)


class TimelineClipItem(QGraphicsRectItem):
    """
    Visual representation of a clip on the timeline.
    
    Features:
    - Shows clip name and duration
    - Has trim handles on left/right edges
    - Can be selected and moved
    - Visual feedback for hover/selection
    """
    
    HANDLE_WIDTH = 8
    MIN_WIDTH = 40
    
    def __init__(self, name: str, start_time: float, duration: float, 
                 track_height: int, pixels_per_second: float, parent=None):
        super().__init__(parent)
        
        self.clip_name = name
        self.start_time = start_time
        self.duration = duration
        self.pixels_per_second = pixels_per_second
        self.track_height = track_height
        
        # Visual state
        self.is_selected = False
        self.hover_handle = None  # 'left', 'right', or None
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_start = 0
        self.drag_start_duration = 0
        
        # Colors
        self.color_normal = QColor(74, 111, 165)
        self.color_selected = QColor(90, 127, 181)
        self.color_hover = QColor(100, 137, 191)
        self.color_handle = QColor(200, 200, 200)
        self.color_handle_hover = QColor(255, 255, 255)
        
        # Set up the rectangle
        width = max(duration * pixels_per_second, self.MIN_WIDTH)
        self.setRect(0, 2, width, track_height - 4)
        self.setPos(start_time * pixels_per_second, 0)
        
        # Enable interactions
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        
        # Clip data
        self.source_in = 0.0  # Source media in point
        self.source_out = duration  # Source media out point
    
    def paint(self, painter: QPainter, option, widget=None):
        """Custom paint for clip with trim handles."""
        rect = self.rect()
        
        # Determine color based on state
        if self.is_selected:
            base_color = self.color_selected
        elif self.hover_handle:
            base_color = self.color_hover
        else:
            base_color = self.color_normal
        
        # Draw clip body with gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, base_color.lighter(110))
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(1, base_color.darker(110))
        
        painter.fillRect(rect, gradient)
        
        # Draw border
        pen = QPen(QColor(40, 40, 40))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(rect)
        
        # Draw trim handles if wide enough
        if rect.width() > self.MIN_WIDTH:
            handle_rect = QRectF(0, 2, self.HANDLE_WIDTH, rect.height())
            
            # Left handle
            left_color = self.color_handle_hover if self.hover_handle == 'left' else self.color_handle
            painter.fillRect(handle_rect, left_color)
            
            # Right handle
            right_rect = QRectF(rect.right() - self.HANDLE_WIDTH, 2, 
                               self.HANDLE_WIDTH, rect.height())
            right_color = self.color_handle_hover if self.hover_handle == 'right' else self.color_handle
            painter.fillRect(right_rect, right_color)
            
            # Draw handle indicators (lines)
            pen = QPen(QColor(60, 60, 60))
            pen.setWidth(1)
            painter.setPen(pen)
            
            # Left handle lines
            for x in [3, 5]:
                painter.drawLine(int(x), 8, int(x), int(rect.height() - 6))
            
            # Right handle lines
            for x in [rect.right() - 5, rect.right() - 3]:
                painter.drawLine(int(x), 8, int(x), int(rect.height() - 6))
        
        # Draw clip name
        if rect.width() > 60:
            painter.setPen(QPen(QColor(255, 255, 255)))
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            
            # Truncate name if needed
            metrics = QFontMetrics(font)
            text = metrics.elidedText(self.clip_name, Qt.TextElideMode.ElideRight, 
                                      int(rect.width() - 20))
            
            text_x = self.HANDLE_WIDTH + 4
            text_y = int(rect.height() / 2) + 4
            painter.drawText(text_x, text_y, text)
    
    def hoverMoveEvent(self, event):
        """Handle mouse hover to detect handle proximity."""
        x = event.pos().x()
        rect = self.rect()
        
        if x < self.HANDLE_WIDTH:
            self.hover_handle = 'left'
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif x > rect.width() - self.HANDLE_WIDTH:
            self.hover_handle = 'right'
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        else:
            self.hover_handle = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        self.update()
    
    def hoverLeaveEvent(self, event):
        """Handle mouse leaving the clip."""
        self.hover_handle = None
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection and drag initiation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selected = True
            self.is_dragging = True
            self.drag_start_x = event.scenePos().x()
            self.drag_start_start = self.start_time
            self.drag_start_duration = self.duration
            self.update()
        super().mousePressEvent(event)
    
    def update_from_drag(self, current_x: float, snap_times: list = None):
        """Update clip position/duration based on drag."""
        if not self.is_dragging:
            return
        
        delta_x = current_x - self.drag_start_x
        delta_time = delta_x / self.pixels_per_second
        
        if self.hover_handle == 'left':
            # Trimming left edge
            new_start = self.drag_start_start + delta_time
            new_duration = self.drag_start_duration - delta_time
            
            if new_duration >= 0.5:  # Minimum 0.5 second clip
                self.start_time = max(0, new_start)
                self.duration = new_duration
                self.setPos(self.start_time * self.pixels_per_second, 0)
                self.setRect(0, 2, max(self.duration * self.pixels_per_second, self.MIN_WIDTH), 
                           self.track_height - 4)
                
        elif self.hover_handle == 'right':
            # Trimming right edge
            new_duration = self.drag_start_duration + delta_time
            if new_duration >= 0.5:
                self.duration = max(0.5, new_duration)
                width = max(self.duration * self.pixels_per_second, self.MIN_WIDTH)
                self.setRect(0, 2, width, self.track_height - 4)
        
        self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
        super().mouseReleaseEvent(event)
    
    def get_time_range(self) -> tuple:
        """Get current start time and duration."""
        return (self.start_time, self.duration)


class WaveformItem(QGraphicsItem):
    """
    Audio waveform visualization using QPainter.
    
    Renders audio amplitude data as a waveform image.
    """
    
    def __init__(self, duration: float, track_height: int, 
                 pixels_per_second: float, parent=None):
        super().__init__(parent)
        
        self.duration = duration
        self.track_height = track_height
        self.pixels_per_second = pixels_per_second
        self.waveform_data = []  # List of amplitude values (0.0 to 1.0)
        self.channel_count = 2
        
        # Colors
        self.waveform_color = QColor(100, 150, 200, 180)
        self.waveform_fill = QColor(100, 150, 200, 60)
        self.center_line_color = QColor(80, 80, 80)
    
    def boundingRect(self):
        """Return bounding rectangle."""
        width = self.duration * self.pixels_per_second
        return QRectF(0, 0, width, self.track_height)
    
    def set_waveform_data(self, data: list):
        """Set waveform amplitude data."""
        self.waveform_data = data
        self.update()
    
    def generate_placeholder_data(self):
        """Generate placeholder waveform data for testing."""
        import random
        num_samples = int(self.duration * 10)  # 10 samples per second
        self.waveform_data = [random.uniform(0.1, 0.9) for _ in range(num_samples)]
        self.update()
    
    def paint(self, painter: QPainter, option, widget=None):
        """Paint the waveform."""
        if not self.waveform_data:
            # Draw placeholder text
            painter.setPen(QPen(QColor(100, 100, 100)))
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            painter.drawText(10, self.track_height // 2, "Audio waveform")
            return
        
        rect = self.boundingRect()
        width = rect.width()
        height = rect.height()
        center_y = height / 2
        
        # Draw center line
        pen = QPen(self.center_line_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(0, center_y, width, center_y)
        
        # Calculate bar width
        num_bars = len(self.waveform_data)
        bar_width = max(2, width / num_bars)
        
        # Draw waveform bars
        for i, amplitude in enumerate(self.waveform_data):
            x = i * bar_width
            bar_height = amplitude * (height - 10)
            
            # Draw mirrored waveform (top and bottom)
            pen = QPen(self.waveform_color)
            pen.setWidth(max(1, bar_width - 1))
            painter.setPen(pen)
            
            # Top half
            painter.drawLine(
                int(x + bar_width / 2), int(center_y - bar_height / 2),
                int(x + bar_width / 2), int(center_y)
            )
            
            # Bottom half
            painter.drawLine(
                int(x + bar_width / 2), int(center_y),
                int(x + bar_width / 2), int(center_y + bar_height / 2)
            )
            
            # Fill
            if bar_width > 3:
                fill_brush = QBrush(self.waveform_fill)
                painter.fillRect(
                    int(x), int(center_y - bar_height / 2),
                    int(bar_width) - 1, int(bar_height),
                    fill_brush
                )


class TimelineTrackWidget(QFrame):
    """
    Enhanced timeline track with clip visualization and audio waveforms.
    
    Signals:
        clip_trimmed: Emitted when a clip is trimmed (name, new_start, new_duration)
        clip_selected: Emitted when a clip is selected (name)
    """
    
    clip_trimmed = pyqtSignal(str, float, float)  # name, start, duration
    clip_selected = pyqtSignal(str)
    
    def __init__(self, name: str, track_type: str = "video", parent=None):
        super().__init__(parent)
        
        self.track_name = name
        self.track_type = track_type  # 'video', 'audio', or 'effect'
        self.track_height = 80 if track_type == "video" else 60
        self.pixels_per_second = 50  # Zoom level
        
        # Clips on this track
        self.clips: list[TimelineClipItem] = []
        self.waveform: WaveformItem = None
        
        # Scene setup
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setStyleSheet("background-color: #1e1e22;")
        self.view.setFixedHeight(self.track_height + 20)
        
        # Track header
        self.header = QLabel(f"{name}\n{track_type.upper()}")
        self.header.setFixedWidth(120)
        self.header.setFixedHeight(self.track_height)
        self.header.setStyleSheet("""
            background-color: #222226;
            color: #a0a0a0;
            border-right: 1px solid #2d2d32;
            padding: 8px;
            font-size: 11px;
        """)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.view, stretch=1)
        
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(self.track_height)
        
        # Enable drag tracking
        self.view.setMouseTracking(True)
        self.scene.setSceneRect(0, 0, 2000, self.track_height)
    
    def add_clip(self, name: str, start_time: float, duration: float):
        """Add a clip to this track."""
        clip = TimelineClipItem(name, start_time, duration, 
                               self.track_height, self.pixels_per_second)
        self.scene.addItem(clip)
        self.clips.append(clip)
        
        # Extend scene if needed
        clip_end = (start_time + duration) * self.pixels_per_second
        if clip_end > self.scene.width():
            self.scene.setSceneRect(0, 0, clip_end + 500, self.track_height)
    
    def add_waveform(self, duration: float):
        """Add audio waveform to this track."""
        self.waveform = WaveformItem(duration, self.track_height, 
                                     self.pixels_per_second)
        self.scene.addItem(self.waveform)
        self.waveform.generate_placeholder_data()
    
    def set_zoom(self, pixels_per_second: float):
        """Set zoom level (pixels per second)."""
        self.pixels_per_second = pixels_per_second
        for clip in self.clips:
            clip.pixels_per_second = pixels_per_second
            # Reposition clip
            clip.setPos(clip.start_time * pixels_per_second, 0)
            width = max(clip.duration * pixels_per_second, clip.MIN_WIDTH)
            clip.setRect(0, 2, width, self.track_height - 4)
        
        if self.waveform:
            self.waveform.pixels_per_second = pixels_per_second
            self.waveform.update()
    
    def update_clips_from_drag(self, pos: QPointF):
        """Update clips based on drag position."""
        for clip in self.clips:
            if clip.is_dragging:
                clip.update_from_drag(pos.x())
                self.clip_trimmed.emit(clip.clip_name, clip.start_time, clip.duration)
    
    def get_clips_in_range(self, start_time: float, end_time: float) -> list:
        """Get clips that overlap with the given time range."""
        result = []
        for clip in self.clips:
            clip_start = clip.start_time
            clip_end = clip.start_time + clip.duration
            if clip_start < end_time and clip_end > start_time:
                result.append(clip)
        return result
