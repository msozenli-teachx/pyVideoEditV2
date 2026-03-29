"""
Controls Panel Widget

Bottom bar with start/end time inputs and process button.
Separated from backend - emits signals for processing.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox,
    QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ControlsPanelWidget(QWidget):
    """
    Controls Panel - Bottom bar for processing operations.
    
    Features:
    - Start time input (seconds)
    - End time input (seconds)
    - Process button (triggers operation)
    - Duration display
    
    Signals:
        process_requested: User clicked Process (start, end)
        start_changed: Start time value changed (float)
        end_changed: End time value changed (float)
    """
    
    process_requested = pyqtSignal(float, float)  # start, end
    start_changed = pyqtSignal(float)
    end_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the controls panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)
        
        # Time inputs group
        time_frame = QFrame()
        time_frame.setObjectName("TimeInputsFrame")
        time_layout = QHBoxLayout(time_frame)
        time_layout.setContentsMargins(12, 8, 12, 8)
        time_layout.setSpacing(12)
        
        # Start time
        start_label = QLabel("Start:")
        start_label.setObjectName("FieldLabel")
        
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setObjectName("TimeSpinBox")
        self.start_spin.setRange(0.0, 99999.0)
        self.start_spin.setDecimals(2)
        self.start_spin.setSuffix(" s")
        self.start_spin.setValue(0.0)
        self.start_spin.setFixedWidth(120)
        self.start_spin.valueChanged.connect(self.start_changed)
        
        # End time
        end_label = QLabel("End:")
        end_label.setObjectName("FieldLabel")
        
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setObjectName("TimeSpinBox")
        self.end_spin.setRange(0.0, 99999.0)
        self.end_spin.setDecimals(2)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(10.0)
        self.end_spin.setFixedWidth(120)
        self.end_spin.valueChanged.connect(self.end_changed)
        
        # Duration display
        self.duration_label = QLabel("Duration: 10.00 s")
        self.duration_label.setObjectName("DurationLabel")
        
        time_layout.addWidget(start_label)
        time_layout.addWidget(self.start_spin)
        time_layout.addSpacing(8)
        time_layout.addWidget(end_label)
        time_layout.addWidget(self.end_spin)
        time_layout.addSpacing(16)
        time_layout.addWidget(self.duration_label)
        time_layout.addStretch()
        
        layout.addWidget(time_frame)
        
        # Process button
        self.process_btn = QPushButton("▶ Process")
        self.process_btn.setObjectName("ProcessButton")
        self.process_btn.setFixedHeight(40)
        self.process_btn.setFixedWidth(140)
        self.process_btn.clicked.connect(self._on_process)
        
        layout.addWidget(self.process_btn)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #TimeInputsFrame {
                background-color: #222226;
                border: 1px solid #2d2d32;
                border-radius: 8px;
            }
            #FieldLabel {
                color: #a0a0a0;
                font-size: 12px;
                font-weight: 500;
            }
            #TimeSpinBox {
                background-color: #1e1e22;
                border: 1px solid #3a3a3f;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e0e0e0;
                font-family: "Consolas", monospace;
            }
            #TimeSpinBox:focus {
                border-color: #4a6fa5;
            }
            #DurationLabel {
                color: #6a6a6a;
                font-size: 11px;
                font-family: "Consolas", monospace;
            }
            #ProcessButton {
                background-color: #4a6fa5;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            #ProcessButton:hover {
                background-color: #5a7fb5;
            }
            #ProcessButton:pressed {
                background-color: #3a5f95;
            }
        """)
    
    def _on_process(self):
        """Handle process button click."""
        start = self.start_spin.value()
        end = self.end_spin.value()
        self.process_requested.emit(start, end)
    
    def get_time_range(self) -> tuple:
        """Get current start and end times."""
        return (self.start_spin.value(), self.end_spin.value())
    
    def set_time_range(self, start: float, end: float):
        """Set start and end times."""
        self.start_spin.setValue(start)
        self.end_spin.setValue(end)
        self._update_duration()
    
    def _update_duration(self):
        """Update duration label."""
        duration = self.end_spin.value() - self.start_spin.value()
        self.duration_label.setText(f"Duration: {duration:.2f} s")
    
    def on_start_changed(self, value: float):
        """Called when start changes."""
        self._update_duration()
    
    def on_end_changed(self, value: float):
        """Called when end changes."""
        self._update_duration()
