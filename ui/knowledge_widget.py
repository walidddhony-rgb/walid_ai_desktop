"""
Knowledge Base Status Widget for Walid AI Desktop.

Provides comprehensive knowledge base dashboard:
- Indexed documents count
- Indexing progress bar
- Document list with status
- Add/remove documents
- Index size and storage info
- Rebuild index option
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QSizePolicy, QSpacerItem, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon


class KnowledgeBaseWidget(QWidget):
    """Comprehensive knowledge base dashboard widget."""
    
    # Signals
    add_documents_requested = pyqtSignal(list)  # Emitted when user adds documents
    remove_document_requested = pyqtSignal(str)  # Emitted when user removes a document
    rebuild_index_requested = pyqtSignal()  # Emitted when user requests index rebuild
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._reset_state()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Set frame style
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            KnowledgeBaseWidget {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("📚 Knowledge Base")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        # Spacer
        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Add button
        self.add_btn = QPushButton("➕ Add Documents")
        self.add_btn.setFixedHeight(32)
        self.add_btn.clicked.connect(self._on_add_documents)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        # Documents count
        self.docs_count_label = QLabel("📄 0 documents")
        self.docs_count_label.setFont(QFont("Segoe UI", 10))
        stats_layout.addWidget(self.docs_count_label)
        
        # Index size
        self.index_size_label = QLabel("💾 0 MB")
        self.index_size_label.setFont(QFont("Segoe UI", 10))
        stats_layout.addWidget(self.index_size_label)
        
        # Status
        self.status_label = QLabel("● Idle")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #6b7280;")
        stats_layout.addWidget(self.status_label)
        
        layout.addLayout(stats_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Indexing...")
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e5e7eb;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()  # Hidden when not indexing
        layout.addWidget(self.progress_bar)
        
        # Document list
        self.doc_list = QListWidget()
        self.doc_list.setAlternatingRowColors(True)
        self.doc_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QListWidget::item:selected {
                background-color: #e0e7ff;
                color: #1e40af;
            }
        """)
        self.doc_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.doc_list, 1)
        
        # Footer actions
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        
        # Rebuild index
        self.rebuild_btn = QPushButton("🔄 Rebuild Index")
        self.rebuild_btn.setFixedHeight(32)
        self.rebuild_btn.clicked.connect(self._on_rebuild_index)
        footer_layout.addWidget(self.rebuild_btn)
        
        # Spacer
        footer_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Clear all
        self.clear_btn = QPushButton("🗑 Clear All")
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #fecaca;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear_all)
        footer_layout.addWidget(self.clear_btn)
        
        layout.addLayout(footer_layout)
    
    def _reset_state(self):
        """Reset widget to initial state."""
        self.docs_count_label.setText("📄 0 documents")
        self.index_size_label.setText("💾 0 MB")
        self.status_label.setText("● Idle")
        self.status_label.setStyleSheet("color: #6b7280;")
        self.progress_bar.hide()
        self.doc_list.clear()
        self.documents = []
    
    def _on_add_documents(self):
        """Handle add documents button click."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Documents to Knowledge Base",
            "",
            "All Supported Files (*.pdf *.txt *.docx *.md *.html);;"
            "PDF Files (*.pdf);;"
            "Text Files (*.txt);;"
            "Word Documents (*.docx);;"
            "Markdown Files (*.md);;"
            "HTML Files (*.html);;"
            "All Files (*)"
        )
        
        if files:
            self.add_documents_requested.emit(files)
    
    def _on_rebuild_index(self):
        """Handle rebuild index button click."""
        reply = QMessageBox.question(
            self,
            "Rebuild Index",
            "This will re-index all documents. This may take several minutes.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.rebuild_index_requested.emit()
    
    def _on_clear_all(self):
        """Handle clear all button click."""
        if self.doc_list.count() == 0:
            QMessageBox.information(self, "Clear All", "No documents to clear.")
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All Documents",
            f"This will remove all {self.doc_list.count()} documents from the knowledge base.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.doc_list.clear()
            self.documents.clear()
            self._update_stats()
    
    def _show_context_menu(self, position):
        """Show context menu for document list."""
        item = self.doc_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        remove_action = menu.addAction("🗑 Remove Document")
        remove_action.triggered.connect(lambda: self._remove_selected_document(item))
        
        menu.exec_(self.doc_list.mapToGlobal(position))
    
    def _remove_selected_document(self, item: QListWidgetItem):
        """Remove selected document from list."""
        doc_path = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Remove Document",
            f"Remove '{item.text()}' from knowledge base?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            row = self.doc_list.row(item)
            self.doc_list.takeItem(row)
            if doc_path in self.documents:
                self.documents.remove(doc_path)
            self.remove_document_requested.emit(doc_path)
            self._update_stats()
    
    def _update_stats(self):
        """Update statistics display."""
        count = self.doc_list.count()
        self.docs_count_label.setText(f"📄 {count} document{'s' if count != 1 else ''}")
        
        # Estimate index size (rough estimate: ~1MB per 100 pages)
        estimated_size = count * 0.5  # 0.5 MB per document average
        self.index_size_label.setText(f"💾 {estimated_size:.1f} MB")
    
    # Public Methods
    
    def set_indexing_status(self, status: str):
        """
        Set indexing status.
        
        Args:
            status: One of 'idle', 'indexing', 'success', 'error'
        """
        if status == 'idle':
            self.status_label.setText("● Idle")
            self.status_label.setStyleSheet("color: #6b7280;")
            self.progress_bar.hide()
        elif status == 'indexing':
            self.status_label.setText("● Indexing...")
            self.status_label.setStyleSheet("color: #3b82f6;")
            self.progress_bar.show()
        elif status == 'success':
            self.status_label.setText("● Ready")
            self.status_label.setStyleSheet("color: #22c55e;")
            self.progress_bar.hide()
        elif status == 'error':
            self.status_label.setText("● Error")
            self.status_label.setStyleSheet("color: #ef4444;")
            self.progress_bar.hide()
    
    def update_progress(self, progress: int, current_doc: str = ""):
        """
        Update indexing progress.
        
        Args:
            progress: Progress percentage (0-100)
            current_doc: Name of currently processing document
        """
        self.progress_bar.setValue(progress)
        if current_doc:
            self.progress_bar.setFormat(f"%p% - {current_doc[:30]}...")
    
    def add_document(self, doc_path: str, status: str = "indexed"):
        """
        Add a document to the list.
        
        Args:
            doc_path: Full path to the document
            status: Document status ('indexed', 'pending', 'error')
        """
        import os
        doc_name = os.path.basename(doc_path)
        
        item = QListWidgetItem(f"📄 {doc_name}")
        item.setData(Qt.ItemDataRole.UserRole, doc_path)
        
        # Set status icon based on status
        if status == "indexed":
            item.setForeground(Qt.GlobalColor.darkGreen)
        elif status == "pending":
            item.setForeground(Qt.GlobalColor.darkYellow)
        elif status == "error":
            item.setForeground(Qt.GlobalColor.darkRed)
        
        self.doc_list.addItem(item)
        self.documents.append(doc_path)
        self._update_stats()
    
    def remove_document(self, doc_path: str):
        """
        Remove a document from the list.
        
        Args:
            doc_path: Full path to the document
        """
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == doc_path:
                self.doc_list.takeItem(i)
                if doc_path in self.documents:
                    self.documents.remove(doc_path)
                self._update_stats()
                break
    
    def clear_documents(self):
        """Clear all documents from the list."""
        self.doc_list.clear()
        self.documents.clear()
        self._update_stats()
    
    def get_documents(self) -> list:
        """
        Get list of all document paths.
        
        Returns:
            List of document paths
        """
        return self.documents.copy()
    
    def get_document_count(self) -> int:
        """
        Get number of indexed documents.
        
        Returns:
            Number of documents
        """
        return self.doc_list.count()


# Quick test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    widget = KnowledgeBaseWidget()
    widget.resize(500, 400)
    widget.show()
    
    # Add some test documents
    widget.add_document("/path/to/document1.pdf", "indexed")
    widget.add_document("/path/to/document2.txt", "indexed")
    widget.add_document("/path/to/document3.md", "pending")
    
    # Simulate indexing
    widget.set_indexing_status("indexing")
    for i in range(0, 101, 10):
        widget.update_progress(i, f"Processing document {i//10}")
        app.processEvents()
        import time
        time.sleep(0.1)
    
    widget.set_indexing_status("success")
    
    sys.exit(app.exec())
