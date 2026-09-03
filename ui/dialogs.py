from PyQt6.QtWidgets import QDialog, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout


class SearchResultsDialog(QDialog):
    def __init__(self, payload, parent=None):
        super().__init__(parent)
        self.setWindowTitle('نتائج البحث')
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['النوع', 'العنوان', 'الرابط', 'الملخص'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rows = []
        for kind in ('web', 'academic'):
            for r in payload.get(kind, []):
                rows.append((kind, r.get('title', ''), r.get('url', ''), r.get('snippet', '')))
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(value))
        layout.addWidget(table)
        close_btn = QPushButton('إغلاق')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
