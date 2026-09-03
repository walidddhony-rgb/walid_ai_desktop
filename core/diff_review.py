import difflib
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def generate_diff(old_content, new_content, filename="file"):
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    fromfile = filename + " (original)"
    tofile = filename + " (new)"
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm="")
    return "".join(diff)


def format_diff_html(diff_text):
    lines = diff_text.split("\n")
    html_parts = [
        "<style>"
        "body{font-family:monospace;font-size:13px;}"
        ".add{background:#d4edda;}"
        ".del{background:#f8d7da;}"
        ".ctx{color:#888;}"
        ".hdr{color:#0066cc;font-weight:bold;}"
        "</style>"
    ]
    html_parts.append("<pre>")
    for line in lines:
        escaped = line.replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("+++") or line.startswith("---"):
            html_parts.append('<span class="hdr">' + escaped + "</span>")
        elif line.startswith("+") and not line.startswith("+++"):
            html_parts.append('<span class="add">' + escaped + "</span>")
        elif line.startswith("-") and not line.startswith("---"):
            html_parts.append('<span class="del">' + escaped + "</span>")
        elif line.startswith("@@"):
            html_parts.append('<span class="hdr">' + escaped + "</span>")
        else:
            html_parts.append('<span class="ctx">' + escaped + "</span>")
        html_parts.append("\n")
    html_parts.append("</pre>")
    return "".join(html_parts)


class DiffReviewDialog(QDialog):
    def __init__(self, filename, old_content, new_content, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.old_content = old_content
        self.new_content = new_content
        self.approved = False
        self.create_file = not old_content
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("مراجعة التغييرات — " + self.filename)
        self.setMinimumSize(900, 600)
        layout = QVBoxLayout(self)

        if self.create_file:
            info = QLabel("إنشاء ملف جديد: <b>" + self.filename + "</b>")
        else:
            info = QLabel("تعديل ملف: <b>" + self.filename + "</b>")
        layout.addWidget(info)

        diff_text = generate_diff(self.old_content, self.new_content, self.filename)
        if not diff_text.strip():
            diff_text = "(no changes)"

        diff_view = QTextEdit()
        diff_view.setReadOnly(True)
        diff_view.setHtml(format_diff_html(diff_text))
        layout.addWidget(diff_view)

        if self.create_file:
            preview_label = QLabel("محتوى الملف الجديد:")
            layout.addWidget(preview_label)
            preview = QTextEdit()
            preview.setReadOnly(True)
            preview.setPlainText(self.new_content)
            preview.setMaximumHeight(200)
            layout.addWidget(preview)

        auto_apply_check = QCheckBox("طبق التغييرات تلقائيًا لهذا الملف في هذه الجلسة")
        layout.addWidget(auto_apply_check)
        self.auto_apply = auto_apply_check

        buttons = QHBoxLayout()
        approve_btn = QPushButton("موافقة وتطبيق")
        approve_btn.setStyleSheet(
            "background: #28a745; color: white; padding: 10px 20px; font-weight: bold;"
        )
        approve_btn.clicked.connect(self.on_approve)
        buttons.addWidget(approve_btn)

        reject_btn = QPushButton("رفض")
        reject_btn.setStyleSheet(
            "background: #dc3545; color: white; padding: 10px 20px; font-weight: bold;"
        )
        reject_btn.clicked.connect(self.on_reject)
        buttons.addWidget(reject_btn)
        layout.addLayout(buttons)

    def on_approve(self):
        self.approved = True
        self.accept()

    def on_reject(self):
        self.approved = False
        self.reject()

    def should_auto_apply(self):
        return self.auto_apply.isChecked()


def apply_file_change(filepath, new_content, auto_apply_files, parent_widget=None):
    p = Path(filepath)
    old_content = ""
    if p.exists():
        try:
            old_content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if old_content == new_content:
        return True

    if filepath in auto_apply_files:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_content, encoding="utf-8")
        return True

    if parent_widget:
        dialog = DiffReviewDialog(p.name, old_content, new_content, parent_widget)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted and dialog.approved:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new_content, encoding="utf-8")
            if dialog.should_auto_apply():
                auto_apply_files.add(filepath)
            return True
        return False

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_content, encoding="utf-8")
    return True
