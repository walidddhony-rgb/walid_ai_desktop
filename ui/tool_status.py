"""Tool Status Widget - displays status of connected tools."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class ToolStatusWidget(QFrame):
    """Widget showing status of connected tools."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tool_statuses = {}
        self._init_ui()
    
    def _init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        title = QLabel("🔧 Tools")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_tool_status(self, tool_name: str, status: str):
        self.tool_statuses[tool_name] = status
        connected = sum(1 for s in self.tool_statuses.values() if s == 'connected')
        total = len(self.tool_statuses)
        self.status_label.setText(f"{connected}/{total} connected")
    
    def get_connected_tools(self) -> list:
        return [name for name, status in self.tool_statuses.items() if status == 'connected']
    
    def get_status_count(self, status: str) -> int:
        return sum(1 for s in self.tool_statuses.values() if s == status)
