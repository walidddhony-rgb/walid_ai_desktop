"""
Theme Customization Dialog for Walid AI Desktop.

Features:
- Light/Dark mode toggle with smooth transitions
- Accent color picker
- Font size adjustment
- Density settings (compact/comfortable)
- Theme preview
- Import/Export themes
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QFrame, QGridLayout, QSpacerItem,
    QSizePolicy, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class ThemeDialog(QDialog):
    """Theme customization dialog with live preview."""
    
    # Signals
    theme_changed = pyqtSignal(dict)  # Emitted when theme settings change
    
    def __init__(self, parent=None, current_theme: dict = None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Theme Customization")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)
        
        self.current_theme = current_theme or self._get_default_theme()
        self.preview_theme = self.current_theme.copy()
        
        self._init_ui()
        self._load_theme()
    
    def _get_default_theme(self) -> dict:
        """Get default theme settings."""
        return {
            'mode': 'Dark',  # Light, Dark, System
            'accent_color': '#3b82f6',  # Blue
            'font_size': 12,
            'density': 'Comfortable',  # Compact, Comfortable
            'border_radius': 6,
        }
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🎨 Theme Customization")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Mode selection
        mode_group = self._create_mode_group()
        layout.addWidget(mode_group)
        
        # Accent color picker
        color_group = self._create_color_group()
        layout.addWidget(color_group)
        
        # Font size slider
        font_group = self._create_font_group()
        layout.addWidget(font_group)
        
        # Density settings
        density_group = self._create_density_group()
        layout.addWidget(density_group)
        
        # Preview section
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group, 1)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # Spacer
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Export theme
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self._export_theme)
        button_layout.addWidget(export_btn)
        
        # Import theme
        import_btn = QPushButton("📂 Import")
        import_btn.clicked.connect(self._import_theme)
        button_layout.addWidget(import_btn)
        
        # Reset to defaults
        reset_btn = QPushButton("↺ Reset")
        reset_btn.clicked.connect(self._reset_theme)
        button_layout.addWidget(reset_btn)
        
        # Cancel
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Apply
        apply_btn = QPushButton("✓ Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply_theme)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
    
    def _create_mode_group(self) -> QFrame:
        """Create mode selection group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("border-radius: 8px; padding: 12px;")
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("🌙 Mode")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['Dark', 'Light', 'System'])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        return frame
    
    def _create_color_group(self) -> QFrame:
        """Create accent color picker group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("border-radius: 8px; padding: 12px;")
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("🎨 Accent Color")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Color buttons grid
        color_layout = QGridLayout()
        
        colors = [
            ('#3b82f6', 'Blue'),
            ('#22c55e', 'Green'),
            ('#f59e0b', 'Amber'),
            ('#ef4444', 'Red'),
            ('#8b5cf6', 'Purple'),
            ('#ec4899', 'Pink'),
            ('#06b6d4', 'Cyan'),
            ('#f97316', 'Orange'),
        ]
        
        self.color_buttons = []
        for i, (color, name) in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(60, 40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid {'#fff' if color in ['#22c55e', '#f97316'] else '#000'};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border: 3px solid #000;
                }}
            """)
            btn.setToolTip(name)
            btn.clicked.connect(lambda checked, c=color: self._on_color_selected(c))
            self.color_buttons.append(btn)
            color_layout.addWidget(btn, i // 4, i % 4)
        
        layout.addLayout(color_layout)
        
        # Current color indicator
        self.current_color_label = QLabel("Current: #3b82f6 (Blue)")
        self.current_color_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.current_color_label)
        
        return frame
    
    def _create_font_group(self) -> QFrame:
        """Create font size group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("border-radius: 8px; padding: 12px;")
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("📏 Font Size")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(10, 18)
        self.font_slider.setValue(12)
        self.font_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_slider.setTickInterval(2)
        self.font_slider.valueChanged.connect(self._on_font_changed)
        layout.addWidget(self.font_slider)
        
        self.font_value_label = QLabel("12 px")
        self.font_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_value_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.font_value_label)
        
        return frame
    
    def _create_density_group(self) -> QFrame:
        """Create density settings group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("border-radius: 8px; padding: 12px;")
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("📐 Density")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.density_combo = QComboBox()
        self.density_combo.addItems(['Compact', 'Comfortable'])
        self.density_combo.currentTextChanged.connect(self._on_density_changed)
        layout.addWidget(self.density_combo)
        
        desc = QLabel("Compact: More content on screen\nComfortable: More spacing")
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #6b7280;")
        layout.addWidget(desc)
        
        return frame
    
    def _create_preview_group(self) -> QFrame:
        """Create theme preview group."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("border-radius: 8px; padding: 12px;")
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("👁 Preview")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Preview panel
        self.preview_panel = QFrame()
        self.preview_panel.setFixedHeight(150)
        self.preview_panel.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 8px;
            }
        """)
        
        preview_layout = QVBoxLayout(self.preview_panel)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        
        # Preview content
        preview_title = QLabel("Preview Title")
        preview_title.setStyleSheet("color: #f3f4f6; font-size: 16px; font-weight: bold;")
        preview_layout.addWidget(preview_title)
        
        preview_text = QLabel("This is how your text will look with the current theme settings.")
        preview_text.setStyleSheet("color: #9ca3af; font-size: 12px;")
        preview_text.setWordWrap(True)
        preview_layout.addWidget(preview_text)
        
        # Preview button
        preview_btn = QPushButton("Preview Button")
        preview_btn.setFixedHeight(32)
        preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_theme['accent_color']};
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
        preview_layout.addWidget(preview_btn)
        
        layout.addWidget(self.preview_panel)
        
        return frame
    
    def _load_theme(self):
        """Load current theme into UI controls."""
        t = self.current_theme
        
        self.mode_combo.setCurrentText(t.get('mode', 'Dark'))
        self.font_slider.setValue(t.get('font_size', 12))
        self.density_combo.setCurrentText(t.get('density', 'Comfortable'))
        
        # Set accent color
        accent = t.get('accent_color', '#3b82f6')
        self._on_color_selected(accent)
        
        self._update_preview()
    
    def _on_mode_changed(self, mode: str):
        """Handle mode change."""
        self.preview_theme['mode'] = mode
        self._update_preview()
    
    def _on_color_selected(self, color: str):
        """Handle accent color selection."""
        self.preview_theme['accent_color'] = color
        
        # Update label
        color_names = {
            '#3b82f6': 'Blue',
            '#22c55e': 'Green',
            '#f59e0b': 'Amber',
            '#ef4444': 'Red',
            '#8b5cf6': 'Purple',
            '#ec4899': 'Pink',
            '#06b6d4': 'Cyan',
            '#f97316': 'Orange',
        }
        name = color_names.get(color, color)
        self.current_color_label.setText(f"Current: {color} ({name})")
        
        self._update_preview()
    
    def _on_font_changed(self, value: int):
        """Handle font size change."""
        self.preview_theme['font_size'] = value
        self.font_value_label.setText(f"{value} px")
        self._update_preview()
    
    def _on_density_changed(self, density: str):
        """Handle density change."""
        self.preview_theme['density'] = density
        self._update_preview()
    
    def _update_preview(self):
        """Update preview panel with current theme."""
        t = self.preview_theme
        
        # Update preview panel background
        bg_color = '#1f2937' if t['mode'] == 'Dark' else '#f9fafb'
        text_color = '#f3f4f6' if t['mode'] == 'Dark' else '#111827'
        muted_color = '#9ca3af' if t['mode'] == 'Dark' else '#6b7280'
        
        self.preview_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """)
        
        # Update preview button
        for btn in self.preview_panel.findChildren(QPushButton):
            if btn.text() == "Preview Button":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['accent_color']};
                        color: white;
                        border-radius: {t.get('border_radius', 6)}px;
                        font-weight: bold;
                        font-size: {t['font_size']}px;
                    }}
                """)
    
    def _apply_theme(self):
        """Apply theme and close dialog."""
        self.current_theme = self.preview_theme.copy()
        self.theme_changed.emit(self.current_theme)
        self.accept()
    
    def _reset_theme(self):
        """Reset theme to defaults."""
        self.current_theme = self._get_default_theme()
        self.preview_theme = self.current_theme.copy()
        self._load_theme()
    
    def _export_theme(self):
        """Export theme to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Theme", "", "JSON Files (*.json)"
        )
        
        if file_path:
            import json
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.current_theme, f, indent=2)
                QMessageBox.information(self, "Success", "Theme exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export theme: {e}")
    
    def _import_theme(self):
        """Import theme from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Theme", "", "JSON Files (*.json)"
        )
        
        if file_path:
            import json
            try:
                with open(file_path, 'r') as f:
                    theme = json.load(f)
                
                self.current_theme = theme
                self.preview_theme = theme.copy()
                self._load_theme()
                QMessageBox.information(self, "Success", "Theme imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import theme: {e}")


# Quick test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = ThemeDialog()
    dialog.exec()
    sys.exit()
