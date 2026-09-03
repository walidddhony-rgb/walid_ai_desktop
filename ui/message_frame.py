from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class MessageFrame(QFrame):
    def __init__(
        self,
        role,
        text,
        on_like=None,
        on_dislike=None,
        on_regenerate=None,
        on_speak=None,
        msg_id=None,
    ):
        super().__init__()
        self.setObjectName(role)
        self.msg_id = msg_id
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        buttons = QHBoxLayout()
        copy_btn = QPushButton("📋 نسخ")
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.label.text()))
        buttons.addWidget(copy_btn)

        if role == "assistant":
            for label, fn, width in [
                ("👍", on_like, 40),
                ("👎", on_dislike, 40),
                ("🔄", on_regenerate, 60),
                ("🔊", on_speak, 50),
            ]:
                btn = QPushButton(label)
                btn.setFixedWidth(width)
                if fn:
                    btn.clicked.connect(fn)
                buttons.addWidget(btn)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(buttons)
