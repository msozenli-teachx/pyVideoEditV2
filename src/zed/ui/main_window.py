"""
Main Window

The primary application window for Zed Video Editor.
Integrates all UI components with a dark theme dashboard layout.
"""

import os
import platform
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QStatusBar, QLabel, QFileDialog, QMessageBox,
    QTabWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont

from .widgets import (
    MediaPoolWidget,
    PreviewAreaWidget,
    ControlsPanelWidget,
    PresetsPanelWidget,
    MetadataPanelWidget,
    EnhancedTimelineWidget,
)
from .dialogs import ConcatDialog, AudioExtractDialog
from .controllers import PlaybackController

from zed.ffmpeg import FFmpegEngine, ProcessResult, get_preset
from zed.config import get_config


class MainWindow(QMainWindow):
    """
    Main Application Window for Zed Video Editor.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Zed Video Editor")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1400, 800)
        
        # Backend
        self._ffmpeg_engine = None
        self._current_video_path = None
        self._current_metadata = None
        
        # Playback controller
        self._playback_controller = None
        
        self._setup_ui()
        self._apply_styles()
        self._create_menus()
        self._connect_signals()
        self._wire_playback_controller()
    
    def _setup_ui(self):
        """Build the main window layout."""
        # Central widget
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main splitter (horizontal: left | center | right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("MainSplitter")
        main_splitter.setHandleWidth(2)
        
        # Left: Media Pool
        self.media_pool = MediaPoolWidget()
        self.media_pool.setObjectName("MediaPoolPanel")
        self.media_pool.setMinimumWidth(200)
        self.media_pool.setMaximumWidth(350)
        
        # Center: Preview Area
        self.preview = PreviewAreaWidget()
        self.preview.setObjectName("PreviewPanel")
        
        # Right: Tabbed panel
        self.right_panel = QTabWidget()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setMinimumWidth(250)
        self.right_panel.setMaximumWidth(350)
        
        # Properties tab
        self.properties_tab = QWidget()
        self.properties_tab.setObjectName("PropertiesTab")
        props_layout = QVBoxLayout(self.properties_tab)
        props_layout.setContentsMargins(12, 12, 12, 12)
        
        props_hint = QLabel("Select a clip on the timeline\nto edit properties")
        props_hint.setObjectName("HintLabel")
        props_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        props_layout.addWidget(props_hint)
        props_layout.addStretch()
        
        # Presets tab
        self.presets_panel = PresetsPanelWidget()
        self.presets_panel.setObjectName("PresetsPanel")
        
        # Metadata tab
        self.metadata_panel = MetadataPanelWidget()
        self.metadata_panel.setObjectName("MetadataPanel")
        
        # Add tabs
        self.right_panel.addTab(self.properties_tab, "Properties")
        self.right_panel.addTab(self.presets_panel, "Export Presets")
        self.right_panel.addTab(self.metadata_panel, "Media Info")
        
        # Add to main splitter
        main_splitter.addWidget(self.media_pool)
        main_splitter.addWidget(self.preview)
        main_splitter.addWidget(self.right_panel)
        
        # Set splitter sizes
        main_splitter.setSizes([250, 900, 300])
        
        main_layout.addWidget(main_splitter, stretch=1)
        
        # Enhanced Timeline
        self.timeline = EnhancedTimelineWidget()
        self.timeline.setObjectName("TimelinePanel")
        self.timeline.setMinimumHeight(250)
        self.timeline.setMaximumHeight(350)
        
        main_layout.addWidget(self.timeline)
        
        # Controls Panel
        self.controls = ControlsPanelWidget()
        self.controls.setObjectName("ControlsPanel")
        self.controls.setFixedHeight(60)
        
        main_layout.addWidget(self.controls)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.setObjectName("StatusBar")
        
        status_label = QLabel("Ready — Import media to begin")
        self.status_bar.addWidget(status_label)
        
        version_label = QLabel("Zed v0.1.0")
        version_label.setObjectName("VersionLabel")
        self.status_bar.addPermanentWidget(version_label)
    
    def _apply_styles(self):
        """Apply dark theme QSS stylesheet."""
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "dark_theme.qss")
        
        try:
            with open(qss_path, 'r') as f:
                qss = f.read()
            self.setStyleSheet(qss)
        except FileNotFoundError:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1a1a1e;
                    color: #e0e0e0;
                    font-family: "Segoe UI", sans-serif;
                }
            """)
        
        self.setStyleSheet(self.styleSheet() + """
            #CentralWidget {
                background-color: #1a1a1e;
            }
            #MainSplitter::handle {
                background-color: #2d2d32;
                width: 2px;
            }
            #MediaPoolPanel, #PreviewPanel {
                background-color: #1a1a1e;
            }
            #RightPanel {
                background-color: #1a1a1e;
            }
            #RightPanel::pane {
                border: none;
                background-color: #1a1a1e;
            }
            #RightPanel QTabBar::tab {
                background-color: #222226;
                color: #a0a0a0;
                padding: 8px 16px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            #RightPanel QTabBar::tab:selected {
                background-color: #1a1a1e;
                color: #e0e0e0;
                border-bottom: 2px solid #4a6fa5;
            }
            #RightPanel QTabBar::tab:hover:!selected {
                background-color: #2d2d32;
                color: #e0e0e0;
            }
            #VersionLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding-right: 8px;
            }
        """)
    
    def _create_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()
        menubar.setObjectName("MenuBar")
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        import_action = QAction("Import Media...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_requested)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # Export with preset submenu
        export_preset_menu = file_menu.addMenu("Export with Preset")
        
        presets = [
            ("YouTube 1080p", "youtube_1080p"),
            ("YouTube 4K", "youtube_4k"),
            ("High Quality", "high_quality"),
            ("Balanced", "balanced"),
            ("Web Optimized", "web_optimized"),
        ]
        for display_name, preset_name in presets:
            action = QAction(display_name, self)
            action.triggered.connect(lambda checked, p=preset_name: self._export_with_preset(p))
            export_preset_menu.addAction(action)
        
        export_action = QAction("Export Custom...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_custom)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        concat_action = QAction("Concatenate Videos...", self)
        concat_action.triggered.connect(self._on_concatenate)
        edit_menu.addAction(concat_action)
        
        edit_menu.addSeparator()
        
        extract_audio_action = QAction("Extract Audio...", self)
        extract_audio_action.triggered.connect(self._on_extract_audio)
        edit_menu.addAction(extract_audio_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        show_media_pool = QAction("Media Pool", self)
        show_media_pool.triggered.connect(lambda: self.media_pool.setVisible(True))
        view_menu.addAction(show_media_pool)
        
        show_timeline = QAction("Timeline", self)
        show_timeline.triggered.connect(lambda: self.timeline.setVisible(True))
        view_menu.addAction(show_timeline)
        
        show_presets = QAction("Export Presets", self)
        show_presets.triggered.connect(lambda: self.right_panel.setCurrentWidget(self.presets_panel))
        view_menu.addAction(show_presets)
        
        show_metadata = QAction("Media Info", self)
        show_metadata.triggered.connect(lambda: self.right_panel.setCurrentWidget(self.metadata_panel))
        view_menu.addAction(show_metadata)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About Zed", self._on_about)
    
    def _connect_signals(self):
        """Connect internal widget signals."""
        # Controls
        self.controls.start_changed.connect(self.controls.on_start_changed)
        self.controls.end_changed.connect(self.controls.on_end_changed)
        self.controls.process_requested.connect(self._on_process_requested)
        
        # Media pool
        self.media_pool.media_selected.connect(self._on_media_selected)
        self.media_pool.files_dropped.connect(self._on_files_dropped)
        
        # Presets panel
        self.presets_panel.export_requested.connect(self._on_preset_export)
        
        # Timeline
        self.timeline.clip_trimmed.connect(self._on_timeline_clip_trimmed)
        self.timeline.position_changed.connect(self._on_timeline_position_changed)
        self.timeline.clip_dropped.connect(self._on_timeline_clip_dropped)
        
        # Sync timeline play/pause with preview
        self.timeline.play_btn.clicked.connect(self._on_timeline_play_clicked)
    
    def _wire_playback_controller(self):
        """Create and wire the PlaybackController."""
        self._playback_controller = PlaybackController()
        
        # Controller -> Preview
        self._playback_controller.position_changed.connect(self.preview.on_position_update)
        self._playback_controller.playing_changed.connect(self.preview.set_playing)
        self._playback_controller.duration_changed.connect(self.preview.set_duration)
        
        # Controller -> Timeline
        self._playback_controller.position_changed.connect(
            lambda pos: self.timeline.set_position(pos)
        )
        self._playback_controller.duration_changed.connect(self.timeline.set_duration)
        
        # Preview -> Controller
        self.preview.play_requested.connect(self._playback_controller.play)
        self.preview.pause_requested.connect(self._playback_controller.pause)
        self.preview.stop_requested.connect(self._playback_controller.stop)
        self.preview.seek_requested.connect(
            lambda frac: self._playback_controller.seek_normalized(frac)
        )
    
    def _on_process_requested(self, start: float, end: float):
        """Handle Process button: clip video."""
        if not self._current_video_path:
            self.status_bar.showMessage("Please import a video first.", 3000)
            QMessageBox.warning(self, "No Video", "Please import a video before processing.")
            return
        
        if end <= start:
            self.status_bar.showMessage("End time must be greater than start time.", 3000)
            return
        
        self.status_bar.showMessage(f"Processing clip: {start:.2f}s → {end:.2f}s...", 0)
        
        try:
            engine = self._get_ffmpeg_engine()
            
            input_path = Path(self._current_video_path)
            output_dir = get_config().ffmpeg.default_output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{input_path.stem}_clip{input_path.suffix}"
            
            result = engine.clip_video(
                input_file=input_path,
                output_file=output_file,
                start_time=start,
                end_time=end,
            )
            
            if result.success:
                self.status_bar.showMessage(f"✓ Exported: {output_file}", 5000)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Clipped video saved to:\n{output_file}"
                )
            else:
                self.status_bar.showMessage(f"✗ Export failed: {result.error_message}", 5000)
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to process video:\n{result.error_message}"
                )
        
        except Exception as e:
            self.status_bar.showMessage(f"✗ Error: {e}", 5000)
            QMessageBox.critical(self, "Error", str(e))
    
    def _on_import_requested(self):
        """Open file dialog to import a video."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)"
        )
        
        if path:
            # Add to media pool (which will also load it)
            self.media_pool.add_media(path)
    
    def _on_files_dropped(self, paths: list):
        """Handle files dropped into media pool."""
        for path in paths:
            self._load_video_path(path)
    
    def _on_media_selected(self, path: str):
        """Handle media pool selection - load without re-adding to pool."""
        if path and Path(path).exists():
            self._load_video_without_adding(path)
    
    def _load_video_path(self, path: str):
        """Common handler to load a video path and add to pool."""
        self._load_video_without_adding(path)
        # Add to media pool (checks for duplicates)
        self.media_pool.add_media(path)
    
    def _load_video_without_adding(self, path: str):
        """Load video without adding to media pool (for existing items)."""
        self._current_video_path = path
        self.preview.load_video(path)
        self.status_bar.showMessage(f"Loaded: {Path(path).name}", 3000)
        
        # Inspect and display metadata
        try:
            from ...operations.metadata import MetadataInspector
            inspector = MetadataInspector()
            metadata = inspector.inspect(path)
            self.metadata_panel.set_metadata(metadata)
            
            # Switch to metadata tab
            self.right_panel.setCurrentWidget(self.metadata_panel)
            
            # Update timeline duration
            if metadata.format.duration:
                self.timeline.set_duration(metadata.format.duration)
                self._playback_controller.set_duration(metadata.format.duration)
                
                # Add a clip representation to the timeline
                self.timeline.add_clip_to_track(
                    0,  # Video track
                    Path(path).name,
                    0.0,  # Start at 0
                    metadata.format.duration
                )
                
                # Add waveform to audio track
                self.timeline.add_waveform_to_track(
                    1,  # Audio track
                    metadata.format.duration
                )
                
        except Exception as e:
            self.status_bar.showMessage(f"Could not read metadata: {e}", 3000)
    
    def _on_timeline_clip_trimmed(self, name: str, start: float, duration: float):
        """Handle clip trim from timeline."""
        self.status_bar.showMessage(
            f"Clip '{name}' trimmed: start={start:.2f}s, duration={duration:.2f}s", 
            3000
        )
        
        # Update controls to match
        self.controls.set_time_range(start, start + duration)
    
    def _on_timeline_position_changed(self, position: float):
        """Handle timeline position change - sync with preview and controller."""
        # Update playback controller
        self._playback_controller.seek(position)
        # Also seek the preview directly for immediate response
        self.preview.seek(position)
    
    def _on_timeline_play_clicked(self):
        """Handle timeline play/pause button - sync with preview."""
        if self.timeline._is_playing:
            self.preview.play()
        else:
            self.preview.pause()
    
    def _on_timeline_clip_dropped(self, path: str, time: float, track_index: int):
        """Handle clip dropped from media pool to timeline."""
        from zed import ZedApp
        
        try:
            # Get metadata for the dropped file
            app = ZedApp()
            metadata = app.inspect(path)
            duration = metadata.format.duration if metadata.format else 10.0
            
            # Add clip to the specified track at the drop time
            track_name = Path(path).name
            self.timeline.add_clip_to_track(
                track_index,
                track_name,
                time,  # Start at drop time
                duration
            )
            
            # If it's a video track (0), also add waveform to audio track
            if track_index == 0:
                self.timeline.add_waveform_to_track(1, duration)
            
            self.status_bar.showMessage(f"Added {track_name} to timeline at {time:.1f}s", 3000)
            
        except Exception as e:
            self.status_bar.showMessage(f"Could not add clip: {e}", 3000)
    
    def _on_preset_export(self, preset_name: str):
        """Handle export with preset."""
        self._export_with_preset(preset_name)
    
    def _export_with_preset(self, preset_name: str):
        """Export current video with selected preset."""
        if not self._current_video_path:
            QMessageBox.warning(self, "No Video", "Please import a video first.")
            return
        
        preset = get_preset(preset_name)
        if not preset:
            QMessageBox.warning(self, "Error", f"Preset not found: {preset_name}")
            return
        
        input_path = Path(self._current_video_path)
        ext = preset.get_file_extension()
        output_dir = get_config().ffmpeg.default_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{input_path.stem}_{preset_name}{ext}"
        
        self.status_bar.showMessage(f"Exporting with {preset.display_name}...", 0)
        
        try:
            engine = self._get_ffmpeg_engine()
            
            builder = engine.create_command()
            builder.input(input_path).output(output_file)
            preset.apply_to_builder(builder)
            builder.description(f"Export with {preset.display_name}")
            
            command = builder.build()
            result = engine.execute(command)
            
            if result.success:
                self.status_bar.showMessage(f"✓ Exported: {output_file.name}", 5000)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Video exported successfully!\n\nPreset: {preset.display_name}\nOutput: {output_file}"
                )
            else:
                self.status_bar.showMessage(f"✗ Export failed", 5000)
                QMessageBox.critical(self, "Export Failed", result.error_message)
                
        except Exception as e:
            self.status_bar.showMessage(f"✗ Error: {e}", 5000)
            QMessageBox.critical(self, "Error", str(e))
    
    def _on_export_custom(self):
        """Open presets panel for custom export."""
        self.right_panel.setCurrentWidget(self.presets_panel)
    
    def _on_concatenate(self):
        """Open concatenation dialog."""
        dialog = ConcatDialog(self, initial_file=self._current_video_path)
        dialog.exec()
    
    def _on_extract_audio(self):
        """Open audio extraction dialog."""
        dialog = AudioExtractDialog(self, input_file=self._current_video_path)
        dialog.exec()
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Zed Video Editor",
            """<h2>Zed Video Editor v0.1.0</h2>
            <p>A Python-based video editor built with PyQt6 and FFmpeg.</p>
            <p>Features:</p>
            <ul>
                <li>Video clipping and trimming</li>
                <li>Visual timeline with clip editing</li>
                <li>Audio waveform display</li>
                <li>Export presets for social media</li>
                <li>Video concatenation</li>
                <li>Audio extraction</li>
                <li>Metadata inspection</li>
            </ul>
            """
        )
    
    def _get_ffmpeg_engine(self):
        """Lazy-create the FFmpeg engine."""
        if self._ffmpeg_engine is None:
            self._ffmpeg_engine = FFmpegEngine()
        return self._ffmpeg_engine
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
