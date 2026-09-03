"""
Tool Execution Status Widget for Walid AI Desktop.

Provides clear visual feedback during tool execution:
- Tool name and description
- Progress indicator
- Status (pending, executing, success, error)
- Expandable output
- Execution time
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame, QScrollArea, QTextEdit, QSizePolicy,
    QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QFont, QColor


class ToolStatusWidget(QWidget):
    """Widget displaying tool execution status with progress."""
    
    # Signals
    cancel_requested = pyqtSignal()  # Emitted when user clicks cancel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._reset_state()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Set frame style
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ToolStatusWidget {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        
        # Header: Tool name + status icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Status icon
        self.status_icon = QLabel("⏳")
        self.status_icon.setFont(QFont("Segoe UI", 16))
        header_layout.addWidget(self.status_icon)
        
        # Tool name
        self.tool_name_label = QLabel("Waiting for tool execution...")
        self.tool_name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.tool_name_label.setWordWrap(True)
        header_layout.addWidget(self.tool_name_label, 1)
        
        # Execution time
        self.time_label = QLabel("0.0s")
        self.time_label.setFont(QFont("Segoe UI", 9))
        self.time_label.setStyleSheet("color: #6b7280;")
        header_layout.addWidget(self.time_label)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate by default
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e5e7eb;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Description
        self.description_label = QLabel("")
        self.description_label.setFont(QFont("Segoe UI", 9))
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #6b7280;")
        layout.addWidget(self.description_label)
        
        # Output area (collapsible)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(150)
        self.output_area.setFont(QFont("Consolas", 9))
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: #1f2937;
                color: #f3f4f6;
                border: 1px solid #374151;
                border-radius: 4px;
            }
        """)
        self.output_area.hide()  # Hidden by default
        layout.addWidget(self.output_area)
        
        # Footer: Status + actions
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        
        # Status text
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 9))
        footer_layout.addWidget(self.status_label)
        
        # Spacer
        footer_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Show output button
        self.show_output_btn = QPushButton("📄 Show Output")
        self.show_output_btn.setFixedHeight(28)
        self.show_output_btn.clicked.connect(self._toggle_output)
        self.show_output_btn.hide()  # Hidden until there's output
        footer_layout.addWidget(self.show_output_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setFixedHeight(28)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.hide()  # Hidden when not executing
        footer_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(footer_layout)
    
    def _reset_state(self):
        """Reset widget to initial state."""
        self.status_icon.setText("⏳")
        self.tool_name_label.setText("Waiting for tool execution...")
        self.description_label.setText("")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #6b7280;")
        self.time_label.setText("0.0s")
        self.output_area.clear()
        self.output_area.hide()
        self.show_output_btn.hide()
        self.cancel_btn.hide()
        self.timer = QElapsedTimer()
    
    def start_execution(self, tool_name: str, description: str = ""):
        """Start tool execution display."""
        self._reset_state()
        
        self.status_icon.setText("⚙")
        self.tool_name_label.setText(f"Executing: {tool_name}")
        self.description_label.setText(description if description else "")
        self.status_label.setText("Executing...")
        self.status_label.setStyleSheet("color: #3b82f6;")
        self.cancel_btn.show()
        
        self.timer.start()
    
    def update_progress(self, progress: int, status_text: str = ""):
        """Update progress bar and status."""
        if progress >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
        
        if status_text:
            self.status_label.setText(status_text)
        
        # Update elapsed time
        elapsed = self.timer.elapsed() / 1000.0
        self.time_label.setText(f"{elapsed:.1f}s")
    
    def set_success(self, output: str = "", duration: float = None):
        """Mark execution as successful."""
        self.status_icon.setText("✅")
        self.status_label.setText("Completed successfully")
        self.status_label.setStyleSheet("color: #22c55e;")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.cancel_btn.hide()
        
        if duration:
            self.time_label.setText(f"{duration:.1f}s")
        else:
            elapsed = self.timer.elapsed() / 1000.0
            self.time_label.setText(f"{elapsed:.1f}s")
        
        if output:
            self.output_area.setPlainText(output)
            self.show_output_btn.show()
    
    def set_error(self, error_message: str, duration: float = None):
        """Mark execution as failed."""
        self.status_icon.setText("❌")
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: #ef4444;")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.cancel_btn.hide()
        
        if duration:
            self.time_label.setText(f"{duration:.1f}s")
        else:
            elapsed = self.timer.elapsed() / 1000.0
            self.time_label.setText(f"{elapsed:.1f}s")
        
        self.output_area.setPlainText(f"Error:\n{error_message}")
        self.show_output_btn.show()
    
    def _toggle_output(self):
        """Toggle output area visibility."""
        if self.output_area.isVisible():
            self.output_area.hide()
            self.show_output_btn.setText("📄 Show Output")
        else:
            self.output_area.show()
            self.show_output_btn.setText("📄 Hide Output")
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.cancel_requested.emit()
        self.status_label.setText("Cancelled")
        self.status_label.setStyleSheet("color: #f59e0b;")
        self.cancel_btn.hide()


class ToolExecutionHistory(QWidget):
    """Widget showing history of tool executions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        title = QLabel("📜 Tool History")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Scroll area for history items
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setSpacing(4)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll.setWidget(self.history_container)
        layout.addWidget(self.scroll)
        
        # Clear button
        clear_btn = QPushButton("🗑 Clear History")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self.clear_history)
        layout.addWidget(clear_btn)
        
        self.executions = []
    
    def add_execution(self, tool_name: str, status: str, duration: float):
        """Add execution to history."""
        item = QWidget()
        item.setStyleSheet("""
            QWidget {
                background-color: #f3f4f6;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(item)
        layout.setSpacing(8)
        
        # Status icon
        icon = "✅" if status == "success" else "❌"
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(icon_label)
        
        # Tool name
        name_label = QLabel(tool_name)
        name_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(name_label, 1)
        
        # Duration
        duration_label = QLabel(f"{duration:.1f}s")
        duration_label.setFont(QFont("Segoe UI", 8))
        duration_label.setStyleSheet("color: #6b7280;")
        layout.addWidget(duration_label)
        
        self.history_layout.addWidget(item)
        self.executions.append(item)
        
        # Keep only last 10
        if len(self.executions) > 10:
            old_item = self.history_layout.takeAt(0).widget()
            old_item.deleteLater()
            self.executions.pop(0)
    
    def clear_history(self):
        """Clear all history."""
        for item in self.executions:
            item.deleteLater()
        self.executions.clear()


# Quick test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    widget = ToolStatusWidget()
    widget.resize(500, 200)
    widget.show()
    
    # Simulate execution
    import time
    widget.start_execution("read_file", "Reading document.txt...")
    
    for i in range(0, 101, 10):
        widget.update_progress(i, f"Reading... {i}%")
        time.sleep(0.1)
        app.processEvents()
    
    widget.set_success("File content:\nHello, World!", duration=1.5)
    
    sys.exit(app.exec())
