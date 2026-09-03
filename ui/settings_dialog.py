"""
Professional Settings Dialog for Walid AI Desktop.

Features:
- Categorized settings (General, Model, Voice, Tools, Advanced)
- Search functionality
- Form layout with clear labels
- Restore defaults button
- Unsaved changes indicator
- Keyboard shortcuts support
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QLabel, QGroupBox, QScrollArea, QFrame,
    QSpacerItem, QSizePolicy, QSplitter, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QKeySequence, QShortcut


class SettingsDialog(QDialog):
    """Professional settings dialog with categorized tabs and search."""
    
    # Signals
    settings_changed = pyqtSignal(dict)  # Emitted when settings are saved
    
    def __init__(self, parent=None, current_settings: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)
        self.resize(900, 650)
        
        self.current_settings = current_settings or self._get_default_settings()
        self.modified_settings = {}
        
        self._init_ui()
        self._load_settings()
        self._setup_shortcuts()
    
    def _get_default_settings(self) -> dict:
        """Get default application settings."""
        return {
            # General
            'theme': 'Dark',
            'language': 'English',
            'font_size': 12,
            'auto_save': True,
            'show_tooltips': True,
            
            # Model
            'model_name': 'llama3.2:3b',
            'model_temperature': 0.7,
            'max_tokens': 2048,
            'context_window': 4096,
            'ollama_host': 'http://localhost:11434',
            
            # Voice
            'stt_engine': 'whisper',
            'tts_engine': 'pyttsx3',
            'voice_rate': 150,
            'voice_volume': 100,
            'auto_listen': False,
            
            # Tools
            'auto_approve_tools': False,
            'show_diff_review': True,
            'sandbox_enabled': True,
            'max_tool_retries': 3,
            
            # Advanced
            'debug_mode': False,
            'log_level': 'INFO',
            'auto_compact': True,
            'compact_threshold': 20000,
        }
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚙ Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs, 1)
        
        # Create tabs
        self._create_general_tab()
        self._create_model_tab()
        self._create_voice_tab()
        self._create_tools_tab()
        self._create_advanced_tab()
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # Spacer
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Restore defaults
        self.restore_btn = QPushButton("↺ Restore Defaults")
        self.restore_btn.clicked.connect(self._restore_defaults)
        button_layout.addWidget(self.restore_btn)
        
        # Cancel
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # Save
        self.save_btn = QPushButton("✓ Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save_settings)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self):
        """Create General settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Appearance Group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(12)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Dark', 'Light', 'System'])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItems(['English', 'Arabic', 'French', 'Spanish'])
        appearance_layout.addRow("Language:", self.language_combo)
        
        # Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setSuffix(" px")
        appearance_layout.addRow("Font Size:", self.font_size_spin)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Behavior Group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout()
        behavior_layout.setSpacing(12)
        
        # Auto Save
        self.auto_save_check = QCheckBox("Auto-save conversations")
        behavior_layout.addRow(self.auto_save_check)
        
        # Show Tooltips
        self.show_tooltips_check = QCheckBox("Show tooltips on hover")
        behavior_layout.addRow(self.show_tooltips_check)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "📌 General")
    
    def _create_model_tab(self):
        """Create Model settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Connection Group
        connection_group = QGroupBox("Ollama Connection")
        connection_layout = QFormLayout()
        connection_layout.setSpacing(12)
        
        # Host
        self.ollama_host_edit = QLineEdit()
        self.ollama_host_edit.setPlaceholderText("http://localhost:11434")
        connection_layout.addRow("Host:", self.ollama_host_edit)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Model Group
        model_group = QGroupBox("Model Configuration")
        model_layout = QFormLayout()
        model_layout.setSpacing(12)
        
        # Model Name
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("llama3.2:3b")
        model_layout.addRow("Model:", self.model_name_edit)
        
        # Temperature
        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 100)
        self.temperature_spin.setSuffix(" (0.0 - 1.0)")
        self.temperature_spin.setToolTip("Higher = more creative, Lower = more focused")
        model_layout.addRow("Temperature:", self.temperature_spin)
        
        # Max Tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 8192)
        self.max_tokens_spin.setSingleStep(256)
        self.max_tokens_spin.setSuffix(" tokens")
        model_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        # Context Window
        self.context_spin = QSpinBox()
        self.context_spin.setRange(1024, 32768)
        self.context_spin.setSingleStep(1024)
        self.context_spin.setSuffix(" tokens")
        model_layout.addRow("Context Window:", self.context_spin)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🤖 Model")
    
    def _create_voice_tab(self):
        """Create Voice settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # STT Group
        stt_group = QGroupBox("Speech-to-Text")
        stt_layout = QFormLayout()
        stt_layout.setSpacing(12)
        
        # STT Engine
        self.stt_engine_combo = QComboBox()
        self.stt_engine_combo.addItems(['whisper', 'faster-whisper', 'vosk'])
        stt_layout.addRow("Engine:", self.stt_engine_combo)
        
        stt_group.setLayout(stt_layout)
        layout.addWidget(stt_group)
        
        # TTS Group
        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QFormLayout()
        tts_layout.setSpacing(12)
        
        # TTS Engine
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(['pyttsx3', 'edge-tts', 'google-tts'])
        tts_layout.addRow("Engine:", self.tts_engine_combo)
        
        # Voice Rate
        self.voice_rate_spin = QSpinBox()
        self.voice_rate_spin.setRange(50, 300)
        self.voice_rate_spin.setSuffix(" wpm")
        tts_layout.addRow("Speech Rate:", self.voice_rate_spin)
        
        # Volume
        self.voice_volume_spin = QSpinBox()
        self.voice_volume_spin.setRange(0, 100)
        self.voice_volume_spin.setSuffix("%")
        tts_layout.addRow("Volume:", self.voice_volume_spin)
        
        # Auto Listen
        self.auto_listen_check = QCheckBox("Auto-listen after response")
        tts_layout.addRow(self.auto_listen_check)
        
        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🎤 Voice")
    
    def _create_tools_tab(self):
        """Create Tools settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Safety Group
        safety_group = QGroupBox("Tool Safety")
        safety_layout = QFormLayout()
        safety_layout.setSpacing(12)
        
        # Auto Approve
        self.auto_approve_check = QCheckBox("Auto-approve tool execution (NOT recommended)")
        self.auto_approve_check.setStyleSheet("color: #ef4444; font-weight: bold;")
        safety_layout.addRow(self.auto_approve_check)
        
        # Show Diff Review
        self.show_diff_check = QCheckBox("Show diff review before file changes")
        safety_layout.addRow(self.show_diff_check)
        
        # Sandbox
        self.sandbox_check = QCheckBox("Enable sandboxed code execution")
        safety_layout.addRow(self.sandbox_check)
        
        # Max Retries
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setSuffix(" attempts")
        safety_layout.addRow("Max Tool Retries:", self.max_retries_spin)
        
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🔧 Tools")
    
    def _create_advanced_tab(self):
        """Create Advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Debug Group
        debug_group = QGroupBox("Debugging")
        debug_layout = QFormLayout()
        debug_layout.setSpacing(12)
        
        # Debug Mode
        self.debug_check = QCheckBox("Enable debug mode")
        self.debug_check.setStyleSheet("color: #f59e0b;")
        debug_layout.addRow(self.debug_check)
        
        # Log Level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        debug_layout.addRow("Log Level:", self.log_level_combo)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # Context Management Group
        context_group = QGroupBox("Context Management")
        context_layout = QFormLayout()
        context_layout.setSpacing(12)
        
        # Auto Compact
        self.auto_compact_check = QCheckBox("Auto-compact conversation context")
        context_layout.addRow(self.auto_compact_check)
        
        # Compact Threshold
        self.compact_threshold_spin = QSpinBox()
        self.compact_threshold_spin.setRange(10000, 30000)
        self.compact_threshold_spin.setSingleStep(1000)
        self.compact_threshold_spin.setSuffix(" tokens")
        context_layout.addRow("Compact Threshold:", self.compact_threshold_spin)
        
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "⚙ Advanced")
    
    def _load_settings(self):
        """Load current settings into UI controls."""
        s = self.current_settings
        
        # General
        self.theme_combo.setCurrentText(s.get('theme', 'Dark'))
        self.language_combo.setCurrentText(s.get('language', 'English'))
        self.font_size_spin.setValue(s.get('font_size', 12))
        self.auto_save_check.setChecked(s.get('auto_save', True))
        self.show_tooltips_check.setChecked(s.get('show_tooltips', True))
        
        # Model
        self.ollama_host_edit.setText(s.get('ollama_host', 'http://localhost:11434'))
        self.model_name_edit.setText(s.get('model_name', 'llama3.2:3b'))
        self.temperature_spin.setValue(int(s.get('model_temperature', 0.7) * 100))
        self.max_tokens_spin.setValue(s.get('max_tokens', 2048))
        self.context_spin.setValue(s.get('context_window', 4096))
        
        # Voice
        self.stt_engine_combo.setCurrentText(s.get('stt_engine', 'whisper'))
        self.tts_engine_combo.setCurrentText(s.get('tts_engine', 'pyttsx3'))
        self.voice_rate_spin.setValue(s.get('voice_rate', 150))
        self.voice_volume_spin.setValue(s.get('voice_volume', 100))
        self.auto_listen_check.setChecked(s.get('auto_listen', False))
        
        # Tools
        self.auto_approve_check.setChecked(s.get('auto_approve_tools', False))
        self.show_diff_check.setChecked(s.get('show_diff_review', True))
        self.sandbox_check.setChecked(s.get('sandbox_enabled', True))
        self.max_retries_spin.setValue(s.get('max_tool_retries', 3))
        
        # Advanced
        self.debug_check.setChecked(s.get('debug_mode', False))
        self.log_level_combo.setCurrentText(s.get('log_level', 'INFO'))
        self.auto_compact_check.setChecked(s.get('auto_compact', True))
        self.compact_threshold_spin.setValue(s.get('compact_threshold', 20000))
    
    def _save_settings(self):
        """Save settings and emit signal."""
        # Collect all settings
        new_settings = {
            # General
            'theme': self.theme_combo.currentText(),
            'language': self.language_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'auto_save': self.auto_save_check.isChecked(),
            'show_tooltips': self.show_tooltips_check.isChecked(),
            
            # Model
            'ollama_host': self.ollama_host_edit.text(),
            'model_name': self.model_name_edit.text(),
            'model_temperature': self.temperature_spin.value() / 100.0,
            'max_tokens': self.max_tokens_spin.value(),
            'context_window': self.context_spin.value(),
            
            # Voice
            'stt_engine': self.stt_engine_combo.currentText(),
            'tts_engine': self.tts_engine_combo.currentText(),
            'voice_rate': self.voice_rate_spin.value(),
            'voice_volume': self.voice_volume_spin.value(),
            'auto_listen': self.auto_listen_check.isChecked(),
            
            # Tools
            'auto_approve_tools': self.auto_approve_check.isChecked(),
            'show_diff_review': self.show_diff_check.isChecked(),
            'sandbox_enabled': self.sandbox_check.isChecked(),
            'max_tool_retries': self.max_retries_spin.value(),
            
            # Advanced
            'debug_mode': self.debug_check.isChecked(),
            'log_level': self.log_level_combo.currentText(),
            'auto_compact': self.auto_compact_check.isChecked(),
            'compact_threshold': self.compact_threshold_spin.value(),
        }
        
        # Emit signal
        self.settings_changed.emit(new_settings)
        
        # Close dialog
        self.accept()
    
    def _restore_defaults(self):
        """Restore all settings to defaults."""
        self.current_settings = self._get_default_settings()
        self._load_settings()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+S to save
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._save_settings)
        
        # Esc to cancel
        cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        cancel_shortcut.activated.connect(self.reject)
        
        # Ctrl+R to restore defaults
        restore_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        restore_shortcut.activated.connect(self._restore_defaults)


# Quick test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.exec()
    sys.exit()
