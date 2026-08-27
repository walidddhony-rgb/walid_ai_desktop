"""Dark and light QSS themes."""

DARK_THEME = """
QMainWindow,QWidget{background:#1e1e2e;color:#e0e0e0}
QPushButton{background:#3b3b4f;border:none;padding:8px 16px;border-radius:6px;font-weight:bold}
QPushButton:hover{background:#4a4a5f}QPushButton:checked{background:#4CAF50}
QTextEdit,QLineEdit{background:#2a2a3e;border:1px solid #444;padding:6px;border-radius:4px}
QListWidget{background:#252538;border:1px solid #333;border-radius:6px}
QListWidget::item{padding:8px}
QListWidget::item:selected{background:#4CAF50}
QScrollArea{background:#1e1e2e;border:none}
QFrame#user{background:#29293b;border-radius:10px;padding:10px;margin:5px}
QFrame#assistant{background:#2a2a3e;border:1px solid #444;border-radius:10px;padding:10px;margin:5px}
QFrame#tool{background:#1a1a2e;border:1px solid #555;border-radius:6px;padding:6px;margin:3px}
QLabel{color:#e0e0e0}
QMenuBar{background:#2a2a3e;color:#e0e0e0}
QMenu{background:#2a2a3e;color:#e0e0e0}
"""

LIGHT_THEME = """
QMainWindow,QWidget{background:#f5f5f5;color:#333}
QPushButton{background:#4CAF50;border:none;padding:8px 16px;border-radius:6px;font-weight:bold;color:white}
QPushButton:hover{background:#45a049}QPushButton:checked{background:#2E7D32}
QTextEdit,QLineEdit{background:white;border:1px solid #ccc;padding:6px;border-radius:4px}
QListWidget{background:white;border:1px solid #ddd;border-radius:6px}
QListWidget::item{padding:8px}
QListWidget::item:selected{background:#4CAF50;color:white}
QScrollArea{background:#f5f5f5;border:none}
QFrame#user{background:#e3f2fd;border-radius:10px;padding:10px;margin:5px}
QFrame#assistant{background:#fff;border:1px solid #ddd;border-radius:10px;padding:10px;margin:5px}
QFrame#tool{background:#f0f0f0;border:1px solid #ccc;border-radius:6px;padding:6px;margin:3px}
QLabel{color:#333}
QMenuBar{background:#fff;color:#333}
QMenu{background:#fff;color:#333}
"""
