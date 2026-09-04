"""Simple test suite for available UI components."""

import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QWidget

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*60)
print("Testing available UI components...")
print("="*60)

class TestAvailableComponents(unittest.TestCase):
    """Test components that should exist."""
    
    def test_status_bar(self):
        try:
            from ui.status_bar import StatusBar
            widget = StatusBar()
            self.assertIsInstance(widget, StatusBar)
            self.assertEqual(widget.fixedHeight(), 32)
            print("✅ StatusBar: OK")
        except Exception as e:
            print(f"❌ StatusBar: {e}")
            self.fail(f"StatusBar failed: {e}")
    
    def test_tool_status(self):
        try:
            from ui.tool_status import ToolStatusWidget
            widget = ToolStatusWidget()
            self.assertIsInstance(widget, ToolStatusWidget)
            print("✅ ToolStatusWidget: OK")
        except Exception as e:
            print(f"❌ ToolStatusWidget: {e}")
            self.fail(f"ToolStatusWidget failed: {e}")
    
    def test_settings_dialog(self):
        try:
            from ui.settings_dialog import SettingsDialog
            widget = SettingsDialog()
            self.assertIsInstance(widget, SettingsDialog)
            self.assertGreaterEqual(widget.tabs.count(), 5)
            print("✅ SettingsDialog: OK")
        except Exception as e:
            print(f"❌ SettingsDialog: {e}")
            self.fail(f"SettingsDialog failed: {e}")
    
    def test_theme_dialog(self):
        try:
            from ui.theme_dialog import ThemeDialog
            widget = ThemeDialog()
            self.assertIsInstance(widget, ThemeDialog)
            print("✅ ThemeDialog: OK")
        except Exception as e:
            print(f"❌ ThemeDialog: {e}")
            self.fail(f"ThemeDialog failed: {e}")
    
    def test_knowledge_widget(self):
        try:
            from ui.knowledge_widget import KnowledgeBaseWidget
            widget = KnowledgeBaseWidget()
            self.assertIsInstance(widget, KnowledgeBaseWidget)
            print("✅ KnowledgeBaseWidget: OK")
        except Exception as e:
            print(f"❌ KnowledgeBaseWidget: {e}")
            self.fail(f"KnowledgeBaseWidget failed: {e}")
    
    def test_message_display(self):
        try:
            from ui.message_display import MessageDisplay
            widget = MessageDisplay()
            self.assertIsInstance(widget, MessageDisplay)
            print("✅ MessageDisplay: OK")
        except Exception as e:
            print(f"❌ MessageDisplay: {e}")
            self.fail(f"MessageDisplay failed: {e}")
    
    def test_session_panel(self):
        try:
            from ui.session_panel import SessionPanel
            widget = SessionPanel(sessions_dir="test_sessions")
            self.assertIsInstance(widget, SessionPanel)
            print("✅ SessionPanel: OK")
        except Exception as e:
            print(f"❌ SessionPanel: {e}")
            self.fail(f"SessionPanel failed: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAvailableComponents)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*60)
    
    sys.exit(0 if result.wasSuccessful() else 1)
