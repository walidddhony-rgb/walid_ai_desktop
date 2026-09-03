"""
Knowledge Base Widget - Professional document management and indexing status display.

Features:
- Document list with status indicators (indexed, pending, error, processing)
- Progress tracking during indexing
- Drag & drop file addition
- Search/filter documents by name or path
- Document details (size, pages, added date, status)
- Bulk operations (add, clear all, rebuild index)
- Total storage size calculation
- Context menu for individual document management

Usage:
    from ui.knowledge_widget import KnowledgeBaseWidget, KnowledgeBasePanel
    
    widget = KnowledgeBaseWidget()
    widget.add_document("/path/to/doc.pdf", status="indexed")
    widget.update_progress(50, "processing.txt")
    
    panel = KnowledgeBasePanel()
    panel.set_total_documents(150)
    panel.set_total_size_mb(45.3)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QProgressBar, QMenu, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QGroupBox, QScrollArea, QFrame, QSplitter, QApplication, QStyle,
    QStyledItemDelegate, QStyleOptionViewItem, QAbstractItemView, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QSize, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPalette, QColor, QFont
from datetime import datetime
import os


class DocumentItemDelegate(QStyledItemDelegate):
    """Custom delegate for drawing document items with status colors."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_colors = {
            'indexed': QColor('#22c55e'),    # Green
            'pending': QColor('#eab308'),   # Yellow
            'error': QColor('#ef4444'),     # Red
            'processing': QColor('#3b82f6') # Blue
        }
    
    def paint(self, painter, option, index):
        painter.save()
        
        # Draw background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor('#e0e7ff'))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor('#f3f4f6'))
        else:
            # Alternating row colors
            if index.row() % 2 == 0:
                painter.fillRect(option.rect, QColor('#ffffff'))
            else:
                painter.fillRect(option.rect, QColor('#f9fafb'))
        
        # Draw status indicator
        status = index.data(Qt.ItemDataRole.UserRole)
        if status in self.status_colors:
            indicator_rect = option.rect.adjusted(4, 4, 0, -4)
            indicator_rect.setWidth(8)
            painter.setBrush(self.status_colors[status])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(indicator_rect, 2, 2)
        
        # Draw text
        text_rect = option.rect.adjusted(20, 0, -4, 0)
        painter.setPen(option.palette.color(QPalette.ColorRole.Text))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data())
        
        painter.restore()


class DocumentDetailsDialog(QDialog):
    """Dialog showing detailed document information."""
    
    def __init__(self, doc_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document Details")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("📄 Document Information")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Info form
        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # File name
        name_label = QLabel(doc_data.get('name', 'N/A'))
        name_label.setWordWrap(True)
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form_layout.addRow("<b>File Name:</b>", name_label)
        
        # File path
        path_label = QLabel(doc_data.get('path', 'N/A'))
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        form_layout.addRow("<b>Path:</b>", path_label)
        
        # File size
        size_str = doc_data.get('size', 0)
        if isinstance(size_str, (int, float)):
            size_str = self._format_size(size_str)
        form_layout.addRow("<b>Size:</b>", QLabel(size_str))
        
        # Page count
        pages = doc_data.get('pages', 'N/A')
        form_layout.addRow("<b>Pages:</b>", QLabel(str(pages)))
        
        # Added date
        added = doc_data.get('added_date', 'N/A')
        if isinstance(added, datetime):
            added = added.strftime("%Y-%m-%d %H:%M")
        form_layout.addRow("<b>Added:</b>", QLabel(added))
        
        # Status
        status = doc_data.get('status', 'unknown')
        status_display = {
            'indexed': '✅ Indexed',
            'pending': '⏳ Pending',
            'error': '❌ Error',
            'processing': '⚙ Processing'
        }.get(status, status)
        form_layout.addRow("<b>Status:</b>", QLabel(status_display))
        
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)
        
        # Spacer
        layout.addStretch()
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"


class KnowledgeBaseWidget(QWidget):
    """
    Enhanced Knowledge Base Widget with document management.
    
    Features:
    - Document list with status indicators
    - Search/filter functionality
    - Drag & drop support
    - Context menu with details
    - Progress tracking
    """
    
    # Signals
    add_documents_requested = pyqtSignal(list)      # List of file paths
    remove_document_requested = pyqtSignal(str)     # Single file path
    rebuild_index_requested = pyqtSignal()
    document_details_requested = pyqtSignal(dict)  # Document data dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.documents = {}  # path -> {name, path, size, pages, added_date, status}
        self._setup_ui()
        self._setup_drag_drop()
    
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📚 Knowledge Base")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.addWidget(title)
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search documents...")
        self.search_input.textChanged.connect(self._filter_documents)
        self.search_input.setMaximumWidth(250)
        header.addWidget(self.search_input)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Stats bar
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        self.doc_count_label = QLabel("📄 0 documents")
        self.doc_count_label.setStyleSheet("color: #374151; font-weight: 500;")
        stats_layout.addWidget(self.doc_count_label)
        
        self.size_label = QLabel("💾 0.0 MB total")
        self.size_label.setStyleSheet("color: #374151; font-weight: 500;")
        stats_layout.addWidget(self.size_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e5e7eb;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.progress_label)
        
        # Document list
        self.doc_list = QListWidget()
        self.doc_list.setAlternatingRowColors(True)
        self.doc_list.setItemDelegate(DocumentItemDelegate(self))
        self.doc_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_list.customContextMenuRequested.connect(self._show_context_menu)
        self.doc_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.doc_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #e0e7ff;
                color: #1e40af;
            }
            QListWidget::item:hover {
                background-color: #f3f4f6;
            }
        """)
        layout.addWidget(self.doc_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.add_btn = QPushButton("➕ Add Documents")
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.add_btn.setStyleSheet(self._btn_style("#3b82f6"))
        btn_layout.addWidget(self.add_btn)
        
        self.clear_btn = QPushButton("🗑 Clear All")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setStyleSheet(self._btn_style("#ef4444"))
        btn_layout.addWidget(self.clear_btn)
        
        self.rebuild_btn = QPushButton("🔄 Rebuild Index")
        self.rebuild_btn.clicked.connect(self._on_rebuild_clicked)
        self.rebuild_btn.setStyleSheet(self._btn_style("#8b5cf6"))
        btn_layout.addWidget(self.rebuild_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _setup_drag_drop(self):
        """Setup drag and drop support."""
        self.setAcceptDrops(True)
        self.doc_list.setAcceptDrops(True)
    
    def _btn_style(self, color):
        """Generate button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
        """
    
    def _filter_documents(self, text):
        """Filter document list based on search text."""
        search_text = text.lower().strip()
        
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            doc_path = item.data(Qt.ItemDataRole.UserRole + 1)
            
            if not search_text or search_text in item.text().lower() or search_text in doc_path.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
        
        # Update visible count
        visible_count = sum(1 for i in range(self.doc_list.count()) if not self.doc_list.item(i).isHidden())
        self.doc_count_label.setText(f"📄 {visible_count}/{len(self.documents)} documents")
    
    def _show_context_menu(self, pos: QPoint):
        """Show context menu for document item."""
        item = self.doc_list.itemAt(pos)
        if not item:
            return
        
        doc_path = item.data(Qt.ItemDataRole.UserRole + 1)
        doc_data = self.documents.get(doc_path, {})
        
        menu = QMenu(self)
        
        # View details
        details_action = menu.addAction("📄 View Details")
        details_action.triggered.connect(lambda: self._show_document_details(doc_data))
        
        menu.addSeparator()
        
        # Remove
        remove_action = menu.addAction("🗑 Remove")
        remove_action.triggered.connect(lambda: self.remove_document_requested.emit(doc_path))
        
        menu.exec(self.doc_list.mapToGlobal(pos))
    
    def _show_document_details(self, doc_data: dict):
        """Show document details dialog."""
        dialog = DocumentDetailsDialog(doc_data, self)
        dialog.exec()
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on document item."""
        doc_path = item.data(Qt.ItemDataRole.UserRole + 1)
        doc_data = self.documents.get(doc_path, {})
        self._show_document_details(doc_data)
    
    def _on_add_clicked(self):
        """Handle add button click."""
        from PyQt6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Documents",
            "",
            "All Supported (*.pdf *.txt *.docx *.md *.html);;PDF Files (*.pdf);;Text Files (*.txt);;Word Documents (*.docx);;Markdown (*.md);;HTML Files (*.html)"
        )
        
        if files:
            self.add_documents_requested.emit(files)
    
    def _on_clear_clicked(self):
        """Handle clear all button click."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Clear All Documents",
            f"Are you sure you want to remove all {len(self.documents)} documents from the knowledge base?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_documents()
    
    def _on_rebuild_clicked(self):
        """Handle rebuild index button click."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Rebuild Index",
            "This will delete the current index and rebuild it from scratch. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.rebuild_index_requested.emit()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.doc_list.setStyleSheet("""
                QListWidget {
                    background-color: #eff6ff;
                    border: 2px dashed #3b82f6;
                    border-radius: 8px;
                    padding: 4px;
                    font-size: 13px;
                }
            """)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.doc_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self.doc_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
        """)
        
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.pdf', '.txt', '.docx', '.md', '.html']:
                        files.append(file_path)
            
            if files:
                self.add_documents_requested.emit(files)
                event.acceptProposedAction()
    
    def add_document(self, file_path: str, status: str = 'pending', size: int = 0, pages: int = 0):
        """
        Add a document to the list.
        
        Args:
            file_path: Full path to the document
            status: Document status ('indexed', 'pending', 'error', 'processing')
            size: File size in bytes
            pages: Number of pages (if applicable)
        """
        if file_path in self.documents:
            return  # Already exists
        
        name = os.path.basename(file_path)
        
        # Store document data
        self.documents[file_path] = {
            'name': name,
            'path': file_path,
            'size': size,
            'pages': pages,
            'added_date': datetime.now(),
            'status': status
        }
        
        # Add to list
        item = QListWidgetItem(f"📄 {name}")
        item.setData(Qt.ItemDataRole.UserRole, status)
        item.setData(Qt.ItemDataRole.UserRole + 1, file_path)
        item.setToolTip(f"{name}\n{file_path}\nStatus: {status}")
        self.doc_list.addItem(item)
        
        self._update_stats()
    
    def update_document_status(self, file_path: str, status: str):
        """Update the status of an existing document."""
        if file_path not in self.documents:
            return
        
        self.documents[file_path]['status'] = status
        
        # Update list item
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == file_path:
                item.setData(Qt.ItemDataRole.UserRole, status)
                item.setToolTip(f"{item.text()}\nStatus: {status}")
                break
        
        self._update_stats()
    
    def remove_document(self, file_path: str):
        """Remove a document from the list."""
        if file_path not in self.documents:
            return
        
        del self.documents[file_path]
        
        # Remove from list
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == file_path:
                self.doc_list.takeItem(i)
                break
        
        self._update_stats()
    
    def clear_documents(self):
        """Clear all documents from the list."""
        self.documents.clear()
        self.doc_list.clear()
        self._update_stats()
    
    def _update_stats(self):
        """Update statistics labels."""
        count = len(self.documents)
        total_size = sum(doc.get('size', 0) for doc in self.documents.values())
        
        self.doc_count_label.setText(f"📄 {count} document{'s' if count != 1 else ''}")
        self.size_label.setText(f"💾 {self._format_size(total_size)} total")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def update_progress(self, progress: int, current_file: str = ""):
        """
        Update indexing progress.
        
        Args:
            progress: Progress percentage (0-100)
            current_file: Name of currently processing file
        """
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(progress)
        
        if current_file:
            self.progress_label.setText(f"Processing: {current_file} ({progress}%)")
        else:
            self.progress_label.setText(f"Indexing... ({progress}%)")
    
    def hide_progress(self):
        """Hide the progress bar."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
    
    def set_indexing_status(self, status: str):
        """
        Set the overall indexing status.
        
        Args:
            status: 'idle', 'indexing', 'success', 'error'
        """
        if status == 'indexing':
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Starting indexing...")
        elif status == 'success':
            self.hide_progress()
            # Optionally show success message
        elif status == 'error':
            self.hide_progress()
            # Optionally show error message
        else:
            self.hide_progress()


class KnowledgeBasePanel(QWidget):
    """
    Comprehensive Knowledge Base Panel with statistics and management.
    
    This panel combines the document list with overall statistics and controls.
    Suitable for use in a sidebar or dashboard.
    """
    
    add_documents_requested = pyqtSignal(list)
    remove_document_requested = pyqtSignal(str)
    rebuild_index_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the panel UI."""
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title = QLabel("📚 Knowledge Base")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #111827;")
        layout.addWidget(title)
        
        # Statistics group
        stats_group = QGroupBox("📊 Statistics")
        stats_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        stats_layout = QFormLayout()
        stats_layout.setSpacing(10)
        
        self.total_docs_label = QLabel("0")
        self.total_docs_label.setFont(QFont("Segoe UI", 11))
        stats_layout.addRow("Total Documents:", self.total_docs_label)
        
        self.total_size_label = QLabel("0.0 MB")
        self.total_size_label.setFont(QFont("Segoe UI", 11))
        stats_layout.addRow("Total Size:", self.total_size_label)
        
        self.indexed_label = QLabel("0")
        self.indexed_label.setFont(QFont("Segoe UI", 11))
        stats_layout.addRow("Indexed:", self.indexed_label)
        
        self.pending_label = QLabel("0")
        self.pending_label.setFont(QFont("Segoe UI", 11))
        stats_layout.addRow("Pending:", self.pending_label)
        
        self.error_label = QLabel("0")
        self.error_label.setFont(QFont("Segoe UI", 11))
        stats_layout.addRow("Errors:", self.error_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Document widget
        self.doc_widget = KnowledgeBaseWidget()
        self.doc_widget.doc_count_label.setVisible(False)
        self.doc_widget.size_label.setVisible(False)
        layout.addWidget(self.doc_widget)
        
        # Connect signals
        self.doc_widget.add_documents_requested.connect(self.add_documents_requested.emit)
        self.doc_widget.remove_document_requested.connect(self.remove_document_requested.emit)
        self.doc_widget.rebuild_index_requested.connect(self.rebuild_index_requested.emit)
        
        self.setLayout(layout)
    
    def set_total_documents(self, count: int):
        """Set total documents count."""
        self.total_docs_label.setText(str(count))
    
    def set_total_size_mb(self, size_mb: float):
        """Set total size in MB."""
        self.total_size_label.setText(f"{size_mb:.1f} MB")
    
    def set_indexed_count(self, count: int):
        """Set indexed documents count."""
        self.indexed_label.setText(str(count))
    
    def set_pending_count(self, count: int):
        """Set pending documents count."""
        self.pending_label.setText(str(count))
    
    def set_error_count(self, count: int):
        """Set error documents count."""
        self.error_label.setText(str(count))


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("Knowledge Base Widget - Enhanced Demo")
    window.setMinimumSize(800, 600)
    
    layout = QVBoxLayout()
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)
    
    # Title
    title = QLabel("📚 Knowledge Base Widget - Enhanced")
    title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)
    
    # Instructions
    instructions = QLabel(
        "Features:\n"
        "• Search/filter documents by name or path\n"
        "• Drag & drop files to add (PDF, TXT, DOCX, MD, HTML)\n"
        "• Double-click or right-click for document details\n"
        "• Progress tracking during indexing\n"
        "• Total size calculation\n"
        "• Status indicators (indexed, pending, error, processing)"
    )
    instructions.setStyleSheet("color: #6b7280; padding: 12px; background: #f9fafb; border-radius: 8px;")
    layout.addWidget(instructions)
    
    # Create widget
    kb_widget = KnowledgeBaseWidget()
    
    # Add sample documents
    sample_docs = [
        ("/docs/research_paper.pdf", "indexed", 2456789, 15),
        ("/docs/lecture_notes.txt", "indexed", 45678, 0),
        ("/docs/thesis_chapter1.docx", "processing", 1234567, 25),
        ("/docs/meeting_notes.md", "pending", 12345, 0),
        ("/docs/data_analysis.html", "error", 567890, 0),
        ("/docs/lab_report.pdf", "indexed", 3456789, 8),
    ]
    
    for path, status, size, pages in sample_docs:
        kb_widget.add_document(path, status=status, size=size, pages=pages)
    
    layout.addWidget(kb_widget)
    
    # Simulate progress
    def simulate_progress():
        kb_widget.set_indexing_status('indexing')
        
        timer = QTimer()
        progress = 0
        
        def update():
            nonlocal progress
            progress += 5
            if progress <= 100:
                kb_widget.update_progress(progress, "processing_file.pdf")
            else:
                timer.stop()
                kb_widget.hide_progress()
        
        timer.timeout.connect(update)
        timer.start(200)
    
    # Progress button
    progress_btn = QPushButton("🔄 Simulate Indexing Progress")
    progress_btn.clicked.connect(simulate_progress)
    progress_btn.setStyleSheet("""
        QPushButton {
            background-color: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #2563eb;
        }
    """)
    layout.addWidget(progress_btn)
    
    window.setLayout(layout)
    window.show()
    
    sys.exit(app.exec())
