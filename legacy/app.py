"""
Legacy Flask/SocketIO prototype.
Not the production entrypoint.
Use main.py for the desktop application.
"""
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parent.parent / 'app.py'
if SOURCE.exists():
    shutil.copy2(SOURCE, Path(__file__))
