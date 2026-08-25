#!/usr/bin/env python3
"""Walid AI Desktop v7 — تطبيق سطح مكتب محلي مع وكيل نظام."""
import sys,os,json,uuid,shutil,re,sqlite3
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QTextEdit,QLineEdit,QPushButton,QListWidget,QListWidgetItem,QLabel,QFileDialog,QMessageBox,QSplitter,QFrame,QSizePolicy,QScrollArea,QInputDialog,QMenu,QMenuBar,QComboBox)
from PyQt6.QtCore import Qt,QThread,pyqtSignal,QSize,QTimer
from PyQt6.QtGui import QFont,QIcon,QAction,QKeyEvent
import requests,subprocess

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document
except ImportError:
    Document = None
try:
    import speech_recognition as sr
except ImportError:
    sr = None

DB_PATH = Path('data/walid_ai.db')
UPLOADS = Path('uploads')
DB_PATH.parent.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)

# تعريفات أوضاع البحث
SEARCH_MODES = {
    'quick': '⚡ سريع',
    'advanced': '🔎 متقدم',
    'code': '💻 كود',
    'deep': '🧠 عميق',
    'web': '🌐 ويب',
    'academic': '🎓 أكاديمي',
}

MODE_PROMPTS = {
    'quick': 'أعطِ إجابة سريعة ومباشرة وموجزة.',
    'advanced': 'ابحث بعمق وقدّم إجابة مفصلة مع تحليل شامل.',
    'code': 'ركّز على الكود البرمجي: اكتب، حلّل، صحّح، أو اشرح الكود مع أمثلة عملية.',
    'deep': 'حلّل الموضوع بعمق في عدة خطوات وقدّم إجابة منظمة ومفصلة.',
    'web': 'ابحث في الويب وقدّم معلومات محدّثة مع الإشارة للمصادر.',
    'academic': 'ابحث في المصادر الأكاديمية والدراسات العلمية وقدّم إجابات مرجعية.',
}

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.init()

    def init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,conversation_id TEXT,role TEXT,content TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS uploaded_files(id INTEGER PRIMARY KEY,conversation_id TEXT,filename TEXT,path TEXT,file_type TEXT,size INTEGER,extracted_text TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS archives(id INTEGER PRIMARY KEY,original_path TEXT,archive_path TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,message_id INTEGER,rating TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY,key TEXT,value TEXT,created_at TEXT);
        """)
        self.conn.commit()

    def convs(self):
        return [dict(r) for r in self.conn.execute('SELECT * FROM conversations ORDER BY updated_at DESC')]

    def conv(self, cid):
        return [dict(r) for r in self.conn.execute('SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id', (cid,))]

    def add_conv(self, title, cid=None):
        cid = cid or str(uuid.uuid4())
        now = datetime.now().isoformat()
        self.conn.execute('INSERT INTO conversations VALUES(?,?,?,?)', (cid, title, now, now))
        self.conn.commit()
        return cid

    def add_msg(self, cid, role, content):
        now = datetime.now().isoformat()
        cur = self.conn.execute('INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)', (cid, role, content, now))
        self.conn.execute('UPDATE conversations SET updated_at=? WHERE id=?', (now, cid))
        self.conn.commit()
        return cur.lastrowid

    def add_file(self, cid, filename, path, ext, size, text):
        now = datetime.now().isoformat()
        cur = self.conn.execute('INSERT INTO uploaded_files(conversation_id,filename,path,file_type,size,extracted_text,created_at) VALUES(?,?,?,?,?,?,?)', (cid, filename, str(path), ext, size, text, now))
        self.conn.commit()
        return cur.lastrowid

    def files(self, cid):
        return [dict(r) for r in self.conn.execute('SELECT id,filename,file_type,size,created_at FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC', (cid,))]

    def delete_file(self, fid):
        row = self.conn.execute('SELECT path FROM uploaded_files WHERE id=?', (fid,)).fetchone()
        self.conn.execute('DELETE FROM uploaded_files WHERE id=?', (fid,))
        self.conn.commit()
        if row:
            try:
                Path(row['path']).unlink(missing_ok=True)
            except Exception:
                pass

    def search_convs(self, q):
        return [dict(r) for r in self.conn.execute('SELECT * FROM conversations WHERE title LIKE ?', ('%' + q + '%',))]

    def add_feedback(self, mid, rating):
        now = datetime.now().isoformat()
        self.conn.execute('INSERT INTO feedback(message_id,rating,created_at) VALUES(?,?,?)', (mid, rating, now))
        self.conn.commit()

    def add_memory(self, key, value):
        now = datetime.now().isoformat()
        existing = self.conn.execute('SELECT id FROM memory WHERE key=?', (key,)).fetchone()
        if existing:
            self.conn.execute('UPDATE memory SET value=?,created_at=? WHERE id=?', (value, now, existing['id']))
        else:
            self.conn.execute('INSERT INTO memory(key,value,created_at) VALUES(?,?,?)', (key, value, now))
        self.conn.commit()

    def get_all_memory(self):
        rows = self.conn.execute('SELECT key,value FROM memory').fetchall()
        return {r['key']: r['value'] for r in rows}

db = Database()


class StreamWorker(QThread):
    chunk = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, msg, files, selected_modes, regenerate=False, memory_text=''):
        super().__init__()
        self.msg = msg
        self.files = files
        self.selected_modes = selected_modes
        self.regenerate = regenerate
        self.memory_text = memory_text
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            ctx = '\n\n'.join(f'ملف: {f["filename"]}\n{f["extracted_text"][:7000]}' for f in self.files if f.get('extracted_text'))
            # بناء الـ prompt من الأوضاع المختارة
            mode_parts = []
            for m in self.selected_modes:
                if m in MODE_PROMPTS:
                    mode_parts.append(MODE_PROMPTS[m])
            prompt = 'أنت Walid AI Desktop، مساعد محلي ذكي. أجب بالعربية.'
            if mode_parts:
                prompt += '\n\nتعليمات البحث:\n' + '\n'.join(f'- {p}' for p in mode_parts)
            if self.regenerate:
                prompt += '\nأعد صياغة الإجابة بطريقة مختلفة تمامًا مع الحفاظ على المعنى.'
            if self.memory_text:
                prompt += '\n\nمعلومات تعلمتها من المستخدم:\n' + self.memory_text
            if ctx:
                prompt += '\n\nمحتوى الملفات:\n' + ctx
            r = requests.post(
                'http://127.0.0.1:11434/api/chat',
                json={'model': 'qwen2.5:7b', 'stream': True, 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': self.msg}]},
                timeout=300,
                stream=True
            )
            r.raise_for_status()
            for line in r.iter_lines():
                if self._stop:
                    break
                if line:
                    data = json.loads(line)
                    if data.get('message', {}).get('content', ''):
                        self.chunk.emit(data['message']['content'])
                    if data.get('done', False):
                        break
            self.finished_signal.emit(0)
        except Exception as e:
            self.error.emit(str(e))


class LearnWorker(QThread):
    done = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, msg, memory_text, selected_modes):
        super().__init__()
        self.msg = msg
        self.memory_text = memory_text
        self.selected_modes = selected_modes

    def run(self):
        try:
            mode_str = ', '.join(self.selected_modes)
            prompt = f'تحليل طلب المستخدم (أوضاع البحث المختارة: {mode_str}). هل يحتوي الطلب على معلومة أو حقيقة أو تفضيل يجب حفظه في الذاكرة؟ إذا نعم، أرجع JSON بصيغة: {{"key":"عنوان مختصر بالعربية","value":"المعلومة"}}. إذا لا، أرجع: {{"key":"","value":""}}.'
            full_prompt = prompt
            if self.memory_text:
                full_prompt += '\nمعلومات موجودة بالفعل:\n' + self.memory_text
            r = requests.post(
                'http://127.0.0.1:11434/api/chat',
                json={'model': 'qwen2.5:7b', 'stream': False, 'messages': [{'role': 'system', 'content': full_prompt}, {'role': 'user', 'content': self.msg}]},
                timeout=60
            )
            r.raise_for_status()
            content = r.json()['message']['content'].strip()
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                self.done.emit(data.get('key', ''), data.get('value', ''))
            else:
                self.done.emit('', '')
        except Exception as e:
            self.error.emit(str(e))


class SystemAgent:
    @staticmethod
    def create_file(path, content):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return str(p)

    @staticmethod
    def create_dir(path):
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    @staticmethod
    def archive_folder(src, dest):
        src = Path(src)
        dest = Path(dest)
        shutil.make_archive(str(dest), 'zip', src)
        return str(dest) + '.zip'


class MessageFrame(QFrame):
    def __init__(self, role, text, on_copy, on_like=None, on_dislike=None, on_regenerate=None, msg_id=None):
        super().__init__()
        self.setObjectName(role)
        self.msg_id = msg_id
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label = label
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton('📋 نسخ')
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(on_copy)
        btn_layout.addWidget(copy_btn)
        if role == 'assistant':
            like_btn = QPushButton('👍')
            like_btn.setFixedWidth(40)
            like_btn.clicked.connect(on_like)
            btn_layout.addWidget(like_btn)
            dislike_btn = QPushButton('👎')
            dislike_btn.setFixedWidth(40)
            dislike_btn.clicked.connect(on_dislike)
            btn_layout.addWidget(dislike_btn)
            regen_btn = QPushButton('🔄 أعد')
            regen_btn.setFixedWidth(60)
            regen_btn.clicked.connect(on_regenerate)
            btn_layout.addWidget(regen_btn)
        btn_layout.addStretch()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(label)
        main_layout.addLayout(btn_layout)


class InputTextEdit(QTextEdit):
    """حقل إدخال متعدد الأسطر: Enter للإرسال، Shift+Enter لسطر جديد."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setPlaceholderText('اكتب أو تحدث... (Enter للإرسال، Shift+Enter لسطر جديد)')
        self.setFixedHeight(80)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.callback()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Walid AI Desktop v7')
        self.setMinimumSize(1400, 900)
        self.cid = None
        self.worker = None
        self.learn_worker = None
        self.dark_mode = True
        self.selected_modes = ['quick']
        self.last_msg = None
        self.current_assistant_label = None
        self.current_assistant_text = ''
        self.setup_ui()
        self.setup_menu()
        self.apply_theme()
        self.load_convs()
        if sr:
            self.recog = sr.Recognizer()
        else:
            self.recog = None

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # شريط الأوضاع — أزرار قابلة للاختيار المتعدد
        top_bar = QHBoxLayout()
        self.mode_buttons = {}
        for key, label in SEARCH_MODES.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self.toggle_mode(k))
            self.mode_buttons[key] = btn
            top_bar.addWidget(btn)
        # تفعيل السريع افتراضيًا
        self.mode_buttons['quick'].setChecked(True)
        top_bar.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('بحث في المحادثات...')
        self.search_input.textChanged.connect(self.do_search)
        self.theme_btn = QPushButton('🌙 داكن')
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(self.theme_btn)
        main_layout.addLayout(top_bar)

        # شريط يُظهر الأوضاع المختارة حاليًا
        self.mode_status = QLabel('الأوضاع المختارة: ⚡ سريع')
        self.mode_status.setStyleSheet('color:#FF9800;font-size:11px;padding:2px 8px')
        main_layout.addWidget(self.mode_status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        center = QWidget()
        right = QWidget()
        left.setFixedWidth(280)
        right.setFixedWidth(320)

        lv = QVBoxLayout(left)
        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self.load_conv)
        lv.addWidget(self.conv_list)
        self.new_btn = QPushButton('+ محادثة جديدة')
        self.new_btn.clicked.connect(self.new_conv)
        lv.addWidget(self.new_btn)
        self.export_btn = QPushButton('📤 تصدير')
        self.export_btn.clicked.connect(self.export_conv)
        lv.addWidget(self.export_btn)
        self.mem_btn = QPushButton('🧠 الذاكرة')
        self.mem_btn.clicked.connect(self.show_memory)
        lv.addWidget(self.mem_btn)

        cv = QVBoxLayout(center)
        self.status = QLabel('● جاهز')
        self.status.setStyleSheet('font-weight:bold;color:#4CAF50')
        cv.addWidget(self.status)
        self.chat = QScrollArea()
        self.chat.setWidgetResizable(True)
        self.chat.setMinimumHeight(680)
        self.chat.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.chat_content = QWidget()        
        self.chat.setWidget(self.chat_content)
        self.chat_layout = QVBoxLayout(self.chat_content)
        cv.addWidget(self.chat)
        input_row = QHBoxLayout()
        self.mic_btn = QPushButton('🎤')
        self.mic_btn.setFixedWidth(50)
        self.mic_btn.clicked.connect(self.start_mic)
        input_row.addWidget(self.mic_btn)
        self.input = InputTextEdit(self.send)
        input_row.addWidget(self.input)
        self.send_btn = QPushButton('إرسال')
        self.send_btn.clicked.connect(self.send)
        input_row.addWidget(self.send_btn)
        self.stop_btn = QPushButton('■ إيقاف')
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.hide()
        input_row.addWidget(self.stop_btn)
        cv.addLayout(input_row)

        rv = QVBoxLayout(right)
        self.file_list = QListWidget()
        rv.addWidget(self.file_list)
        self.up_btn = QPushButton('📎 رفع ملفات')
        self.up_btn.clicked.connect(self.upload)
        rv.addWidget(self.up_btn)
        self.arch_btn = QPushButton('🗄 أرشفة مجلد')
        self.arch_btn.clicked.connect(self.archive)
        rv.addWidget(self.arch_btn)
        self.create_btn = QPushButton('📄 إنشاء ملف')
        self.create_btn.clicked.connect(self.create_file_wiz)
        rv.addWidget(self.create_btn)
        self.mkdir_btn = QPushButton('📁 إنشاء مجلد')
        self.mkdir_btn.clicked.connect(self.mkdir_wiz)
        rv.addWidget(self.mkdir_btn)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        main_layout.addWidget(splitter)

    def toggle_mode(self, key):
        """تبديل اختيار الوضع (اختيار متعدد)."""
        btn = self.mode_buttons[key]
        if btn.isChecked():
            if key not in self.selected_modes:
                self.selected_modes.append(key)
        else:
            if key in self.selected_modes:
                self.selected_modes.remove(key)
        # ضمان وجود وضع واحد على الأقل
        if not self.selected_modes:
            self.selected_modes = ['quick']
            self.mode_buttons['quick'].setChecked(True)
        self.update_mode_status()

    def update_mode_status(self):
        labels = [SEARCH_MODES[m] for m in self.selected_modes if m in SEARCH_MODES]
        self.mode_status.setText('الأوضاع المختارة: ' + ' + '.join(labels))

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('ملف')
        new_action = QAction('محادثة جديدة', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_conv)
        file_menu.addAction(new_action)
        export_action = QAction('تصدير', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_conv)
        file_menu.addAction(export_action)
        edit_menu = menubar.addMenu('تعديل')
        theme_action = QAction('الوضع الداكن', self)
        theme_action.setShortcut('Ctrl+T')
        theme_action.triggered.connect(self.toggle_theme)
        edit_menu.addAction(theme_action)

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow,QWidget{background:#1e1e2e;color:#e0e0e0}
                QPushButton{background:#3b3b4f;border:none;padding:8px 16px;border-radius:6px;font-weight:bold}
                QPushButton:hover{background:#4a4a5f}
                QPushButton:checked{background:#4CAF50}
                QTextEdit,QLineEdit,QComboBox{background:#2a2a3e;border:1px solid #444;padding:6px;border-radius:4px}
                QListWidget{background:#252538;border:1px solid #333;border-radius:6px}
                QListWidget::item{padding:8px;border-radius:4px}
                QListWidget::item:selected{background:#4CAF50}
                QScrollArea{background:#1e1e2e;border:none}
                QFrame#user{background:#29293b;border-radius:10px;padding:10px;margin:5px}
                QFrame#assistant{background:#2a2a3e;border:1px solid #444;border-radius:10px;padding:10px;margin:5px}
                QLabel{color:#e0e0e0}
                QMenuBar{background:#2a2a3e;color:#e0e0e0}
                QMenu{background:#2a2a3e;color:#e0e0e0}
            """)
        else:
            self.setStyleSheet("""
                QMainWindow,QWidget{background:#f5f5f5;color:#333}
                QPushButton{background:#4CAF50;border:none;padding:8px 16px;border-radius:6px;font-weight:bold;color:white}
                QPushButton:hover{background:#45a049}
                QPushButton:checked{background:#2E7D32}
                QTextEdit,QLineEdit,QComboBox{background:white;border:1px solid #ccc;padding:6px;border-radius:4px}
                QListWidget{background:white;border:1px solid #ddd;border-radius:6px}
                QListWidget::item{padding:8px;border-radius:4px}
                QListWidget::item:selected{background:#4CAF50;color:white}
                QScrollArea{background:#f5f5f5;border:none}
                QFrame#user{background:#e3f2fd;border-radius:10px;padding:10px;margin:5px}
                QFrame#assistant{background:#ffffff;border:1px solid #ddd;border-radius:10px;padding:10px;margin:5px}
                QLabel{color:#333}
                QMenuBar{background:#fff;color:#333}
                QMenu{background:#fff;color:#333}
            """)

    def do_search(self, q):
        if not q:
            self.load_convs()
            return
        results = db.search_convs(q)
        self.conv_list.clear()
        for r in results:
            self.conv_list.addItem(r['title'])

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_btn.setText('☀️ فاتح' if self.dark_mode else '🌙 داكن')
        self.apply_theme()

    def add_msg_widget(self, role, text, msg_id=None):
        def on_copy():
            QApplication.clipboard().setText(text)
            self.status.setText('✓ تم النسخ')
        def on_like():
            if msg_id:
                db.add_feedback(msg_id, 'like')
            self.status.setText('👍 تم التقييم')
        def on_dislike():
            if msg_id:
                db.add_feedback(msg_id, 'dislike')
            self.status.setText('👎 تم التقييم')
        def on_regenerate():
            if self.last_msg:
                self.send(regenerate=True)
        frame = MessageFrame(role, text, on_copy, on_like if role == 'assistant' else None, on_dislike if role == 'assistant' else None, on_regenerate if role == 'assistant' else None, msg_id)
        self.chat_layout.addWidget(frame)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())
        return frame

    def add_streaming_assistant_frame(self):
        def on_copy():
            QApplication.clipboard().setText(self.current_assistant_text)
            self.status.setText('✓ تم النسخ')
        def on_like():
            if hasattr(self, '_pending_mid') and self._pending_mid:
                db.add_feedback(self._pending_mid, 'like')
            self.status.setText('👍 تم التقييم')
        def on_dislike():
            if hasattr(self, '_pending_mid') and self._pending_mid:
                db.add_feedback(self._pending_mid, 'dislike')
            self.status.setText('👎 تم التقييم')
        def on_regenerate():
            if self.last_msg:
                self.send(regenerate=True)
        label = QLabel('...')
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton('📋 نسخ')
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(on_copy)
        btn_layout.addWidget(copy_btn)
        like_btn = QPushButton('👍')
        like_btn.setFixedWidth(40)
        like_btn.clicked.connect(on_like)
        btn_layout.addWidget(like_btn)
        dislike_btn = QPushButton('👎')
        dislike_btn.setFixedWidth(40)
        dislike_btn.clicked.connect(on_dislike)
        btn_layout.addWidget(dislike_btn)
        regen_btn = QPushButton('🔄 أعد')
        regen_btn.setFixedWidth(60)
        regen_btn.clicked.connect(on_regenerate)
        btn_layout.addWidget(regen_btn)
        btn_layout.addStretch()
        frame = QFrame()
        frame.setObjectName('assistant')
        fl = QVBoxLayout(frame)
        fl.addWidget(label)
        fl.addLayout(btn_layout)
        self.chat_layout.addWidget(frame)
        self.current_assistant_label = label
        self.current_assistant_text = ''
        self._pending_mid = None
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())
        return frame

    def on_chunk(self, chunk_text):
        self.current_assistant_text += chunk_text
        if self.current_assistant_label:
            self.current_assistant_label.setText(self.current_assistant_text)
            self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def on_stream_done(self, _):
        text = self.current_assistant_text.strip()
        if text and self.cid:
            mid = db.add_msg(self.cid, 'assistant', text)
            self._pending_mid = mid
        self.status.setText('● جاهز')
        self.status.setStyleSheet('color:#4CAF50;font-weight:bold')
        self.send_btn.show()
        self.stop_btn.hide()
        if text:
            self.speak(text)
        self.current_assistant_label = None
        self.current_assistant_text = ''

    def on_learn_done(self, key, value):
        if key and value:
            db.add_memory(key, value)

    def on_learn_error(self, e):
        pass

    def send(self, regenerate=False):
        msg = self.input.toPlainText().strip()
        if not msg and not regenerate:
            return
        if not regenerate:
            self.input.clear()
            self.add_msg_widget('user', msg)
            self.status.setText('● جارٍ التحليل...')
            self.status.setStyleSheet('color:#FF9800;font-weight:bold')
            self.send_btn.hide()
            self.stop_btn.show()
            if not self.cid:
                self.cid = db.add_conv(msg[:55] or 'محادثة جديدة')
            db.add_msg(self.cid, 'user', msg)
            self.last_msg = msg
            mem = db.get_all_memory()
            mem_text = '\n'.join(f'{k}: {v}' for k, v in mem.items()) if mem else ''
            self.learn_worker = LearnWorker(msg, mem_text, self.selected_modes)
            self.learn_worker.done.connect(self.on_learn_done)
            self.learn_worker.error.connect(self.on_learn_error)
            self.learn_worker.start()
        else:
            self.status.setText('● جارٍ إعادة الصياغة...')
            self.status.setStyleSheet('color:#FF9800;font-weight:bold')
            self.send_btn.hide()
            self.stop_btn.show()
        cid = self.cid
        files = [dict(r) for r in db.conn.execute('SELECT * FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC LIMIT 3', (cid,))]
        mem = db.get_all_memory()
        mem_text = '\n'.join(f'{k}: {v}' for k, v in mem.items()) if mem else ''
        self.add_streaming_assistant_frame()
        self.worker = StreamWorker(self.last_msg or msg, files, list(self.selected_modes), regenerate, mem_text)
        self.worker.chunk.connect(self.on_chunk)
        self.worker.finished_signal.connect(self.on_stream_done)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_error(self, e):
        self.add_msg_widget('assistant', 'خطأ: ' + e)
        self.status.setText('● خطأ')
        self.status.setStyleSheet('color:#F44336;font-weight:bold')
        self.send_btn.show()
        self.stop_btn.hide()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker.terminate()
            self.status.setText('● تم الإيقاف')
            self.send_btn.show()
            self.stop_btn.hide()

    def speak(self, text):
        try:
            subprocess.run(['powershell', '-c', f'Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text[:500]}")'], shell=True, timeout=15)
        except Exception:
            pass

    def start_mic(self):
        if not self.recog:
            return
        with sr.Microphone() as src:
            self.status.setText('● تحدث الآن...')
            audio = self.recog.listen(src)
            try:
                text = self.recog.recognize_google(audio, language='ar-SA')
                self.input.setText(text)
                self.send()
            except Exception as e:
                self.status.setText('خطأ: ' + str(e))

    def load_convs(self):
        self.conv_list.clear()
        for c in db.convs():
            self.conv_list.addItem(c['title'])

    def load_conv(self, item):
        cid = db.convs()[self.conv_list.currentRow()]['id']
        self.cid = cid
        self.clear_chat()
        for m in db.conv(cid):
            self.add_msg_widget(m['role'], m['content'], m['id'])
        self.file_list.clear()
        for f in db.files(cid):
            self.file_list.addItem(f['filename'])

    def clear_chat(self):
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def new_conv(self):
        self.cid = None
        self.clear_chat()
        self.file_list.clear()
        self.status.setText('● جاهز')

    def export_conv(self):
        if not self.cid:
            return
        msgs = db.conv(self.cid)
        txt = '\n\n'.join(m['role'].upper() + ': ' + m['content'] for m in msgs)
        path, _ = QFileDialog.getSaveFileName(self, 'تصدير المحادثة', '', 'Text Files (*.txt)')
        if path:
            Path(path).write_text(txt, encoding='utf-8')

    def upload(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'رفع ملفات', '', 'All Files (*.*)')
        if not files:
            return
        for f in files:
            p = Path(f)
            ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
            text = '[ملف]'
            if ext in ('txt', 'md'):
                text = p.read_text()[:15000]
            elif ext == 'pdf' and PdfReader:
                text = '\n'.join(x.extract_text() or '' for x in PdfReader(str(p)).pages)[:15000]
            elif ext == 'docx' and Document:
                text = '\n'.join(x.text for x in Document(str(p)).paragraphs)[:15000]
            if not self.cid:
                self.cid = db.add_conv('محادثة جديدة')
            db.add_file(self.cid, p.name, p, ext, p.stat().st_size, text)
            self.file_list.addItem(p.name)

    def archive(self):
        folder = QFileDialog.getExistingDirectory(self, 'اختر مجلدًا للأرشفة')
        if not folder:
            return
        dest = QFileDialog.getExistingDirectory(self, 'اختر مجلد الوجهة') or 'archives'
        zip_path = SystemAgent.archive_folder(folder, dest)
        QMessageBox.information(self, 'تمت الأرشفة', f'تم حفظ الملف في:\n{zip_path}')

    def create_file_wiz(self):
        path, _ = QFileDialog.getSaveFileName(self, 'إنشاء ملف', '', 'Text Files (*.txt);;All Files (*.*)')
        if path:
            SystemAgent.create_file(path, 'محتوى جديد')
            QMessageBox.information(self, 'تم الإنشاء', f'تم إنشاء:\n{path}')

    def mkdir_wiz(self):
        name, ok = QInputDialog.getText(self, 'إنشاء مجلد', 'اسم المجلد:')
        if ok and name:
            path = Path.cwd() / name
            SystemAgent.create_dir(str(path))
            QMessageBox.information(self, 'تم الإنشاء', f'تم إنشاء:\n{path}')

    def show_memory(self):
        mem = db.get_all_memory()
        if not mem:
            QMessageBox.information(self, 'الذاكرة', 'لا توجد معلومات محفوظة بعد.')
            return
        text = '\n'.join(f'📌 {k}: {v}' for k, v in mem.items())
        QMessageBox.information(self, '🧠 ذاكرة Walid AI', text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont('Tahoma', 11))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
