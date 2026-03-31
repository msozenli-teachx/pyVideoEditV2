"""
Audio Extraction Dialog

Dialog for extracting audio from video files.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QMessageBox, QProgressBar, QGroupBox,
    QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from ...operations.audio import AudioExtractor
from ...ffmpeg import ProcessResult, AudioCodec


class AudioExtractWorker(QThread):
    """Worker thread for audio extraction."""
    
    finished = pyqtSignal(object)  # ProcessResult
    error = pyqtSignal(str)
    
    def __init__(self, extractor: AudioExtractor, input_file, output_file, **kwargs):
        super().__init__()
        self.extractor = extractor
        self.input_file = input_file
        self.output_file = output_file
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.extractor.extract_audio(
                self.input_file, self.output_file, **self.kwargs
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AudioExtractDialog(QDialog):
    """
    Dialog for extracting audio from video files.
    
    Allows users to:
    - Select output format and codec
    - Configure bitrate and sample rate
    - Choose output location
    - Extract audio
    """
    
    def __init__(self, parent=None, input_file: str = None):
        super().__init__(parent)
        self.setWindowTitle("Extract Audio")
        self.setMinimumSize(500, 400)
        
        self.extractor = AudioExtractor()
        self.worker: AudioExtractWorker = None
        self.input_file = input_file
        
        self._setup_ui()
        self._apply_styles()
        self._populate_formats()
        
        # Set input file display
        if input_file:
            self.input_label.setText(f"Input: {Path(input_file).name}")
            self._auto_set_output()
    
    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Extract Audio")
        title.setObjectName("DialogTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Input file info
        self.input_label = QLabel("Input: No file selected")
        self.input_label.setObjectName("InputLabel")
        self.input_label.setWordWrap(True)
        layout.addWidget(self.input_label)
        
        # Options group
        options_group = QGroupBox("Export Options")
        options_group.setObjectName("OptionsGroup")
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(12, 16, 12, 12)
        options_layout.setSpacing(12)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Format:")
        format_label.setObjectName("FieldLabel")
        
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("FormatCombo")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo, stretch=1)
        options_layout.addLayout(format_layout)
        
        # Bitrate
        bitrate_layout = QHBoxLayout()
        bitrate_label = QLabel("Bitrate:")
        bitrate_label.setObjectName("FieldLabel")
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setObjectName("BitrateCombo")
        self.bitrate_combo.addItem("Auto", None)
        self.bitrate_combo.addItem("64 kbps", "64k")
        self.bitrate_combo.addItem("128 kbps", "128k")
        self.bitrate_combo.addItem("192 kbps", "192k")
        self.bitrate_combo.addItem("256 kbps", "256k")
        self.bitrate_combo.addItem("320 kbps", "320k")
        self.bitrate_combo.setCurrentIndex(3)  # 192k default
        
        bitrate_layout.addWidget(bitrate_label)
        bitrate_layout.addWidget(self.bitrate_combo, stretch=1)
        options_layout.addLayout(bitrate_layout)
        
        # Sample rate
        samplerate_layout = QHBoxLayout()
        samplerate_label = QLabel("Sample Rate:")
        samplerate_label.setObjectName("FieldLabel")
        
        self.samplerate_combo = QComboBox()
        self.samplerate_combo.setObjectName("SampleRateCombo")
        self.samplerate_combo.addItem("Auto", None)
        self.samplerate_combo.addItem("22.05 kHz", 22050)
        self.samplerate_combo.addItem("44.1 kHz", 44100)
        self.samplerate_combo.addItem("48 kHz", 48000)
        self.samplerate_combo.addItem("96 kHz", 96000)
        
        samplerate_layout.addWidget(samplerate_label)
        samplerate_layout.addWidget(self.samplerate_combo, stretch=1)
        options_layout.addLayout(samplerate_layout)
        
        # Channels
        channels_layout = QHBoxLayout()
        channels_label = QLabel("Channels:")
        channels_label.setObjectName("FieldLabel")
        
        self.channels_combo = QComboBox()
        self.channels_combo.setObjectName("ChannelsCombo")
        self.channels_combo.addItem("Auto", None)
        self.channels_combo.addItem("Mono (1)", 1)
        self.channels_combo.addItem("Stereo (2)", 2)
        
        channels_layout.addWidget(channels_label)
        channels_layout.addWidget(self.channels_combo, stretch=1)
        options_layout.addLayout(channels_layout)
        
        layout.addWidget(options_group)
        
        # Output file
        output_group = QGroupBox("Output")
        output_group.setObjectName("OutputGroup")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 16, 12, 12)
        
        output_file_layout = QHBoxLayout()
        
        self.output_edit = QLineEdit()
        self.output_edit.setObjectName("OutputEdit")
        self.output_edit.setPlaceholderText("Select output file...")
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setObjectName("BrowseButton")
        self.browse_btn.clicked.connect(self._on_browse_output)
        
        output_file_layout.addWidget(self.output_edit, stretch=1)
        output_file_layout.addWidget(self.browse_btn)
        output_layout.addLayout(output_file_layout)
        
        layout.addWidget(output_group)
        
        # Progress bar (hidden initially)
        self.progress = QProgressBar()
        self.progress.setObjectName("ProgressBar")
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.extract_btn = QPushButton("▶ Extract Audio")
        self.extract_btn.setObjectName("ExtractButton")
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._on_extract)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.extract_btn)
        layout.addLayout(btn_layout)
    
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
            #InputLabel {
                color: #a0a0a0;
                font-size: 12px;
                padding: 8px;
                background-color: #1e1e22;
                border-radius: 4px;
            }
            #OptionsGroup, #OutputGroup {
                color: #e0e0e0;
                font-weight: bold;
                border: 1px solid #3a3a3f;
                border-radius: 8px;
                margin-top: 8px;
            }
            #OptionsGroup::title, #OutputGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #a0a0a0;
                font-size: 11px;
            }
            #FieldLabel {
                color: #a0a0a0;
                font-size: 12px;
                min-width: 80px;
            }
            #FormatCombo, #BitrateCombo, #SampleRateCombo, #ChannelsCombo {
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
            #ExtractButton {
                background-color: #4a6fa5;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            #ExtractButton:hover {
                background-color: #5a7fb5;
            }
            #ExtractButton:disabled {
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
    
    def _populate_formats(self):
        """Populate format dropdown."""
        formats = [
            ("MP3", AudioCodec.MP3, ".mp3"),
            ("AAC", AudioCodec.AAC, ".m4a"),
            ("WAV", AudioCodec.PCM, ".wav"),
            ("FLAC", AudioCodec.FLAC, ".flac"),
            ("OGG Vorbis", AudioCodec.VORBIS, ".ogg"),
            ("Opus", AudioCodec.OPUS, ".opus"),
        ]
        
        for name, codec, ext in formats:
            self.format_combo.addItem(name, (codec, ext))
    
    def _on_format_changed(self, index):
        """Handle format selection change."""
        self._auto_set_output()
    
    def _auto_set_output(self):
        """Auto-set output filename based on input."""
        if not self.input_file:
            return
        
        data = self.format_combo.currentData()
        if data:
            _, ext = data
            input_path = Path(self.input_file)
            output_path = input_path.with_suffix(ext)
            self.output_edit.setText(str(output_path))
            self.extract_btn.setEnabled(True)
    
    def _on_browse_output(self):
        """Handle browse output button."""
        data = self.format_combo.currentData()
        ext_filter = "All Files (*)"
        default_ext = ".mp3"
        
        if data:
            _, default_ext = data
            codec_name = self.format_combo.currentText()
            ext_filter = f"{codec_name} Files (*{default_ext});;All Files (*)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio File",
            f"audio{default_ext}",
            ext_filter
        )
        if file_path:
            self.output_edit.setText(file_path)
            self.extract_btn.setEnabled(True)
    
    def _on_extract(self):
        """Handle extract button."""
        if not self.input_file:
            QMessageBox.warning(self, "Error", "No input file selected")
            return
        
        output = self.output_edit.text()
        if not output:
            QMessageBox.warning(self, "Error", "Please select output file")
            return
        
        # Get options
        data = self.format_combo.currentData()
        audio_codec = data[0] if data else AudioCodec.MP3
        
        bitrate = self.bitrate_combo.currentData()
        sample_rate = self.samplerate_combo.currentData()
        channels = self.channels_combo.currentData()
        
        kwargs = {'audio_codec': audio_codec}
        if bitrate:
            kwargs['audio_bitrate'] = bitrate
        if sample_rate:
            kwargs['sample_rate'] = sample_rate
        if channels:
            kwargs['channels'] = channels
        
        # Show progress
        self.progress.setVisible(True)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("Extracting...")
        
        # Run in worker thread
        self.worker = AudioExtractWorker(
            self.extractor, self.input_file, output, **kwargs
        )
        self.worker.finished.connect(self._on_extract_finished)
        self.worker.error.connect(self._on_extract_error)
        self.worker.start()
    
    def _on_extract_finished(self, result: ProcessResult):
        """Handle extraction completion."""
        self.progress.setVisible(False)
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("▶ Extract Audio")
        
        if result.success:
            QMessageBox.information(
                self,
                "Success",
                f"Audio extracted successfully!\n\nOutput: {result.output_file}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Extraction failed:\n{result.error_message}"
            )
    
    def _on_extract_error(self, error_msg: str):
        """Handle extraction error."""
        self.progress.setVisible(False)
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("▶ Extract Audio")
        
        QMessageBox.critical(
            self,
            "Error",
            f"Extraction failed:\n{error_msg}"
        )
