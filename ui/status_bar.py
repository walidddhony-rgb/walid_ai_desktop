"""
Enhanced status bar for Walid AI Desktop.

Provides clear visual indicators for:
- Model connection status
- Token count
- Indexing status
- Tool execution status
- Error messages
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class StatusBar(QStatusBar):
    """Enhanced status bar with multiple sections for system status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        """Initialize status bar sections."""
        # Set fixed height for consistency
        self.setFixedHeight(28)
        
        # Section 1: Model status (left)
        self.model_label = QLabel("● Model: Disconnected")
        self.model_label.setToolTip("Current LLM model connection status")
        self.addWidget(self.model_label, 1)
        
        # Section 2: Token count (center-left)
        self.token_label = QLabel("Tokens: 0 / 24000")
        self.token_label.setToolTip("Current conversation token count")
        self.addWidget(self.token_label, 1)
        
        # Section 3: Indexing status (center-right)
        self.index_label = QLabel("Index: Idle")
        self.index_label.setToolTip("Knowledge base indexing status")
        self.addWidget(self.index_label, 1)
        
        # Section 4: Tool status (right)
        self.tool_label = QLabel("Tools: Ready")
        self.tool_label.setToolTip("Tool execution status")
        self.addWidget(self.tool_label, 1)
        
        # Section 5: Message area (far right, wider)
        self.message_label = QLabel("")
        self.message_label.setToolTip("System messages and notifications")
        self.addWidget(self.message_label, 2)
    
    def _apply_styles(self):
        """Apply consistent styling to all labels."""
        font = QFont("Segoe UI", 9)
        
        for label in [self.model_label, self.token_label, self.index_label, 
                      self.tool_label, self.message_label]:
            label.setFont(font)
            label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            label.setContentsMargins(8, 0, 8, 0)
    
    # Model Status Methods
    def set_model_connected(self, model_name: str = "Unknown"):
        """Set model status to connected (green)."""
        self.model_label.setText(f"● Model: {model_name}")
        self.model_label.setStyleSheet("color: #22c55e;")  # Green
        self.model_label.setToolTip(f"Connected to {model_name}")
    
    def set_model_disconnected(self):
        """Set model status to disconnected (red)."""
        self.model_label.setText("● Model: Disconnected")
        self.model_label.setStyleSheet("color: #ef4444;")  # Red
        self.model_label.setToolTip("Not connected to any model")
    
    def set_model_connecting(self):
        """Set model status to connecting (yellow)."""
        self.model_label.setText("● Model: Connecting...")
        self.model_label.setStyleSheet("color: #f59e0b;")  # Yellow
        self.model_label.setToolTip("Attempting to connect to model")
    
    # Token Count Methods
    def set_token_count(self, current: int, max_tokens: int = 24000):
        """Update token count display."""
        self.token_label.setText(f"Tokens: {current:,} / {max_tokens:,}")
        
        # Color based on usage
        usage_ratio = current / max_tokens
        if usage_ratio > 0.9:
            self.token_label.setStyleSheet("color: #ef4444;")  # Red - critical
        elif usage_ratio > 0.7:
            self.token_label.setStyleSheet("color: #f59e0b;")  # Yellow - warning
        else:
            self.token_label.setStyleSheet("color: #22c55e;")  # Green - normal
    
    # Indexing Status Methods
    def set_indexing_idle(self):
        """Set indexing status to idle."""
        self.index_label.setText("Index: Idle")
        self.index_label.setStyleSheet("color: #6b7280;")  # Gray
    
    def set_indexing_active(self, progress: int = 0):
        """Set indexing status to active."""
        if progress > 0:
            self.index_label.setText(f"Index: {progress}%")
        else:
            self.index_label.setText("Index: Active")
        self.index_label.setStyleSheet("color: #3b82f6;")  # Blue
    
    def set_indexing_error(self, error_msg: str = "Error"):
        """Set indexing status to error."""
        self.index_label.setText(f"Index: Error")
        self.index_label.setStyleSheet("color: #ef4444;")  # Red
        self.index_label.setToolTip(error_msg)
    
    # Tool Status Methods
    def set_tools_ready(self):
        """Set tool status to ready."""
        self.tool_label.setText("Tools: Ready")
        self.tool_label.setStyleSheet("color: #22c55e;")  # Green
    
    def set_tools_executing(self, tool_name: str = ""):
        """Set tool status to executing."""
        if tool_name:
            self.tool_label.setText(f"Tools: Executing {tool_name}")
        else:
            self.tool_label.setText("Tools: Executing...")
        self.tool_label.setStyleSheet("color: #3b82f6;")  # Blue
    
    def set_tools_error(self):
        """Set tool status to error."""
        self.tool_label.setText("Tools: Error")
        self.tool_label.setStyleSheet("color: #ef4444;")  # Red
    
    # Message Methods
    def show_message(self, message: str, duration: int = 5000):
        """Show a temporary message in the status bar."""
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #6b7280;")  # Gray
        
        if duration > 0:
            # Clear message after duration
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.message_label.setText(""))
    
    def show_error(self, error: str, duration: int = 10000):
        """Show an error message."""
        self.message_label.setText(f"⚠ {error}")
        self.message_label.setStyleSheet("color: #ef4444;")  # Red
        self.message_label.setToolTip(error)
        
        if duration > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.clear_message())
    
    def show_success(self, message: str, duration: int = 3000):
        """Show a success message."""
        self.message_label.setText(f"✓ {message}")
        self.message_label.setStyleSheet("color: #22c55e;")  # Green
        
        if duration > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(duration, lambda: self.clear_message())
    
    def clear_message(self):
        """Clear the message area."""
        self.message_label.setText("")
        self.message_label.setToolTip("")
    
    # Convenience Methods
    def reset_all(self):
        """Reset all status indicators to default state."""
        self.set_model_disconnected()
        self.set_token_count(0, 24000)
        self.set_indexing_idle()
        self.set_tools_ready()
        self.clear_message()
    
    def set_system_ready(self, model_name: str = "Unknown"):
        """Set all indicators to system ready state."""
        self.set_model_connected(model_name)
        self.set_token_count(0, 24000)
        self.set_indexing_idle()
        self.set_tools_ready()
        self.show_message("System ready", 2000)
