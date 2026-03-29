"""
Media Pool Widget

Left panel for managing media files (import, browse, organize).
Separated from backend - just UI presentation for now.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont


class MediaPoolWidget(QWidget):
    """
    Media Pool Panel - Manages imported media files.
    
    Features:
    - Import button for adding media
    - List view of media files
    - Drag & drop ready (placeholder for future)
    - Context menu ready (placeholder for future)
    
    Signals:
        import_requested: Emitted when user wants to import files
        media_selected: Emitted when a media item is selected (str path)
    """
    
    import_requested = pyqtSignal()
    media_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the media pool UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Media Pool")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        
        # Import button
        self.import_btn = QPushButton("+ Import")
        self.import_btn.setObjectName("ImportButton")
        self.import_btn.setFixedHeight(28)
        self.import_btn.clicked.connect(self.import_requested)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.import_btn)
        
        layout.addLayout(header_layout)
        
        # Media list
        self.media_list = QListWidget()
        self.media_list.setObjectName("MediaList")
        self.media_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.media_list.itemClicked.connect(self._on_item_clicked)
        
        # Placeholder items (demo)
        demo_items = [
            "📹 sample_video_1.mp4",
            "📹 sample_video_2.mp4", 
            "🎵 background_music.wav",
            "🖼️  logo_overlay.png",
        ]
        for item_text in demo_items:
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, item_text)  # Store path
            self.media_list.addItem(item)
        
        layout.addWidget(self.media_list, stretch=1)
        
        # Info label
        info = QLabel("Drag files here or click Import")
        info.setObjectName("HintLabel")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
    
    def _apply_styles(self):
        """Apply inline styles specific to this widget."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #MediaList {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
                padding: 4px;
            }
            #MediaList::item {
                padding: 10px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            #MediaList::item:hover {
                background-color: #3a3a3f;
            }
            #MediaList::item:selected {
                background-color: #4a6fa5;
                color: #ffffff;
            }
            #ImportButton {
                background-color: #4a6fa5;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                font-weight: 500;
                padding: 0 12px;
            }
            #ImportButton:hover {
                background-color: #5a7fb5;
            }
            #HintLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding: 4px;
            }
        """)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle media selection."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.media_selected.emit(path)
    
    def add_media(self, path: str, display_name: str = None):
        """Add a media file to the pool."""
        display = display_name or path.split("/")[-1]
        item = QListWidgetItem(f"📄 {display}")
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.media_list.addItem(item)
    
    def clear_media(self):
        """Clear all media items."""
        self.media_list.clear()
