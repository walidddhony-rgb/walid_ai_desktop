import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent.worker import AgentWorker
from core.agents_md import read_agents_md, write_agents_md
from core.code_executor import CodeExecutionWorker
from core.config import SEARCH_MODES, load_config, save_config
from core.diff_review import DiffReviewDialog
from core.hooks import HOOK_EVENTS, create_hook_template, discover_hooks
from core.profiles import ensure_default_profile, list_profiles, load_profile
from core.session import list_sessions, load_session, save_session
from core.skills import discover_skills
from core.subagent import SubagentManager
from db.database import Database
from knowledge.index_worker import IndexWorker
from knowledge.ingestor import preview_file_content
from tools.file_tools import FileChangeBridge, set_bridge
from ui.message_frame import MessageFrame
from ui.themes import DARK_THEME, LIGHT_THEME
from voice.stt_engine import VoiceRecorder, VoiceSTTWorker, save_frames_to_wav
from voice.tts_engine import TTSSpeakWorker

db = Database()
ensure_default_profile()


class InputTextEdit(QTextEdit):
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Walid AI Desktop v8.2 — Subagents + Hooks")
        self.setMinimumSize(1600, 1000)
        self.config = load_config()
        self.dark_mode = self.config.get("dark_mode", True)
        self.workspace_path = Path(self.config.get("workspace_path", str(Path.cwd())))
        self.auto_learn = self.config.get("auto_learn", True)
        self.auto_run = False
        self.selected_modes = ["quick"]
        self.worker = None
        self.tts_worker = None
        self.recorder = None
        self.stt_worker = None
        self.index_worker = None
        self.command_worker = None
        self.code_worker = None
        self.current_assistant_label = None
        self.current_assistant_text = ""
        self.cid = None
        self.attached_files = []
        self._is_working = False
        self._file_bridge = FileChangeBridge()
        self._file_bridge.review_needed.connect(self.on_file_review_needed)
        set_bridge(self._file_bridge)
        self._subagent_mgr = SubagentManager()
        self.setup_ui()
        self.setup_menu()
        self.apply_theme()

    def setup_ui(self):
        c = QWidget()
        self.setCentralWidget(c)
        root = QVBoxLayout(c)
        root.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.mode_buttons = {}
        for key, label in SEARCH_MODES.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, k=key: self.toggle_mode(k))
            self.mode_buttons[key] = btn
            top.addWidget(btn)
        self.mode_buttons["quick"].setChecked(True)
        top.addStretch()
        self.agent_btn = QPushButton("🤖 وكيل")
        self.agent_btn.setCheckable(True)
        self.agent_btn.setChecked(True)
        self.agent_btn.clicked.connect(self.update_mode_status)
        top.addWidget(self.agent_btn)
        self.auto_run_btn = QPushButton("⚡ تشغيل تلقائي")
        self.auto_run_btn.setCheckable(True)
        self.auto_run_btn.clicked.connect(self.toggle_auto_run)
        top.addWidget(self.auto_run_btn)
        self.voice_btn = QPushButton("🎙 محادثة صوتية")
        self.voice_btn.setCheckable(True)
        self.voice_btn.clicked.connect(self.toggle_voice_recording)
        top.addWidget(self.voice_btn)
        self.tts_btn = QPushButton("🔊 نطق آخر رد")
        self.tts_btn.clicked.connect(self.speak_last_reply)
        top.addWidget(self.tts_btn)
        self.theme_btn = QPushButton("☀️" if self.dark_mode else "🌙")
        self.theme_btn.clicked.connect(self.toggle_theme)
        top.addWidget(self.theme_btn)
        root.addLayout(top)
        info_row = QHBoxLayout()
        self.mode_status = QLabel()
        self.workspace_label = QLabel("📂 مساحة العمل: " + str(self.workspace_path))
        self.status = QLabel("● جاهز")
        self.subagent_counter = QLabel("🧩 وكلاء: 0")
        info_row.addWidget(self.mode_status)
        info_row.addWidget(self.workspace_label)
        info_row.addWidget(self.subagent_counter)
        info_row.addWidget(self.status)
        root.addLayout(info_row)
        self.update_mode_status()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("الملف:"))
        self.profile_combo = QComboBox()
        self.refresh_profiles()
        self.profile_combo.currentTextChanged.connect(self.on_profile_change)
        profile_row.addWidget(self.profile_combo)
        resume_btn = QPushButton("📋 استئناف")
        resume_btn.clicked.connect(self.resume_session)
        profile_row.addWidget(resume_btn)
        agents_btn = QPushButton("📝 AGENTS.md")
        agents_btn.clicked.connect(self.edit_agents_md)
        profile_row.addWidget(agents_btn)
        skills_btn = QPushButton("🛠 المهارات")
        skills_btn.clicked.connect(self.show_skills)
        profile_row.addWidget(skills_btn)
        hooks_btn = QPushButton("🪝 الخطافات")
        hooks_btn.clicked.connect(self.show_hooks)
        profile_row.addWidget(hooks_btn)
        root.addLayout(profile_row)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        center = QWidget()
        right = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        self.conv_list = QListWidget()
        left_layout.addWidget(self.conv_list)
        new_btn = QPushButton("+ محادثة جديدة")
        new_btn.clicked.connect(self.new_conv)
        left_layout.addWidget(new_btn)
        self.learn_btn = QPushButton("🧠 تعلّم")
        self.learn_btn.setCheckable(True)
        self.learn_btn.setChecked(self.auto_learn)
        self.learn_btn.clicked.connect(self.toggle_auto_learn)
        left_layout.addWidget(self.learn_btn)
        self.auto_index_check = QCheckBox("فهرسة تلقائية")
        self.auto_index_check.setChecked(True)
        left_layout.addWidget(self.auto_index_check)
        spawn_btn = QPushButton("🧩 وكيل فرعي")
        spawn_btn.clicked.connect(self.manual_spawn_subagent)
        left_layout.addWidget(spawn_btn)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)
        self.chat = QScrollArea()
        self.chat.setWidgetResizable(True)
        self.chat.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.addStretch()
        self.chat.setWidget(self.chat_content)
        center_layout.addWidget(self.chat)
        input_row = QHBoxLayout()
        self.input = InputTextEdit(self.on_send_clicked)
        input_row.addWidget(self.input)
        self.send_btn = QPushButton("إرسال")
        self.send_btn.clicked.connect(self.on_send_clicked)
        input_row.addWidget(self.send_btn)
        center_layout.addLayout(input_row)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(8)
        right_splitter.setChildrenCollapsible(False)
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(4, 4, 4, 4)
        files_layout.addWidget(QLabel("📎 الملفات"))
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.preview_selected_file)
        files_layout.addWidget(self.file_list)
        fb = QHBoxLayout()
        upload_btn = QPushButton("📎 رفع")
        upload_btn.clicked.connect(self.upload_files)
        fb.addWidget(upload_btn)
        preview_btn = QPushButton("👁 معاينة")
        preview_btn.clicked.connect(lambda: self.preview_selected_file(self.file_list.currentRow()))
        fb.addWidget(preview_btn)
        files_layout.addLayout(fb)
        fa = QHBoxLayout()
        ia = QPushButton("🧠 فهرسة")
        ia.clicked.connect(self.index_attachments)
        fa.addWidget(ia)
        id_btn = QPushButton("📚 مجلد")
        id_btn.clicked.connect(self.index_directory_dialog)
        fa.addWidget(id_btn)
        files_layout.addLayout(fa)
        fw = QHBoxLayout()
        ws_btn = QPushButton("📂 Workspace")
        ws_btn.clicked.connect(self.choose_workspace)
        fw.addWidget(ws_btn)
        cf_btn = QPushButton("📄 ملف")
        cf_btn.clicked.connect(self.create_file_in_workspace)
        fw.addWidget(cf_btn)
        cd_btn = QPushButton("📁 مجلد")
        cd_btn.clicked.connect(self.create_dir_in_workspace)
        fw.addWidget(cd_btn)
        files_layout.addLayout(fw)
        exec_btn = QPushButton("▶ نفّذ كود")
        exec_btn.clicked.connect(self.execute_code_dialog)
        files_layout.addWidget(exec_btn)
        preview_widget = QWidget()
        pl = QVBoxLayout(preview_widget)
        pl.setContentsMargins(4, 4, 4, 4)
        pl.addWidget(QLabel("👁 المعاينة"))
        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        pl.addWidget(self.preview_box)
        log_widget = QWidget()
        ll = QVBoxLayout(log_widget)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.addWidget(QLabel("📋 سجل المهام"))
        self.task_log = QTextEdit()
        self.task_log.setReadOnly(True)
        ll.addWidget(self.task_log)
        right_splitter.addWidget(files_widget)
        right_splitter.addWidget(preview_widget)
        right_splitter.addWidget(log_widget)
        right_splitter.setSizes([300, 250, 350])
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(right_splitter)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setSizes([250, 800, 500])
        root.addWidget(splitter)

    def setup_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("ملف")
        a = QAction("محادثة جديدة", self)
        a.setShortcut("Ctrl+N")
        a.triggered.connect(self.new_conv)
        fm.addAction(a)
        a2 = QAction("استئناف جلسة", self)
        a2.setShortcut("Ctrl+R")
        a2.triggered.connect(self.resume_session)
        fm.addAction(a2)
        a3 = QAction("حفظ الجلسة", self)
        a3.setShortcut("Ctrl+S")
        a3.triggered.connect(self.save_current_session)
        fm.addAction(a3)
        fm.addAction(QAction("خروج", self, triggered=self.close))

    def update_mode_status(self):
        modes = " + ".join(SEARCH_MODES[m] for m in self.selected_modes)
        ag = "مفعل" if self.agent_btn.isChecked() else "معطل"
        ar = "تلقائي" if self.auto_run else "يدوي"
        self.mode_status.setText("الأوضاع: " + modes + " | الوكيل: " + ag + " | " + ar)
        self.subagent_counter.setText("🧩 وكلاء: " + str(self._subagent_mgr.active_count()))

    def apply_theme(self):
        self.setStyleSheet(DARK_THEME if self.dark_mode else LIGHT_THEME)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_btn.setText("☀️" if self.dark_mode else "🌙")
        self.apply_theme()
        self.config["dark_mode"] = self.dark_mode
        save_config(self.config)

    def toggle_auto_run(self):
        self.auto_run = self.auto_run_btn.isChecked()
        self.update_mode_status()

    def toggle_auto_learn(self):
        self.auto_learn = self.learn_btn.isChecked()
        self.config["auto_learn"] = self.auto_learn
        save_config(self.config)

    def toggle_mode(self, key):
        btn = self.mode_buttons[key]
        if btn.isChecked() and key not in self.selected_modes:
            self.selected_modes.append(key)
        elif (not btn.isChecked()) and key in self.selected_modes:
            self.selected_modes.remove(key)
        if not self.selected_modes:
            self.selected_modes = ["quick"]
            self.mode_buttons["quick"].setChecked(True)
        self.update_mode_status()

    def log_task(self, text):
        self.task_log.append(text)
        self.status.setText(text)

    def set_working(self, is_working):
        self._is_working = is_working
        if is_working:
            self.send_btn.setText("⏹ إيقاف")
            self.send_btn.setStyleSheet("background: #dc3545; color: white; font-weight: bold;")
            self.input.setEnabled(False)
        else:
            self.send_btn.setText("إرسال")
            self.send_btn.setStyleSheet("")
            self.input.setEnabled(True)

    def on_send_clicked(self):
        if self._is_working:
            self.cancel_all_tasks()
            return
        self.send()

    def cancel_all_tasks(self):
        cancelled = False
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            cancelled = True
        if self._subagent_mgr.active_count() > 0:
            self._subagent_mgr.stop_all()
            cancelled = True
        for attr in ["index_worker", "command_worker", "recorder", "tts_worker", "code_worker"]:
            w = getattr(self, attr, None)
            if w and hasattr(w, "isRunning") and w.isRunning():
                if hasattr(w, "stop"):
                    w.stop()
                cancelled = True
        self.set_working(False)
        self.log_task("⏹ تم إيقاف جميع المهام." if cancelled else "لا توجد مهام قيد التشغيل.")

    def cancel_current_operation(self):
        self.cancel_all_tasks()

    def refresh_profiles(self):
        self.profile_combo.clear()
        profiles = list_profiles() or ["default"]
        for p in profiles:
            self.profile_combo.addItem(p)

    def on_profile_change(self, name):
        if not name:
            return
        data = load_profile(name)
        if data:
            if "auto_run" in data:
                self.auto_run = data["auto_run"]
                self.auto_run_btn.setChecked(self.auto_run)
            if "auto_learn" in data:
                self.auto_learn = data["auto_learn"]
                self.learn_btn.setChecked(self.auto_learn)
            self.update_mode_status()

    def choose_workspace(self):
        d = QFileDialog.getExistingDirectory(self, "اختر Workspace", str(self.workspace_path))
        if d:
            self.workspace_path = Path(d)
            self.workspace_label.setText("📂 " + str(self.workspace_path))
            self.config["workspace_path"] = str(self.workspace_path)
            save_config(self.config)
            self.log_task("Workspace: " + str(self.workspace_path))

    def create_file_in_workspace(self):
        name, ok = QInputDialog.getText(self, "ملف", "الاسم:")
        if ok and name:
            p = self.workspace_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
            self.log_task("ملف: " + str(p))

    def create_dir_in_workspace(self):
        name, ok = QInputDialog.getText(self, "مجلد", "الاسم:")
        if ok and name:
            p = self.workspace_path / name
            p.mkdir(parents=True, exist_ok=True)
            self.log_task("مجلد: " + str(p))

    def execute_code_dialog(self):
        lang, ok = QInputDialog.getItem(
            self, "كود", "اللغة:", ["python", "shell", "javascript"], 0, False
        )
        if not ok:
            return
        code, ok2 = QInputDialog.getMultiLineText(self, "كود", lang + ":")
        if ok2 and code.strip():
            self.run_code(lang, code.strip())

    def run_code(self, language, code):
        self.code_worker = CodeExecutionWorker(
            code, language, str(self.workspace_path), self.auto_run
        )
        self.code_worker.code_started.connect(
            lambda c, language_name: self.log_task("تنفيذ " + language_name)
        )
        self.code_worker.code_output.connect(self.log_task)
        self.code_worker.approval_needed.connect(self.on_approval_needed)
        self.code_worker.code_finished.connect(lambda rc, out: self.log_task("رمز: " + str(rc)))
        self.code_worker.error.connect(lambda e: self.log_task("خطأ: " + e))
        self.code_worker.start()

    def on_approval_needed(self, code, language, action):
        mb = QMessageBox(self)
        mb.setWindowTitle("موافقة")
        mb.setText(language + " / " + action + "\n\nموافقة؟")
        mb.setDetailedText(code)
        mb.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if mb.exec() == QMessageBox.StandardButton.Yes:
            self.code_worker.approve()
        else:
            self.code_worker.reject()

    def on_file_review_needed(self, filepath, old_content, new_content):
        p = Path(filepath)
        dialog = DiffReviewDialog(p.name, old_content, new_content, self)
        result = dialog.exec()
        approved = result == dialog.DialogCode.Accepted and dialog.approved
        if approved:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new_content, encoding="utf-8")
            self.log_task("تطبيق: " + p.name)
        else:
            self.log_task("رفض: " + p.name)
        self._file_bridge.set_result(approved, dialog.should_auto_apply())

    def edit_agents_md(self):
        current = read_agents_md(str(self.workspace_path))
        text, ok = QInputDialog.getMultiLineText(self, "AGENTS.md", "التعليمات:", current)
        if ok:
            path = write_agents_md(str(self.workspace_path), text)
            self.log_task("AGENTS.md: " + path)

    def show_skills(self):
        skills = discover_skills(str(self.workspace_path))
        if not skills:
            self.log_task("لا توجد مهارات")
            return
        self.log_task("مهارات: " + str(len(skills)))
        for s in skills:
            self.task_log.append("  - " + s["name"])

    def show_hooks(self):
        hooks = discover_hooks(str(self.workspace_path))
        if not hooks:
            choice = QMessageBox.question(
                self,
                "خطافات",
                "لا توجد خطافات. إنشاء مثال؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if choice == QMessageBox.StandardButton.Yes:
                event, ok = QInputDialog.getItem(self, "حدث", "اختر:", HOOK_EVENTS, 0, False)
                if ok and event:
                    path = create_hook_template(str(self.workspace_path), event)
                    self.log_task("خطاف: " + path)
            return
        self.log_task("الخطافات:")
        for event, scripts in hooks.items():
            self.task_log.append("  " + event + ":")
            for s in scripts:
                self.task_log.append("    - " + Path(s).name)

    def manual_spawn_subagent(self):
        task, ok = QInputDialog.getText(self, "وكيل فرعي", "المهمة:")
        if not ok or not task.strip():
            return
        mode, ok2 = QInputDialog.getItem(self, "نوع", "اختر:", ["worker", "explorer"], 0, False)
        if ok2:
            self.spawn_subagent(task.strip(), mode)

    def spawn_subagent(self, task, mode="worker"):
        agent_id, worker = self._subagent_mgr.spawn(task, str(self.workspace_path), mode)
        if worker is None:
            self.log_task(agent_id)
            return agent_id
        worker.result_ready.connect(self.on_subagent_result)
        worker.step_log.connect(lambda aid, msg: self.log_task("🧩 " + aid + ": " + msg[:150]))
        worker.error.connect(lambda aid, err: self.log_task("🧩 خطأ " + aid + ": " + err[:100]))
        worker.start()
        self.update_mode_status()
        self.log_task("🧩 وكيل فرعي: " + agent_id + " (" + mode + ")")
        return agent_id

    def on_subagent_result(self, agent_id, result):
        self._subagent_mgr.set_result(agent_id, result)
        self.log_task("🧩 نتيجة " + agent_id + ": " + result[:200])
        self.update_mode_status()

    def get_subagent_results(self):
        results = self._subagent_mgr.get_all_results()
        active = self._subagent_mgr.active_count()
        status = "running" if active > 0 else "done"
        return json.dumps(
            {"status": status, "active": active, "results": results}, ensure_ascii=False
        )

    def has_active_subagents(self):
        return self._subagent_mgr.active_count() > 0

    def resume_session(self):
        sessions = list_sessions()
        if not sessions:
            self.log_task("لا توجد جلسات")
            return
        items = [s["title"] or s["cid"][:8] for s in sessions]
        choice, ok = QInputDialog.getItem(self, "جلسة", "اختر:", items, 0, False)
        if not ok:
            return
        data = load_session(sessions[items.index(choice)]["cid"])
        if not data:
            self.log_task("فشل التحميل")
            return
        self.cid = data["cid"]
        self.conv_list.addItem(self.cid)
        for m in data.get("messages", []):
            self.add_msg_widget(m.get("role", "user"), m.get("content", ""))
        self.log_task("استئناف: " + self.cid)

    def save_current_session(self):
        if not self.cid:
            self.log_task("لا توجد محادثة")
            return
        from db.database import Database as DB

        conn = DB()
        rows = conn.conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id", (self.cid,)
        ).fetchall()
        msgs = [{"role": r["role"], "content": r["content"]} for r in rows]
        path = save_session(self.cid, msgs, "محادثة")
        self.log_task("حفظ: " + path)

    def upload_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "ملفات",
            str(self.workspace_path),
            "All (*);;PDF (*.pdf);;Word (*.docx);;Text (*.txt *.md);;Python (*.py)",
        )
        if not paths:
            return
        self.attached_files.extend(paths)
        self.file_list.clear()
        for p in self.attached_files:
            self.file_list.addItem(Path(p).name)
        self.file_list.setCurrentRow(len(self.attached_files) - len(paths))
        self.log_task("إرفاق " + str(len(paths)) + " ملف")
        if self.auto_index_check.isChecked():
            self.index_attachments()

    def preview_selected_file(self, row):
        if row < 0 or row >= len(self.attached_files):
            self.preview_box.clear()
            return
        self.preview_box.setPlainText(preview_file_content(self.attached_files[row]))
        self.log_task("معاينة: " + Path(self.attached_files[row]).name)

    def index_attachments(self):
        if not self.attached_files:
            self.log_task("لا مرفقات")
            return
        self.progress_bar.setValue(0)
        self.index_worker = IndexWorker(file_paths=self.attached_files)
        self.index_worker.progress_changed.connect(self.progress_bar.setValue)
        self.index_worker.log_message.connect(self.log_task)
        self.index_worker.finished_indexing.connect(
            lambda n: (self.progress_bar.setValue(100), self.log_task("فهرسة: " + str(n) + " مقطع"))
        )
        self.index_worker.error.connect(lambda e: self.log_task("خطأ فهرسة: " + e))
        self.index_worker.start()

    def index_directory_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "مجلد أبحاث", str(self.workspace_path))
        if not d:
            return
        self.progress_bar.setValue(0)
        self.index_worker = IndexWorker(directory_path=d)
        self.index_worker.progress_changed.connect(self.progress_bar.setValue)
        self.index_worker.log_message.connect(self.log_task)
        self.index_worker.finished_indexing.connect(
            lambda n: (self.progress_bar.setValue(100), self.log_task("فهرسة: " + str(n) + " مقطع"))
        )
        self.index_worker.error.connect(lambda e: self.log_task("خطأ: " + e))
        self.index_worker.start()

    def toggle_voice_recording(self):
        if self.voice_btn.isChecked():
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recorder = VoiceRecorder()
        self.recorder.error.connect(lambda e: self.log_task("ميكروفون: " + e))
        self.recorder.start()
        self.voice_btn.setText("⏹ إيقاف")
        self.log_task("تسجيل...")

    def stop_recording(self):
        if not self.recorder:
            return
        self.recorder.stop()
        self.recorder.wait(3000)
        wav = save_frames_to_wav(self.recorder.frames)
        self.recorder = None
        self.voice_btn.setText("🎙 محادثة صوتية")
        self.voice_btn.setChecked(False)
        self.log_task("تفريغ...")
        self.stt_worker = VoiceSTTWorker(wav)
        self.stt_worker.transcribed.connect(self.on_transcribed)
        self.stt_worker.error.connect(lambda e: self.log_task("STT: " + e))
        self.stt_worker.start()

    def on_transcribed(self, text):
        self.input.setPlainText(text)
        self.log_task("تفريغ: " + text[:80])

    def speak_last_reply(self):
        if not self.current_assistant_text.strip():
            self.log_task("لا يوجد رد")
            return
        if self.tts_worker and self.tts_worker.isRunning():
            self.log_task("نطق جارٍ")
            return
        self.tts_btn.setEnabled(False)
        self.tts_worker = TTSSpeakWorker(self.current_assistant_text)
        self.tts_worker.error.connect(lambda e: self.log_task("TTS: " + e))
        self.tts_worker.finished_speaking.connect(
            lambda: (self.tts_btn.setEnabled(True), self.log_task("انتهى النطق"))
        )
        self.tts_worker.start()

    def _insert_chat_widget(self, widget):
        spacer = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(widget)
        if spacer:
            self.chat_layout.addItem(spacer)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def add_msg_widget(self, role, text):
        frame = MessageFrame(role, text, on_speak=self.speak_last_reply)
        self._insert_chat_widget(frame)
        return frame

    def new_conv(self):
        self.cid = db.add_conv("محادثة جديدة")
        self.conv_list.addItem(self.cid)
        self.log_task("محادثة جديدة")

    def send(self):
        msg = self.input.toPlainText().strip()
        if not msg:
            return
        if not self.cid:
            self.new_conv()
        db.add_msg(self.cid, "user", msg)
        self.add_msg_widget("user", msg)
        self.input.clear()
        self.current_assistant_text = ""
        assistant = self.add_msg_widget("assistant", "")
        self.current_assistant_label = assistant.label
        memory = "\n".join(f"{k}: {v}" for k, v in db.get_all_memory().items())
        self._subagent_mgr.clear()
        self.set_working(True)
        self.worker = AgentWorker(
            msg,
            self.selected_modes,
            memory,
            self.attached_files,
            self.cid,
            self.auto_learn,
            str(self.workspace_path),
            exec_callback=self.run_code_sync,
            spawn_callback=self.spawn_subagent,
            results_callback=self.get_subagent_results,
            wait_callback=self.has_active_subagents,
        )
        self.worker.chunk.connect(self.on_chunk)
        self.worker.tool_action.connect(self.on_tool_action)
        self.worker.code_execution.connect(self.on_code_from_agent)
        self.worker.step_started.connect(self.on_step_started)
        self.worker.compaction_triggered.connect(lambda info: self.log_task("📦 " + info))
        self.worker.hook_triggered.connect(
            lambda ev, msg: self.log_task("🪝 " + ev + ": " + msg[:120])
        )
        self.worker.subagent_waiting.connect(lambda msg: self.log_task("⏳ " + msg))
        self.worker.learned_fact.connect(lambda f: self.log_task("تعلّم: " + f[:80]))
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.cancelled.connect(lambda msg: (self.set_working(False), self.log_task(msg)))
        self.worker.error.connect(self.on_error)
        self.worker.start()
        self.log_task("إرسال للوكيل...")
        self.update_mode_status()

    def on_step_started(self, step):
        self.log_task("--- الخطوة " + str(step) + " ---")
        if step > 1:
            if self.cid and self.current_assistant_text.strip():
                db.add_msg(self.cid, "assistant", self.current_assistant_text)
            self.current_assistant_text = ""
            new_a = self.add_msg_widget("assistant", "")
            self.current_assistant_label = new_a.label

    def on_tool_action(self, name, output):
        self.log_task(name + ":")
        if output:
            self.task_log.append(output)

    def run_code_sync(self, language, code):
        import os as _os
        import subprocess as _sp
        import sys as _sys
        import tempfile as _tf

        from core.sandbox import is_dangerous

        if is_dangerous(code):
            return "rejected"
        tmp = Path(_tf.gettempdir()) / "walid_exec.py"
        tmp.write_text("# -*- coding: utf-8 -*-\n" + code, encoding="utf-8")
        env = _os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        r = _sp.run(
            [_sys.executable, str(tmp)],
            cwd=str(self.workspace_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=env,
        )
        return ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()[:1000]

    def on_code_from_agent(self, language, code):
        self.log_task("كود " + language + ":")
        self.task_log.append(code[:500])
        self.run_code(language, code)

    def on_chunk(self, text):
        self.current_assistant_text += text
        if self.current_assistant_label:
            self.current_assistant_label.setText(self.current_assistant_text)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def on_finished(self, _code):
        if self.cid and self.current_assistant_text.strip():
            db.add_msg(self.cid, "assistant", self.current_assistant_text)
        self.set_working(False)
        self.log_task("اكتمل الرد.")
        self.update_mode_status()

    def on_error(self, text):
        self.set_working(False)
        self.log_task(text)
