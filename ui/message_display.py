"""
Message Display Widget - Enhanced chat message rendering with Markdown support.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QTextEdit, QSizePolicy, QApplication, QToolTip, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import re


class CodeBlockWidget(QWidget):
    """Widget for displaying code blocks with syntax highlighting and copy button."""
    
    copy_clicked = pyqtSignal(str)
    
    def __init__(self, code: str, language: str = "", parent=None):
        super().__init__(parent)
        self.code = code
        self.language = language
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 4)
        
        if self.language:
            lang_label = QLabel(self.language.upper())
            lang_label.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            lang_label.setStyleSheet("color: #94a3b8; background: transparent;")
            header.addWidget(lang_label)
        
        header.addStretch()
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        copy_btn.clicked.connect(self._on_copy_clicked)
        header.addWidget(copy_btn)
        
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #1e293b; border-radius: 6px 6px 0 0;")
        header_widget.setLayout(header)
        layout.addWidget(header_widget)
        
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFont(QFont("Consolas", 11))
        self.code_display.setPlainText(self.code)
        self.code_display.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: none;
                border-radius: 0 0 6px 6px;
                padding: 12px;
            }
        """)
        
        line_count = self.code.count('\n') + 1
        max_lines = min(line_count, 20)
        font_height = self.code_display.fontMetrics().height()
        self.code_display.setFixedHeight(max_lines * font_height + 24)
        
        layout.addWidget(self.code_display)
        self.setLayout(layout)
    
    def _on_copy_clicked(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code)
        QToolTip.showText(self.mapToGlobal(self.code_display.pos()), "Copied!", self, QRect(), 1500)
        self.copy_clicked.emit(self.code)


class MessageBubble(QFrame):
    """Single message bubble with avatar and content."""
    
    copy_clicked = pyqtSignal(str)
    
    def __init__(self, content: str, role: str = "user", parent=None):
        super().__init__(parent)
        self.content = content
        self.role = role
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        avatar = QLabel()
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        
        if self.role == "user":
            avatar.setText("👤")
            avatar.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 18px;")
        else:
            avatar.setText("🤖")
            avatar.setStyleSheet("background-color: #10b981; color: white; border-radius: 18px;")
        
        layout.addWidget(avatar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        
        role_label = QLabel("You" if self.role == "user" else "Assistant")
        role_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        role_label.setStyleSheet("color: #64748b;")
        content_layout.addWidget(role_label)
        
        self.bubble = QFrame()
        self.bubble.setFrameStyle(QFrame.Shape.StyledPanel)
        bubble_layout = QVBoxLayout()
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(8)
        
        if self.role == "user":
            self.bubble.setStyleSheet("background-color: #eff6ff; border-radius: 12px; border: 1px solid #dbeafe;")
        else:
            self.bubble.setStyleSheet("background-color: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;")
        
        self._render_markdown(bubble_layout)
        
        if self.role == "assistant":
            copy_btn = QPushButton("📋 Copy")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setFixedSize(70, 24)
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #f1f5f9; color: #334155; }
            """)
            copy_btn.clicked.connect(self._on_copy_clicked)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(copy_btn)
            bubble_layout.addLayout(btn_layout)
        
        bubble_layout.addStretch()
        self.bubble.setLayout(bubble_layout)
        content_layout.addWidget(self.bubble)
        
        content_widget.setLayout(content_layout)
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(content_widget)
        self.setLayout(layout)
    
    def _render_markdown(self, layout: QVBoxLayout):
        blocks = self._split_into_blocks()
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            
            code_match = re.match(r'```(\w*)\n(.+?)```', block, re.DOTALL)
            if code_match:
                language = code_match.group(1)
                code = code_match.group(2).strip()
                code_widget = CodeBlockWidget(code, language)
                code_widget.copy_clicked.connect(self.copy_clicked.emit)
                layout.addWidget(code_widget)
            else:
                text_label = QLabel()
                text_label.setWordWrap(True)
                text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextBrowserInteraction)
                text_label.setFont(QFont("Segoe UI", 12))
                text_label.setStyleSheet("color: #1e293b; line-height: 1.6;")
                rich_text = self._markdown_to_html(block)
                text_label.setText(rich_text)
                layout.addWidget(text_label)
    
    def _split_into_blocks(self) -> list:
        blocks = []
        current_block = []
        in_code = False
        for line in self.content.split('\n'):
            if line.strip().startswith('```'):
                if current_block:
                    blocks.append('\n'.join(current_block))
                    current_block = []
                in_code = not in_code
                current_block.append(line)
            else:
                current_block.append(line)
        if current_block:
            blocks.append('\n'.join(current_block))
        return blocks
    
    def _markdown_to_html(self, text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'`(.+?)`', r'<code style="background:#f1f5f9;padding:2px 6px;border-radius:3px;font-family:Consolas,monospace;">\1</code>', text)
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color:#3b82f6;">\1</a>', text)
        text = text.replace('\n', '<br>')
        return text
    
    def _on_copy_clicked(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.content)
        QToolTip.showText(self.mapToGlobal(self.bubble.pos()), "Copied!", self, QRect(), 1500)
        self.copy_clicked.emit(self.content)


class MessageDisplay(QScrollArea):
    """Scrollable message display area with chat bubbles."""
    
    message_copied = pyqtSignal(str)
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container_layout.setSpacing(12)
        self.container_layout.addStretch()
        self.container.setLayout(self.container_layout)
        self.setWidget(self.container)
        self.setStyleSheet("QScrollArea { background-color: #ffffff; border: none; }")
        self.container.setObjectName("container")
    
    def add_message(self, content: str, role: str = "user"):
        self.messages.append((content, role))
        bubble = MessageBubble(content, role)
        bubble.copy_clicked.connect(self.message_copied.emit)
        self.container_layout.insertWidget(self.container_layout.count() - 1, bubble)
        self._scroll_to_bottom()
    
    def add_typing_indicator(self):
        indicator = QLabel("⏳ Assistant is typing...")
        indicator.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        indicator.setStyleSheet("color: #64748b; padding: 8px;")
        indicator.setObjectName("typing_indicator")
        self.container_layout.insertWidget(self.container_layout.count() - 1, indicator)
        self._scroll_to_bottom()
        return indicator
    
    def remove_typing_indicator(self, indicator: QLabel):
        indicator.deleteLater()
    
    def clear_messages(self):
        self.messages.clear()
        for i in range(self.container_layout.count() - 1):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.clear_requested.emit()
    
    def get_message_count(self) -> int:
        return len(self.messages)
    
    def get_conversation_text(self) -> str:
        lines = []
        for content, role in self.messages:
            role_name = "User" if role == "user" else "Assistant"
            lines.append(f"{role_name}: {content}")
        return '\n\n'.join(lines)
    
    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))
    
    def search_messages(self, query: str) -> list:
        results = []
        query_lower = query.lower()
        for i, (content, role) in enumerate(self.messages):
            if query_lower in content.lower():
                results.append((i, content, role))
        return results


class MessageDisplayWithToolbar(QWidget):
    """Message display with toolbar for actions."""
    
    message_copied = pyqtSignal(str)
    clear_requested = pyqtSignal()
    export_requested = pyqtSignal()
    search_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        self.display = MessageDisplay()
        self.display.message_copied.connect(self.message_copied.emit)
        self.display.clear_requested.connect(self.clear_requested.emit)
        layout.addWidget(self.display)
        self.setLayout(layout)
    
    def _create_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet("background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        title = QLabel("💬 Conversation")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        self.count_label = QLabel("0 messages")
        self.count_label.setStyleSheet("color: #64748b;")
        layout.addWidget(self.count_label)
        layout.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search...")
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
        
        clear_btn = QPushButton("🗑 Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #fef2f2; }
        """)
        clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("📥 Export")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(export_btn)
        
        toolbar.setLayout(layout)
        return toolbar
    
    def _on_clear_clicked(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Clear Conversation", "Are you sure you want to clear all messages?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.display.clear_messages()
            self.count_label.setText("0 messages")
    
    def add_message(self, content: str, role: str = "user"):
        self.display.add_message(content, role)
        count = self.display.get_message_count()
        self.count_label.setText(f"{count} message{'s' if count != 1 else ''}")
    
    def get_display(self) -> MessageDisplay:
        return self.display