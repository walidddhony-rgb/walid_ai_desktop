"""Dialog windows."""
from PyQt6.QtWidgets import (
    QDialog, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QInputDialog, QMessageBox,
)


class SearchResultsDialog(QDialog):
    """Dialog showing web/academic search results in a table."""

    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("نتائج البحث")
        self.resize(900, 600)
        l = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["النوع", "العنوان", "الرابط", "الملخص"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rows = []
        for k in ("web", "academic"):
            for r in payload.get(k, []):
                rows.append((k, r.get("title", ""), r.get("url", ""), r.get("snippet", "")))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(v))
        l.addWidget(self.table)
        b = QPushButton("إغلاق")
        b.clicked.connect(self.accept)
        l.addWidget(b)
