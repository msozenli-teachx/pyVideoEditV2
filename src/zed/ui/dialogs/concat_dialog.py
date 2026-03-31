"""
Video Concatenation Dialog

Dialog for concatenating multiple video files.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QComboBox,
    QLineEdit, QMessageBox, QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from ...operations.concat import VideoConcatenator
from ...ffmpeg import ProcessResult


class ConcatWorker(QThread):
    """Worker thread for concatenation operation."""
    
    finished = pyqtSignal(object)  # ProcessResult
    error = pyqtSignal(str)
    
    def __init__(self, concatenator: VideoConcatenator, files, output, method):
        super().__init__()
        self.concatenator = concatenator
        self.files = files
        self.output = output
        self.method = method
    
    def run(self):
        try:
            result = self.concatenator.concat_files(
                self.files, self.output, method=self.method
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ConcatDialog(QDialog):
    """
    Dialog for concatenating multiple video files.
    
    Allows users to:
    - Add/remove/reorder video files
    - Select concatenation method (demuxer/filter)
    - Choose output location
    - Execute concatenation
    """
    
    def __init__(self, parent=None, initial_file: str = None):
        super().__init__(parent)
        self.setWindowTitle("Concatenate Videos")
        self.setMinimumSize(600, 500)
        
        self.concatenator = VideoConcatenator()
        self.worker: ConcatWorker = None
        
        self._setup_ui()
        self._apply_styles()
        
        # Add initial file if provided
        if initial_file:
            self._add_file(initial_file)
    
    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Video Concatenation")
        title.setObjectName("DialogTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Add videos in the order you want them concatenated.")
        desc.setObjectName("Description")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Files list group
        files_group = QGroupBox("Video Files")
        files_group.setObjectName("FilesGroup")
        files_layout = QVBoxLayout(files_group)
        files_layout.setContentsMargins(12, 16, 12, 12)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setObjectName("FileList")
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        files_layout.addWidget(self.file_list)
        
        # File buttons
        file_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+ Add Video")
        self.add_btn.setObjectName("ActionButton")
        self.add_btn.clicked.connect(self._on_add_file)
        
        self.remove_btn = QPushButton("- Remove")
        self.remove_btn.setObjectName("ActionButton")
        self.remove_btn.clicked.connect(self._on_remove_file)
        self.remove_btn.setEnabled(False)
        
        self.move_up_btn = QPushButton("↑ Move Up")
        self.move_up_btn.setObjectName("ActionButton")
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_up_btn.setEnabled(False)
        
        self.move_down_btn = QPushButton("↓ Move Down")
        self.move_down_btn.setObjectName("ActionButton")
        self.move_down_btn.clicked.connect(self._on_move_down)
        self.move_down_btn.setEnabled(False)
        
        file_btn_layout.addWidget(self.add_btn)
        file_btn_layout.addWidget(self.remove_btn)
        file_btn_layout.addWidget(self.move_up_btn)
        file_btn_layout.addWidget(self.move_down_btn)
        file_btn_layout.addStretch()
        
        files_layout.addLayout(file_btn_layout)
        layout.addWidget(files_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_group.setObjectName("OptionsGroup")
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(12, 16, 12, 12)
        
        # Method selection
        method_layout = QHBoxLayout()
        method_label = QLabel("Method:")
        method_label.setObjectName("FieldLabel")
        
        self.method_combo = QComboBox()
        self.method_combo.setObjectName("MethodCombo")
        self.method_combo.addItem("Fast (Stream Copy)", "demuxer")
        self.method_combo.addItem("Compatible (Re-encode)", "filter")
        
        method_info = QLabel("Fast requires same format/codecs")
        method_info.setObjectName("InfoLabel")
        
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        method_layout.addWidget(method_info)
        method_layout.addStretch()
        options_layout.addLayout(method_layout)
        
        # Output file
        output_layout = QHBoxLayout()
        output_label = QLabel("Output:")
        output_label.setObjectName("FieldLabel")
        
        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("OutputEdit")
        self.output_edit.setPlaceholderText("Select output file...")
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setObjectName("BrowseButton")
        self.browse_btn.clicked.connect(self._on_browse_output)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_edit, stretch=1)
        output_layout.addWidget(self.browse_btn)
        options_layout.addLayout(output_layout)
        
        layout.addWidget(options_group)
        
        # Progress bar (hidden initially)
        self.progress = QProgressBar()
        self.progress.setObjectName("ProgressBar")
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.concat_btn = QPushButton("▶ Concatenate")
        self.concat_btn.setObjectName("ConcatButton")
        self.concat_btn.setEnabled(False)
        self.concat_btn.clicked.connect(self._on_concatenate)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.concat_btn)
        layout.addLayout(btn_layout)
        
        # Connect list selection
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.file_list.model().rowsMoved.connect(self._update_button_states)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1e;
            }
            #DialogTitle {
                color: #e0e0e0;
                font-weight: bold;
            }
            #Description {
                color: #6a6a6a;
                font-size: 12px;
            }
            #FilesGroup, #OptionsGroup {
                color: #e0e0e0;
                font-weight: bold;
                border: 1px solid #3a3a3f;
                border-radius: 8px;
                margin-top: 8px;
            }
            #FilesGroup::title, #OptionsGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #a0a0a0;
                font-size: 11px;
            }
            #FileList {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 4px;
            }
            #FileList::item {
                padding: 8px;
                border-radius: 4px;
            }
            #FileList::item:selected {
                background-color: #4a6fa5;
            }
            #FileList::item:hover {
                background-color: #3a3a3f;
            }
            #ActionButton {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 12px;
                font-size: 12px;
            }
            #ActionButton:hover {
                background-color: #3a3a3f;
            }
            #FieldLabel {
                color: #a0a0a0;
                font-size: 12px;
                min-width: 60px;
            }
            #InfoLabel {
                color: #6a6a6a;
                font-size: 11px;
                font-style: italic;
            }
            #MethodCombo {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 4px 8px;
            }
            #OutputEdit {
                background-color: #1e1e22;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 10px;
            }
            #BrowseButton {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 12px;
            }
            #CancelButton {
                background-color: #3a3a3f;
                border: none;
                border-radius: 6px;
                color: #e0e0e0;
                padding: 8px 20px;
                font-size: 13px;
            }
            #ConcatButton {
                background-color: #4a6fa5;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            #ConcatButton:hover {
                background-color: #5a7fb5;
            }
            #ConcatButton:disabled {
                background-color: #3a3a3f;
                color: #6a6a6a;
            }
            #ProgressBar {
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                text-align: center;
                color: #e0e0e0;
            }
            #ProgressBar::chunk {
                background-color: #4a6fa5;
            }
        """)
    
    def _add_file(self, file_path: str):
        """Add a file to the list."""
        item = QListWidgetItem(f"{self.file_list.count() + 1}. {Path(file_path).name}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setToolTip(file_path)
        self.file_list.addItem(item)
        self._update_button_states()
    
    def _on_add_file(self):
        """Handle add file button."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)"
        )
        for file in files:
            self._add_file(file)
    
    def _on_remove_file(self):
        """Handle remove file button."""
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            self.file_list.takeItem(current_row)
            self._renumber_items()
            self._update_button_states()
    
    def _on_move_up(self):
        """Move selected item up."""
        current_row = self.file_list.currentRow()
        if current_row > 0:
            item = self.file_list.takeItem(current_row)
            self.file_list.insertItem(current_row - 1, item)
            self.file_list.setCurrentRow(current_row - 1)
            self._renumber_items()
    
    def _on_move_down(self):
        """Move selected item down."""
        current_row = self.file_list.currentRow()
        if current_row < self.file_list.count() - 1:
            item = self.file_list.takeItem(current_row)
            self.file_list.insertItem(current_row + 1, item)
            self.file_list.setCurrentRow(current_row + 1)
            self._renumber_items()
    
    def _renumber_items(self):
        """Renumber items after reordering."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{i + 1}. {Path(file_path).name}")
    
    def _on_selection_changed(self):
        """Handle list selection change."""
        self._update_button_states()
    
    def _update_button_states(self):
        """Update button enabled states."""
        count = self.file_list.count()
        has_selection = self.file_list.currentRow() >= 0
        
        self.remove_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and self.file_list.currentRow() > 0)
        self.move_down_btn.setEnabled(has_selection and self.file_list.currentRow() < count - 1)
        
        # Enable concat button if we have 2+ files and output path
        has_output = bool(self.output_edit.text())
        self.concat_btn.setEnabled(count >= 2 and has_output)
    
    def _on_browse_output(self):
        """Handle browse output button."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Concatenated Video",
            "concatenated.mp4",
            "MP4 Video (*.mp4);;MKV Video (*.mkv);;MOV Video (*.mov);;All Files (*)"
        )
        if file_path:
            self.output_edit.setText(file_path)
            self._update_button_states()
    
    def _on_concatenate(self):
        """Handle concatenate button."""
        # Get all files
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            files.append(item.data(Qt.ItemDataRole.UserRole))
        
        output = self.output_edit.text()
        method = self.method_combo.currentData()
        
        # Show progress
        self.progress.setVisible(True)
        self.concat_btn.setEnabled(False)
        self.concat_btn.setText("Processing...")
        
        # Run in worker thread
        self.worker = ConcatWorker(self.concatenator, files, output, method)
        self.worker.finished.connect(self._on_concat_finished)
        self.worker.error.connect(self._on_concat_error)
        self.worker.start()
    
    def _on_concat_finished(self, result: ProcessResult):
        """Handle concatenation completion."""
        self.progress.setVisible(False)
        self.concat_btn.setEnabled(True)
        self.concat_btn.setText("▶ Concatenate")
        
        if result.success:
            QMessageBox.information(
                self,
                "Success",
                f"Videos concatenated successfully!\n\nOutput: {result.output_file}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Concatenation failed:\n{result.error_message}"
            )
    
    def _on_concat_error(self, error_msg: str):
        """Handle concatenation error."""
        self.progress.setVisible(False)
        self.concat_btn.setEnabled(True)
        self.concat_btn.setText("▶ Concatenate")
        
        QMessageBox.critical(
            self,
            "Error",
            f"Concatenation failed:\n{error_msg}"
        )
    
    def get_files(self) -> list:
        """Get list of files to concatenate."""
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            files.append(item.data(Qt.ItemDataRole.UserRole))
        return files
