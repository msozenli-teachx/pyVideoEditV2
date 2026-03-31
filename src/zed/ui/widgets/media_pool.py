"""
Media Pool Widget

Left panel for managing media files (import, browse, organize).
Handles drag-and-drop and proper file path management.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QFileDialog,
    QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent


class MediaPoolWidget(QWidget):
    """
    Media Pool Panel - Manages imported media files.
    
    Features:
    - Import button for adding media
    - Drag-and-drop file support
    - List view of media files with metadata
    - Context menu for operations
    - Proper file path storage
    
    Signals:
        import_requested: Emitted when user wants to import files
        media_selected: Emitted when a media item is selected (str path)
        media_double_clicked: Emitted on double-click (str path)
        files_dropped: Emitted when files are dropped (list of paths)
    """
    
    import_requested = pyqtSignal()
    media_selected = pyqtSignal(str)
    media_double_clicked = pyqtSignal(str)
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_files: dict[str, Path] = {}  # name -> Path mapping
        self._setup_ui()
        self._apply_styles()
        self._setup_drag_drop()
    
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
        self.import_btn.setToolTip("Import media files (Ctrl+I)")
        self.import_btn.clicked.connect(self._on_import_clicked)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.import_btn)
        
        layout.addLayout(header_layout)
        
        # Media list
        self.media_list = QListWidget()
        self.media_list.setObjectName("MediaList")
        self.media_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.media_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.media_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Connect signals
        self.media_list.itemClicked.connect(self._on_item_clicked)
        self.media_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.media_list.customContextMenuRequested.connect(self._on_context_menu)
        
        layout.addWidget(self.media_list, stretch=1)
        
        # Info label
        info = QLabel("Drag files here or click Import")
        info.setObjectName("HintLabel")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # File count label
        self.count_label = QLabel("0 files")
        self.count_label.setObjectName("CountLabel")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #MediaList {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
                padding: 4px;
                color: #e0e0e0;
            }
            #MediaList::item {
                padding: 10px 12px;
                border-radius: 4px;
                margin: 2px;
                color: #e0e0e0;
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
            #CountLabel {
                color: #6a6a6a;
                font-size: 10px;
                padding: 2px;
            }
        """)
    
    def _setup_drag_drop(self):
        """Set up drag and drop support."""
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
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
        """Handle file drop."""
        urls = event.mimeData().urls()
        paths = []
        
        for url in urls:
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if self._is_valid_media_file(path):
                    paths.append(str(path))
                    self.add_media(str(path))
        
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _is_valid_media_file(self, path: Path) -> bool:
        """Check if file is a valid media file."""
        valid_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', 
                          '.mp3', '.wav', '.aac', '.flac', '.m4a',
                          '.png', '.jpg', '.jpeg', '.gif', '.bmp'}
        return path.suffix.lower() in valid_extensions
    
    def _on_import_clicked(self):
        """Handle import button click."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Media Files",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;"
            "Audio Files (*.mp3 *.wav *.aac *.flac *.m4a);;"
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;"
            "All Media Files (*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.aac *.flac *.m4a *.png *.jpg *.jpeg *.gif *.bmp);;"
            "All Files (*)"
        )
        
        for file_path in files:
            self.add_media(file_path)
        
        if files:
            self.import_requested.emit()
    
    def add_media(self, path: str, display_name: str = None):
        """
        Add a media file to the pool.
        
        Args:
            path: Full path to the media file
            display_name: Optional display name (defaults to filename)
        """
        path_obj = Path(path)
        if not path_obj.exists():
            return
        
        # Check if this exact path already exists in the pool
        for existing_name, existing_path in self._media_files.items():
            if existing_path == path_obj:
                # Path already exists, just select it
                self.select_media(path)
                return
        
        # Use display name or filename
        name = display_name or path_obj.name
        
        # Check for name duplicates (same name, different path)
        if name in self._media_files:
            # Append number if duplicate
            base = path_obj.stem
            ext = path_obj.suffix
            counter = 1
            while name in self._media_files:
                name = f"{base}_{counter}{ext}"
                counter += 1
        
        # Store the path
        self._media_files[name] = path_obj
        
        # Determine icon based on file type
        icon = self._get_file_icon(path_obj.suffix)
        
        # Add to list
        item = QListWidgetItem(f"{icon} {name}")
        item.setData(Qt.ItemDataRole.UserRole, str(path_obj))
        item.setToolTip(f"{path_obj}\nClick to load, double-click to open")
        self.media_list.addItem(item)
        
        self._update_count()
    
    def _get_file_icon(self, extension: str) -> str:
        """Get emoji icon for file type."""
        ext = extension.lower()
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
        audio_exts = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.opus'}
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        
        if ext in video_exts:
            return "📹"
        elif ext in audio_exts:
            return "🎵"
        elif ext in image_exts:
            return "🖼️"
        else:
            return "📄"
    
    def remove_media(self, name: str):
        """Remove a media file from the pool."""
        if name in self._media_files:
            del self._media_files[name]
            
            # Find and remove from list
            for i in range(self.media_list.count()):
                item = self.media_list.item(i)
                if name in item.text():
                    self.media_list.takeItem(i)
                    break
            
            self._update_count()
    
    def clear_media(self):
        """Clear all media items."""
        self._media_files.clear()
        self.media_list.clear()
        self._update_count()
    
    def get_media_path(self, name: str) -> Path:
        """Get the full path for a media item."""
        return self._media_files.get(name)
    
    def get_all_media(self) -> list:
        """Get list of all media paths."""
        return [str(p) for p in self._media_files.values()]
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle media selection."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.media_selected.emit(path)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle media double-click."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.media_double_clicked.emit(path)
    
    def _on_context_menu(self, position):
        """Show context menu."""
        item = self.media_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d32;
                color: #e0e0e0;
                border: 1px solid #3a3a3f;
            }
            QMenu::item:selected {
                background-color: #4a6fa5;
            }
        """)
        
        load_action = menu.addAction("Load")
        remove_action = menu.addAction("Remove")
        menu.addSeparator()
        reveal_action = menu.addAction("Reveal in Folder")
        
        action = menu.exec(self.media_list.mapToGlobal(position))
        
        if action == load_action:
            self._on_item_clicked(item)
        elif action == remove_action:
            name = item.text().split(" ", 1)[1] if " " in item.text() else item.text()
            self.remove_media(name)
        elif action == reveal_action:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                self._reveal_in_folder(path)
    
    def _reveal_in_folder(self, path: str):
        """Open file manager to show the file."""
        import subprocess
        import platform
        
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["explorer", "/select,", path])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", path])
            else:  # Linux
                subprocess.run(["xdg-open", str(Path(path).parent)])
        except Exception:
            pass  # Silently fail if can't open folder
    
    def _update_count(self):
        """Update the file count label."""
        count = len(self._media_files)
        self.count_label.setText(f"{count} file{'s' if count != 1 else ''}")
    
    def select_media(self, path: str):
        """Select a media item by path."""
        for i in range(self.media_list.count()):
            item = self.media_list.item(i)
            item_path = item.data(Qt.ItemDataRole.UserRole)
            if item_path == path:
                self.media_list.setCurrentItem(item)
                break
