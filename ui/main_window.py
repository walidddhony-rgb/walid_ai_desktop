"""Main application window with chat, agent mode, file management, and search."""
from __future__ import annotations

import json
import shutil
import subprocess

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)

from agent.worker import AgentWorker, StreamWorker, SearchWorker, LearnWorker
from core.config import (
    SEARCH_MODES, MAX_INPUT_CHARS, load_config, save_config,
)
from core.utils import safe_filename, truncate
from db.database import Database
from tools.system_agent import SystemAgent
from ui.dialogs import SearchResultsDialog
from ui.message_frame import MessageFrame
from ui.themes import DARK_THEME, LIGHT_THEME

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document
except ImportError:
    Document = None
try:
    import whisper
except ImportError:
    whisper = None

db = Database()


class InputTextEdit(QTextEdit):
    """Auto-resizing text input with Enter-to-send support."""

    def __init__(self, cb):
        super().__init__()
        self.callback = cb
        self.setPlaceholderText("اكتب... (Enter=إرسال, Shift+Enter=سطر جديد)")
        self.setFixedHeight(90)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.callback()
            return
        super().keyPressEvent(e)


class MainWindow(QMainWindow):
    """Main application window with chat, agent mode, file management, and search."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Walid AI Desktop v10.1 — Agent")
        self.setMinimumSize(1450, 920)
        self.cid = None
        self.worker = None
        self.learn_worker = None
        self.search_worker = None
        self.whisper_worker = None
        self.config = load_config()
        self.dark_mode = self.config.get("dark_mode", True)
        self.selected_modes = ["quick"]
        self.last_msg = None
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self._pending_mid = None
        self.pending_search_payload = {"web": [], "academic": []}
        self.agent_mode = False
        self.setup_ui()
        self.setup_menu()
        self.apply_theme()
        self.load_convs()

    # ─── UI setup ───

    def setup_ui(self):
        c = QWidget()
        self.setCentralWidget(c)
        ml = QVBoxLayout(c)
        ml.setContentsMargins(0, 0, 0, 0)

        # Top toolbar: modes + agent toggle + search + theme
        tb = QHBoxLayout()
        self.mode_buttons = {}
        for k, lbl in SEARCH_MODES.items():
            b = QPushButton(lbl)
            b.setCheckable(True)
            b.clicked.connect(lambda _, k=k: self.toggle_mode(k))
            self.mode_buttons[k] = b
            tb.addWidget(b)
        self.mode_buttons["quick"].setChecked(True)
        tb.addStretch()

        self.agent_btn = QPushButton("🤖 وكيل")
        self.agent_btn.setCheckable(True)
        self.agent_btn.clicked.connect(self.toggle_agent)
        tb.addWidget(self.agent_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث في المحادثات...")
        self.search_input.textChanged.connect(self.do_search)
        tb.addWidget(self.search_input)

        self.results_btn = QPushButton("🔍")
        self.results_btn.clicked.connect(self.show_search_results)
        tb.addWidget(self.results_btn)

        self.theme_btn = QPushButton("🌙" if not self.dark_mode else "☀️")
        self.theme_btn.clicked.connect(self.toggle_theme)
        tb.addWidget(self.theme_btn)
        ml.addLayout(tb)

        self.mode_status = QLabel("الأوضاع: ⚡ سريع | الوكيل: معطل")
        self.mode_status.setStyleSheet("color:#FF9800;font-size:11px;padding:2px 8px")
        ml.addWidget(self.mode_status)

        # Main splitter: conversations | chat | files
        sp = QSplitter(Qt.Orientation.Horizontal)
        left, center, right = QWidget(), QWidget(), QWidget()
        left.setFixedWidth(290)
        right.setFixedWidth(340)

        # Left panel: conversations
        lv = QVBoxLayout(left)
        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self.load_conv)
        self.conv_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conv_list.customContextMenuRequested.connect(self.conv_context_menu)
        lv.addWidget(self.conv_list)
        self.new_btn = QPushButton("+ محادثة جديدة")
        self.new_btn.clicked.connect(self.new_conv)
        lv.addWidget(self.new_btn)
        self.export_btn = QPushButton("📤 تصدير")
        self.export_btn.clicked.connect(self.export_conv)
        lv.addWidget(self.export_btn)
        self.mem_btn = QPushButton("🧠 الذاكرة")
        self.mem_btn.clicked.connect(self.show_memory)
        lv.addWidget(self.mem_btn)

        # Center panel: chat
        cv = QVBoxLayout(center)
        self.status = QLabel("● جاهز")
        self.status.setStyleSheet("font-weight:bold;color:#4CAF50")
        cv.addWidget(self.status)
        self.chat = QScrollArea()
        self.chat.setWidgetResizable(True)
        self.chat.setMinimumHeight(680)
        self.chat.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.chat_content = QWidget()
        self.chat.setWidget(self.chat_content)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.addStretch()
        cv.addWidget(self.chat)

        # Input row
        ir = QHBoxLayout()
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedWidth(50)
        self.mic_btn.clicked.connect(self.start_mic)
        ir.addWidget(self.mic_btn)
        self.input = InputTextEdit(self.send)
        ir.addWidget(self.input)
        self.send_btn = QPushButton("إرسال")
        self.send_btn.clicked.connect(self.send)
        ir.addWidget(self.send_btn)
        self.stop_btn = QPushButton("■ إيقاف")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.hide()
        ir.addWidget(self.stop_btn)
        cv.addLayout(ir)

        # Right panel: files
        rv = QVBoxLayout(right)
        self.file_list = QListWidget()
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.file_context_menu)
        rv.addWidget(self.file_list)
        self.up_btn = QPushButton("📎 رفع ملفات")
        self.up_btn.clicked.connect(self.upload)
        rv.addWidget(self.up_btn)
        self.create_btn = QPushButton("📄 إنشاء ملف")
        self.create_btn.clicked.connect(self.create_file_wiz)
        rv.addWidget(self.create_btn)
        self.mkdir_btn = QPushButton("📁 إنشاء مجلد")
        self.mkdir_btn.clicked.connect(self.mkdir_wiz)
        rv.addWidget(self.mkdir_btn)

        sp.addWidget(left)
        sp.addWidget(center)
        sp.addWidget(right)
        ml.addWidget(sp)

    def setup_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("ملف")
        a = QAction("محادثة جديدة", self)
        a.setShortcut("Ctrl+N")
        a.triggered.connect(self.new_conv)
        fm.addAction(a)
        a = QAction("تصدير", self)
        a.setShortcut("Ctrl+E")
        a.triggered.connect(self.export_conv)
        fm.addAction(a)
        a = QAction("حذف المحادثة", self)
        a.setShortcut("Ctrl+D")
        a.triggered.connect(self.delete_current_conv)
        fm.addAction(a)

    # ─── Theme ───

    def set_status(self, text: str, color: str = "#4CAF50"):
        self.status.setText(text)
        self.status.setStyleSheet(f"font-weight:bold;color:{color}")

    def apply_theme(self):
        self.setStyleSheet(DARK_THEME if self.dark_mode else LIGHT_THEME)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_btn.setText("🌙" if not self.dark_mode else "☀️")
        self.apply_theme()
        self.config["dark_mode"] = self.dark_mode
        save_config(self.config)

    # ─── Mode & Agent toggles ───

    def toggle_agent(self):
        self.agent_mode = self.agent_btn.isChecked()
        self._update_mode_status()

    def _update_mode_status(self):
        self.mode_status.setText(
            "الأوضاع: " + " + ".join(SEARCH_MODES[m] for m in self.selected_modes)
            + (" | الوكيل: مفعل" if self.agent_mode else " | الوكيل: معطل")
        )

    def toggle_mode(self, k: str):
        b = self.mode_buttons[k]
        if b.isChecked():
            if k not in self.selected_modes:
                self.selected_modes.append(k)
        else:
            if k in self.selected_modes:
                self.selected_modes.remove(k)
        if not self.selected_modes:
            self.selected_modes = ["quick"]
            self.mode_buttons["quick"].setChecked(True)
        self._update_mode_status()

    # ─── Chat widget helpers ───

    def _insert_chat_widget(self, w: QWidget):
        s = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(w)
        if s:
            self.chat_layout.addItem(s)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _add_tool_log(self, text: str):
        f = QFrame()
        f.setObjectName("tool")
        l = QHBoxLayout(f)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size:11px;color:#FF9800")
        l.addWidget(lbl)
        self._insert_chat_widget(f)

    def add_msg_widget(self, role: str, text: str, msg_id=None) -> MessageFrame:
        def on_copy():
            QApplication.clipboard().setText(text)
            self.set_status("✓ تم النسخ", "#4CAF50")

        def on_like():
            if msg_id:
                db.add_feedback(msg_id, "like")

        def on_dislike():
            if msg_id:
                db.add_feedback(msg_id, "dislike")

        def on_regen():
            if self.last_msg:
                self.send(regenerate=True)

        frame = MessageFrame(role, text, on_copy, on_like, on_dislike, on_regen, msg_id)
        self._insert_chat_widget(frame)
        return frame

    # ─── Conversation management ───

    def load_convs(self):
        self.conv_list.clear()
        for c in db.convs():
            it = QListWidgetItem(c["title"])
            it.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.conv_list.addItem(it)

    def load_conv(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        self.cid = cid
        while self.chat_layout.count() > 1:
            w = self.chat_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        for m in db.conv(cid):
            msg_id = m["id"] if m["role"] == "assistant" else None
            self.add_msg_widget(m["role"], m["content"], msg_id)
        self.file_list.clear()
        for f in db.files(cid):
            it = QListWidgetItem(f"{f['filename']} ({f['file_type']})")
            it.setData(Qt.ItemDataRole.UserRole, f["id"])
            self.file_list.addItem(it)

    def new_conv(self):
        self.cid = db.add_conv("محادثة جديدة")
        self.load_convs()
        while self.chat_layout.count() > 1:
            w = self.chat_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.file_list.clear()

    def conv_context_menu(self, pos):
        item = self.conv_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        a = menu.addAction("🗑️ حذف")
        action = menu.exec(self.conv_list.mapToGlobal(pos))
        if action == a:
            cid = item.data(Qt.ItemDataRole.UserRole)
            db.delete_conv(cid)
            self.load_convs()

    def delete_current_conv(self):
        if not self.cid:
            return
        db.delete_conv(self.cid)
        self.cid = None
        self.load_convs()
        while self.chat_layout.count() > 1:
            w = self.chat_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

    def export_conv(self):
        if not self.cid:
            return
        msgs = db.conv(self.cid)
        path, _ = QFileDialog.getSaveFileName(self, "تصدير", "", "Text (*.txt)")
        if path:
            lines = []
            for m in msgs:
                lines.append("[" + m["role"] + "]\n" + m["content"] + "\n")
            from pathlib import Path
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self.set_status("✓ تم التصدير", "#4CAF50")

    # ─── Send / receive ───

    def send(self, regenerate: bool = False):
        if regenerate and self.last_msg:
            msg = self.last_msg
        else:
            msg = self.input.toPlainText().strip()
            if not msg or len(msg) > MAX_INPUT_CHARS:
                self.set_status("⚠ النص طويل جدًا", "#F44336")
                return
        if not self.cid:
            self.new_conv()
        self.last_msg = msg
        if not regenerate:
            mid = db.add_msg(self.cid, "user", msg)
            self.add_msg_widget("user", msg, mid)
            self.input.clear()
        self.current_assistant_text = ""
        assistant = self.add_msg_widget("assistant", "")
        self.current_assistant_label = assistant.label
        self.send_btn.hide()
        self.stop_btn.show()
        self.set_status("● جارٍ التفكير...", "#FF9800")

        memory_text = "\n".join(f"{k}: {v}" for k, v in db.get_all_memory().items())
        files = db.recent_file_rows(self.cid) if self.cid else []

        if self.agent_mode:
            self.worker = AgentWorker(msg, self.selected_modes, memory_text, files, regenerate)
            self.worker.chunk.connect(self.on_chunk)
            self.worker.tool_action.connect(self.on_tool_action)
            self.worker.finished_signal.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
        else:
            self.worker = StreamWorker(msg, files, self.selected_modes, regenerate,
                                       memory_text, self.pending_search_payload)
            self.worker.chunk.connect(self.on_chunk)
            self.worker.finished_signal.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
        self.worker.start()

        # Auto-learn
        self.learn_worker = LearnWorker(msg, memory_text, self.selected_modes)
        self.learn_worker.done.connect(lambda k, v: db.add_memory(k, v) if k else None)
        self.learn_worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.hide()
        self.send_btn.show()

    def on_chunk(self, text: str):
        self.current_assistant_text += text
        if self.current_assistant_label:
            self.current_assistant_label.setText(self.current_assistant_text)

    def on_tool_action(self, text: str):
        self._add_tool_log(text)

    def on_finished(self, _code: int):
        self.stop_btn.hide()
        self.send_btn.show()
        self.set_status("● جاهز", "#4CAF50")
        if self.cid and self.current_assistant_text:
            db.add_msg(self.cid, "assistant", self.current_assistant_text)
        self.current_assistant_text = ""
        self.current_assistant_label = None
        self.load_convs()

    def on_error(self, text: str):
        self.stop_btn.hide()
        self.send_btn.show()
        self.set_status("✗ " + text[:80], "#F44336")

    # ─── Search ───

    def do_search(self):
        q = self.search_input.text().strip()
        if not q:
            self.load_convs()
            return
        self.conv_list.clear()
        for c in db.search_convs(q):
            it = QListWidgetItem(c["title"])
            it.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.conv_list.addItem(it)

    def show_search_results(self):
        if not self.pending_search_payload.get("web") and not self.pending_search_payload.get("academic"):
            msg = self.input.toPlainText().strip() or self.last_msg or ""
            if not msg:
                return
            self.search_worker = SearchWorker(msg, self.selected_modes)
            self.search_worker.done.connect(self._on_search_done)
            self.search_worker.start()
        else:
            dlg = SearchResultsDialog(self.pending_search_payload, self)
            dlg.exec()

    def _on_search_done(self, payload: dict):
        self.pending_search_payload = payload
        dlg = SearchResultsDialog(payload, self)
        dlg.exec()

    # ─── Memory ───

    def show_memory(self):
        mem = db.get_all_memory()
        if not mem:
            QMessageBox.information(self, "الذاكرة", "لا توجد ذكريات محفوظة.")
            return
        text = "\n\n".join(f"📌 {k}\n{v}" for k, v in mem.items())
        QMessageBox.information(self, "الذاكرة", text)

    # ─── File management ───

    def upload(self):
        if not self.cid:
            self.new_conv()
        paths, _ = QFileDialog.getOpenFileNames(self, "رفع ملفات", "",
            "All (*.pdf *.txt *.md *.docx *.wav *.mp3);;PDF (*.pdf);;Text (*.txt *.md);;Word (*.docx);;Audio (*.wav *.mp3)")
        for p in paths:
            from pathlib import Path
            fp = Path(p)
            ext = fp.suffix.lstrip(".").lower()
            text = self._extract_text(fp, ext)
            db.add_file(self.cid, fp.name, fp, ext, fp.stat().st_size, text)
            it = QListWidgetItem(f"{fp.name} ({ext})")
            it.setData(Qt.ItemDataRole.UserRole, db.conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            self.file_list.addItem(it)
        self.set_status(f"✓ رفع {len(paths)} ملف", "#4CAF50")

    def _extract_text(self, path, ext):
        try:
            if ext in ("txt", "md"):
                return path.read_text(encoding="utf-8", errors="ignore")[:15000]
            if ext == "pdf" and PdfReader:
                return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)[:15000]
            if ext == "docx" and Document:
                return "\n".join(p.text for p in Document(str(path)).paragraphs)[:15000]
            if ext in ("wav", "mp3"):
                return "[ملف صوتي: استخدم Whisper لتحويله إلى نص]"
        except Exception as e:
            return f"[خطأ: {e}]"
        return ""

    def file_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        a = menu.addAction("🗑️ حذف")
        action = menu.exec(self.file_list.mapToGlobal(pos))
        if action == a:
            fid = item.data(Qt.ItemDataRole.UserRole)
            db.delete_file(fid)
            self.file_list.takeItem(self.file_list.row(item))

    def create_file_wiz(self):
        path, ok = QInputDialog.getText(self, "إنشاء ملف", "المسار:")
        if not ok or not path:
            return
        content, ok = QInputDialog.getMultiLineText(self, "محتوى الملف", "اكتب المحتوى:")
        if not ok:
            return
        SystemAgent.create_file(path, content)
        self.set_status(f"✓ تم إنشاء {path}", "#4CAF50")

    def mkdir_wiz(self):
        path, ok = QInputDialog.getText(self, "إنشاء مجلد", "المسار:")
        if not ok or not path:
            return
        SystemAgent.create_dir(path)
        self.set_status(f"✓ تم إنشاء {path}", "#4CAF50")

    # ─── Voice input ───

    def start_mic(self):
        if not whisper:
            self.set_status("⚠ Whisper غير مثبت", "#F44336")
            return
        self.set_status("🎤 جارٍ التسجيل...", "#FF9800")
        try:
            model = whisper.load_model("base")
            import tempfile
            import sounddevice as sd
            import numpy as np
            fs = 16000
            duration = 5
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                import soundfile as sf
                sf.write(f.name, recording, fs)
                result = model.transcribe(f.name)
                text = result.get("text", "").strip()
                if text:
                    self.input.setPlainText(text)
                    self.set_status("✓ تم التفريغ", "#4CAF50")
        except Exception as e:
            self.set_status("✗ " + str(e), "#F44336")
