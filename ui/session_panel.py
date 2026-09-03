"""
Session Management Panel - Manage conversation sessions with save/load/delete functionality.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QFileDialog, QMessageBox, QFrame,
    QScrollArea, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import json
import os
from datetime import datetime


class SessionItemWidget(QFrame):
    """Widget representing a single session in the list."""
    
    load_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    
    def __init__(self, session_id: str, session_data: dict, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.session_data = session_data
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #f1f5f9;
                border-color: #cbd5e1;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        icon = QLabel("📁")
        icon.setFont(QFont("Segoe UI Emoji", 18))
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background-color: #e0f2fe; border-radius: 16px; padding: 4px;")
        layout.addWidget(icon)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name = self.session_data.get('name', 'Untitled Session')
        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #1e293b;")
        info_layout.addWidget(name_label)
        
        date_str = self.session_data.get('created_at', '')
        msg_count = len(self.session_data.get('messages', []))
        meta_label = QLabel(f"{msg_count} messages • {date_str}")
        meta_label.setFont(QFont("Segoe UI", 9))
        meta_label.setStyleSheet("color: #64748b;")
        info_layout.addWidget(meta_label)
        
        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        info_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(info_widget)
        
        load_btn = QPushButton("📂 Load")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setFixedSize(70, 28)
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        load_btn.clicked.connect(self._on_load_clicked)
        layout.addWidget(load_btn)
        
        delete_btn = QPushButton("🗑")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setFixedSize(32, 28)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #fef2f2; }
        """)
        delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
    
    def _on_load_clicked(self):
        self.load_clicked.emit(self.session_id)
    
    def _on_delete_clicked(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Delete Session")
        msg.setText(f"Are you sure you want to delete '{self.session_data.get('name', 'Untitled')}'?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: white; }
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
            QPushButton:default { background-color: #3b82f6; color: white; border: none; }
        """)
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_clicked.emit(self.session_id)


class SessionPanel(QScrollArea):
    """Panel for managing conversation sessions."""
    
    session_loaded = pyqtSignal(dict)
    session_deleted = pyqtSignal(str)
    session_created = pyqtSignal()
    
    def __init__(self, sessions_dir: str = "sessions", parent=None):
        super().__init__(parent)
        self.sessions_dir = sessions_dir
        self.sessions = {}
        self._ensure_sessions_dir()
        self._setup_ui()
        self.refresh_sessions()
    
    def _ensure_sessions_dir(self):
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QScrollArea { background-color: #ffffff; border: none; }")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container_layout.setSpacing(12)
        self.container.setLayout(self.container_layout)
        self.setWidget(self.container)
        
        self._build_header()
        self._build_session_list()
    
    def _build_header(self):
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #f8fafc; border-radius: 8px;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        
        title = QLabel("💾 Saved Sessions")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        new_btn = QPushButton("➕ New Session")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        new_btn.clicked.connect(self.session_created.emit)
        layout.addWidget(new_btn)
        
        header.setLayout(layout)
        self.container_layout.addWidget(header)
    
    def _build_session_list(self):
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout()
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.list_container.setLayout(self.list_layout)
        self.container_layout.addWidget(self.list_container)
    
    def refresh_sessions(self):
        self._load_sessions()
        self._rebuild_list()
    
    def _load_sessions(self):
        self.sessions = {}
        if not os.path.exists(self.sessions_dir):
            return
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                filepath = os.path.join(self.sessions_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.sessions[session_id] = data
                except Exception:
                    pass
    
    def _rebuild_list(self):
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.sessions:
            empty_label = QLabel("📭 No saved sessions yet\n\nStart a conversation and save it!")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setFont(QFont("Segoe UI", 11))
            empty_label.setStyleSheet("color: #94a3b8; padding: 40px;")
            self.list_layout.insertWidget(0, empty_label)
            return
        
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].get('created_at', ''),
            reverse=True
        )
        
        for session_id, session_data in sorted_sessions:
            widget = SessionItemWidget(session_id, session_data)
            widget.load_clicked.connect(self.session_loaded.emit)
            widget.delete_clicked.connect(self._on_session_delete)
            self.list_layout.insertWidget(self.list_layout.count() - 1, widget)
    
    def _on_session_delete(self, session_id: str):
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            del self.sessions[session_id]
            self.session_deleted.emit(session_id)
            self.refresh_sessions()
    
    def save_current_session(self, session_id: str, name: str, messages: list):
        session_data = {
            'id': session_id,
            'name': name,
            'messages': messages,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        self.refresh_sessions()
    
    def load_session(self, session_id: str) -> dict:
        if session_id in self.sessions:
            self.session_loaded.emit(self.sessions[session_id])
            return self.sessions[session_id]
        return None
    
    def get_session_count(self) -> int:
        return len(self.sessions)
    
    def search_sessions(self, query: str) -> list:
        results = []
        query_lower = query.lower()
        for session_id, data in self.sessions.items():
            if query_lower in data.get('name', '').lower():
                results.append((session_id, data))
        return results


class SessionPanelWithToolbar(QWidget):
    """Session panel with search and actions toolbar."""
    
    session_loaded = pyqtSignal(dict)
    session_deleted = pyqtSignal(str)
    session_created = pyqtSignal()
    search_changed = pyqtSignal(str)
    
    def __init__(self, sessions_dir: str = "sessions", parent=None):
        super().__init__(parent)
        self._setup_ui(sessions_dir)
    
    def _setup_ui(self, sessions_dir: str):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        self.panel = SessionPanel(sessions_dir)
        self.panel.session_loaded.connect(self.session_loaded.emit)
        self.panel.session_deleted.connect(self.session_deleted.emit)
        self.panel.session_created.connect(self.session_created.emit)
        layout.addWidget(self.panel)
        self.setLayout(layout)
    
    def _create_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet("background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        title = QLabel("📁 Sessions")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        self.count_label = QLabel("0 sessions")
        self.count_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.count_label)
        layout.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search sessions...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.search_changed.emit)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """)
        layout.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #3b82f6;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #eff6ff; }
        """)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_btn)
        
        toolbar.setLayout(layout)
        return toolbar
    
    def _on_refresh_clicked(self):
        self.panel.refresh_sessions()
        self.count_label.setText(f"{self.panel.get_session_count()} session{'s' if self.panel.get_session_count() != 1 else ''}")
    
    def refresh(self):
        self.panel.refresh_sessions()
        self.count_label.setText(f"{self.panel.get_session_count()} session{'s' if self.panel.get_session_count() != 1 else ''}")
    
    def get_panel(self) -> SessionPanel:
        return self.panel