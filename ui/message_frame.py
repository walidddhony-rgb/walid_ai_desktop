"""Chat message frame widget."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class MessageFrame(QFrame):
    """A chat message frame with role-based styling and action buttons."""

    def __init__(self, role: str, text: str, on_copy, on_like=None,
                 on_dislike=None, on_regenerate=None, msg_id=None):
        super().__init__()
        self.setObjectName(role)
        self.msg_id = msg_id
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        bl = QHBoxLayout()
        cb = QPushButton("📋 نسخ")
        cb.setFixedWidth(80)
        cb.clicked.connect(on_copy)
        bl.addWidget(cb)

        if role == "assistant":
            for t, fn, wd in [("👍", on_like, 40), ("👎", on_dislike, 40), ("🔄", on_regenerate, 60)]:
                b = QPushButton(t)
                b.setFixedWidth(wd)
                if fn:
                    b.clicked.connect(fn)
                bl.addWidget(b)
        bl.addStretch()

        ml = QVBoxLayout(self)
        ml.addWidget(self.label)
        ml.addLayout(bl)
