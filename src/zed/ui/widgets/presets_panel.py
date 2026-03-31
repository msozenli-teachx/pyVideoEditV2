"""
Export Presets Panel

Widget for selecting and configuring export presets.
Integrates with the backend preset system.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QTextEdit, QFrame, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...ffmpeg.presets import (
    get_preset_registry, PresetCategory, ExportPreset
)


class PresetsPanelWidget(QWidget):
    """
    Export Presets Panel - Allows users to select export presets.
    
    Signals:
        preset_selected: Emitted when a preset is selected (preset_name, preset)
        export_requested: Emitted when user clicks export (preset_name, output_path)
    """
    
    preset_selected = pyqtSignal(str, object)  # name, ExportPreset
    export_requested = pyqtSignal(str)  # preset_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._registry = get_preset_registry()
        self._current_preset: ExportPreset = None
        self._setup_ui()
        self._apply_styles()
        self._populate_categories()
    
    def _setup_ui(self):
        """Build the presets panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Export Presets")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Category selector
        category_layout = QHBoxLayout()
        category_label = QLabel("Category:")
        category_label.setObjectName("FieldLabel")
        
        self.category_combo = QComboBox()
        self.category_combo.setObjectName("CategoryCombo")
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo, stretch=1)
        layout.addLayout(category_layout)
        
        # Preset selector
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setObjectName("FieldLabel")
        
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("PresetCombo")
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo, stretch=1)
        layout.addLayout(preset_layout)
        
        # Preset details group
        details_group = QGroupBox("Preset Details")
        details_group.setObjectName("DetailsGroup")
        details_layout = QVBoxLayout(details_group)
        details_layout.setContentsMargins(12, 16, 12, 12)
        details_layout.setSpacing(8)
        
        # Description
        self.description_label = QLabel("Select a preset to see details")
        self.description_label.setObjectName("DescriptionLabel")
        self.description_label.setWordWrap(True)
        self.description_label.setMinimumHeight(40)
        details_layout.addWidget(self.description_label)
        
        # Technical specs
        specs_frame = QFrame()
        specs_frame.setObjectName("SpecsFrame")
        specs_layout = QVBoxLayout(specs_frame)
        specs_layout.setContentsMargins(8, 8, 8, 8)
        specs_layout.setSpacing(4)
        
        self.resolution_label = QLabel("Resolution: -")
        self.resolution_label.setObjectName("SpecLabel")
        
        self.codec_label = QLabel("Codecs: -")
        self.codec_label.setObjectName("SpecLabel")
        
        self.bitrate_label = QLabel("Bitrate: -")
        self.bitrate_label.setObjectName("SpecLabel")
        
        self.size_estimate_label = QLabel("Est. Size: -")
        self.size_estimate_label.setObjectName("SpecLabel")
        
        specs_layout.addWidget(self.resolution_label)
        specs_layout.addWidget(self.codec_label)
        specs_layout.addWidget(self.bitrate_label)
        specs_layout.addWidget(self.size_estimate_label)
        specs_layout.addStretch()
        
        details_layout.addWidget(specs_frame)
        layout.addWidget(details_group)
        
        # Export button
        self.export_btn = QPushButton("Export with Preset")
        self.export_btn.setObjectName("ExportButton")
        self.export_btn.setFixedHeight(40)
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
            }
            #FieldLabel {
                color: #a0a0a0;
                font-size: 11px;
                min-width: 60px;
            }
            #CategoryCombo, #PresetCombo {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 4px;
                color: #e0e0e0;
                padding: 6px 10px;
                font-size: 12px;
            }
            #CategoryCombo::drop-down, #PresetCombo::drop-down {
                border: none;
                width: 24px;
            }
            #CategoryCombo QAbstractItemView, #PresetCombo QAbstractItemView {
                background-color: #2d2d32;
                color: #e0e0e0;
                selection-background-color: #4a6fa5;
            }
            #DetailsGroup {
                color: #e0e0e0;
                font-weight: bold;
                border: 1px solid #3a3a3f;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            #DetailsGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #a0a0a0;
                font-size: 11px;
            }
            #DescriptionLabel {
                color: #c0c0c0;
                font-size: 12px;
                font-style: italic;
            }
            #SpecsFrame {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
            }
            #SpecLabel {
                color: #a0a0a0;
                font-size: 11px;
                font-family: "Consolas", monospace;
            }
            #ExportButton {
                background-color: #4a6fa5;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
            }
            #ExportButton:hover {
                background-color: #5a7fb5;
            }
            #ExportButton:pressed {
                background-color: #3a5f95;
            }
            #ExportButton:disabled {
                background-color: #3a3a3f;
                color: #6a6a6a;
            }
        """)
    
    def _populate_categories(self):
        """Populate category dropdown."""
        self.category_combo.clear()
        self.category_combo.addItem("All Categories", None)
        
        for category in self._registry.get_categories():
            display_name = category.value.replace('_', ' ').title()
            self.category_combo.addItem(display_name, category)
        
        # Select first real category to populate presets
        if self.category_combo.count() > 1:
            self.category_combo.setCurrentIndex(1)
    
    def _on_category_changed(self, text: str):
        """Handle category selection change."""
        category = self.category_combo.currentData()
        self._populate_presets(category)
    
    def _populate_presets(self, category=None):
        """Populate preset dropdown for selected category."""
        self.preset_combo.clear()
        self.preset_combo.addItem("Select a preset...", None)
        
        if category:
            presets = self._registry.get_by_category(category)
        else:
            presets = self._registry.get_all()
        
        for preset in sorted(presets, key=lambda p: p.display_name):
            self.preset_combo.addItem(preset.display_name, preset.name)
    
    def _on_preset_changed(self, text: str):
        """Handle preset selection change."""
        preset_name = self.preset_combo.currentData()
        
        if preset_name:
            self._current_preset = self._registry.get(preset_name)
            self._update_details(self._current_preset)
            self.preset_selected.emit(preset_name, self._current_preset)
            self.export_btn.setEnabled(True)
        else:
            self._current_preset = None
            self._clear_details()
            self.export_btn.setEnabled(False)
    
    def _update_details(self, preset: ExportPreset):
        """Update details display for selected preset."""
        self.description_label.setText(preset.description)
        
        # Resolution
        if preset.resolution:
            self.resolution_label.setText(f"Resolution: {preset.resolution}")
        else:
            self.resolution_label.setText("Resolution: Original")
        
        # Codecs
        video = preset.video_codec.value if preset.video_codec else "None"
        audio = preset.audio_codec.value if preset.audio_codec else "None"
        self.codec_label.setText(f"Video: {video} | Audio: {audio}")
        
        # Bitrate
        v_bitrate = preset.video_bitrate or "Auto"
        a_bitrate = preset.audio_bitrate or "Auto"
        self.bitrate_label.setText(f"V: {v_bitrate} | A: {a_bitrate}")
        
        # Size estimate
        if preset.estimated_file_size:
            self.size_estimate_label.setText(f"Est. Size: {preset.estimated_file_size}")
        else:
            self.size_estimate_label.setText("Est. Size: Varies")
    
    def _clear_details(self):
        """Clear details display."""
        self.description_label.setText("Select a preset to see details")
        self.resolution_label.setText("Resolution: -")
        self.codec_label.setText("Codecs: -")
        self.bitrate_label.setText("Bitrate: -")
        self.size_estimate_label.setText("Est. Size: -")
    
    def _on_export_clicked(self):
        """Handle export button click."""
        if self._current_preset:
            self.export_requested.emit(self._current_preset.name)
    
    def get_current_preset(self) -> ExportPreset:
        """Get currently selected preset."""
        return self._current_preset
    
    def select_preset(self, preset_name: str):
        """Select a preset by name programmatically."""
        preset = self._registry.get(preset_name)
        if preset:
            # Find and select the category
            category_index = self.category_combo.findData(preset.category)
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            # Find and select the preset
            preset_index = self.preset_combo.findData(preset_name)
            if preset_index >= 0:
                self.preset_combo.setCurrentIndex(preset_index)
