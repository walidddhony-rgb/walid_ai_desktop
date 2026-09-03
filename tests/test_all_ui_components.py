"""Comprehensive test suite for all UI components."""

import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton
from PyQt6.QtCore import QObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ui.status_bar import StatusBar
    from ui.settings_dialog import SettingsDialog
    from ui.tool_status import ToolStatusWidget
    from ui.theme_dialog import ThemeDialog
    from ui.knowledge_widget import KnowledgeBaseWidget
    from ui.error_dialog import ErrorDialog
    from ui.message_display import MessageDisplay, MessageBubble, CodeBlockWidget, MessageDisplayWithToolbar
    from ui.session_panel import SessionPanel, SessionItemWidget, SessionPanelWithToolbar
    ALL_IMPORTED = True
except ImportError as e:
    print(f"Import error: {e}")
    ALL_IMPORTED = False

class TestStatusBar(unittest.TestCase):
    def setUp(self):
        self.widget = StatusBar()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, StatusBar)
        self.assertIsInstance(self.widget, QWidget)
    def test_fixed_height(self):
        self.assertEqual(self.widget.fixedHeight(), 32)
    def test_update_status(self):
        self.widget.update_status("Test status")
        self.assertEqual(self.widget.status_label.text(), "Test status")
    def test_update_connections(self):
        self.widget.update_connections(5)
        self.assertEqual(self.widget.connections_label.text(), "🔗 5")
    def test_update_tokens(self):
        self.widget.update_tokens(1234)
        self.assertEqual(self.widget.tokens_label.text(), "💰 1234")
    def test_update_latency(self):
        self.widget.update_latency(250)
        self.assertEqual(self.widget.latency_label.text(), "⏱ 250ms")
    def test_clear_status(self):
        self.widget.update_status("Test")
        self.widget.clear_status()
        self.assertEqual(self.widget.status_label.text(), "")

class TestSettingsDialog(unittest.TestCase):
    def setUp(self):
        self.widget = SettingsDialog()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, SettingsDialog)
        self.assertIsInstance(self.widget, QWidget)
    def test_tabs_exist(self):
        self.assertIsNotNone(self.widget.tabs)
        self.assertGreaterEqual(self.widget.tabs.count(), 5)
    def test_tab_titles(self):
        expected_tabs = ["General", "API Keys", "Model", "Tools", "Advanced"]
        for i, expected in enumerate(expected_tabs):
            self.assertEqual(self.widget.tabs.tabText(i), expected)
    def test_save_button(self):
        save_btn = self.widget.findChild(QPushButton, "save_button")
        self.assertIsNotNone(save_btn)
    def test_cancel_button(self):
        cancel_btn = self.widget.findChild(QPushButton, "cancel_button")
        self.assertIsNotNone(cancel_btn)
    def test_get_settings(self):
        settings = self.widget.get_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn("api_keys", settings)
        self.assertIn("model", settings)
        self.assertIn("theme", settings)

class TestToolStatusWidget(unittest.TestCase):
    def setUp(self):
        self.widget = ToolStatusWidget()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, ToolStatusWidget)
        self.assertIsInstance(self.widget, QWidget)
    def test_fixed_height(self):
        self.assertEqual(self.widget.fixedHeight(), 40)
    def test_update_tool_status(self):
        self.widget.update_tool_status("github", "connected")
        self.widget.update_tool_status("notion", "disconnected")
        self.widget.update_tool_status("gmail", "error")
    def test_get_connected_tools(self):
        self.widget.update_tool_status("github", "connected")
        self.widget.update_tool_status("notion", "connected")
        connected = self.widget.get_connected_tools()
        self.assertIn("github", connected)
        self.assertIn("notion", connected)
    def test_get_status_count(self):
        self.widget.update_tool_status("github", "connected")
        count = self.widget.get_status_count("connected")
        self.assertEqual(count, 1)

class TestThemeDialog(unittest.TestCase):
    def setUp(self):
        self.widget = ThemeDialog()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, ThemeDialog)
        self.assertIsInstance(self.widget, QWidget)
    def test_theme_buttons(self):
        buttons = self.widget.findChildren(QPushButton)
        self.assertGreaterEqual(len(buttons), 3)
    def test_apply_theme_signal(self):
        class Receiver(QObject):
            received = False
            theme_name = None
        receiver = Receiver()
        self.widget.theme_selected.connect(lambda name: setattr(receiver, "theme_name", name) or setattr(receiver, "received", True))
        for btn in self.widget.findChildren(QPushButton):
            if btn.objectName().startswith("theme_"):
                btn.click()
                break
        self.assertTrue(receiver.received)

class TestKnowledgeBaseWidget(unittest.TestCase):
    def setUp(self):
        self.widget = KnowledgeBaseWidget()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, KnowledgeBaseWidget)
        self.assertIsInstance(self.widget, QWidget)
    def test_add_document(self):
        self.widget.add_document("test.txt", "Test content")
        self.assertEqual(self.widget.get_document_count(), 1)
    def test_search_documents(self):
        self.widget.add_document("doc1.txt", "Python programming")
        self.widget.add_document("doc2.txt", "JavaScript web")
        results = self.widget.search_documents("python")
        self.assertEqual(len(results), 1)
    def test_clear_documents(self):
        self.widget.add_document("test.txt", "content")
        self.widget.clear_documents()
        self.assertEqual(self.widget.get_document_count(), 0)

class TestErrorDialog(unittest.TestCase):
    def setUp(self):
        self.widget = ErrorDialog()
    def test_instantiation(self):
        self.assertIsInstance(self.widget, ErrorDialog)
        self.assertIsInstance(self.widget, QWidget)
    def test_show_error(self):
        self.widget.show_error("Test Error", "This is a test error message")
        self.assertEqual(self.widget.error_title.text(), "Test Error")
    def test_show_warning(self):
        self.widget.show_warning("Test Warning", "This is a warning")
        self.assertEqual(self.widget.error_title.text(), "Test Warning")
    def test_show_info(self):
        self.widget.show_info("Test Info", "Information message")
        self.assertEqual(self.widget.error_title.text(), "Test Info")

class TestMessageDisplay(unittest.TestCase):
    def test_message_bubble_instantiation(self):
        bubble = MessageBubble("Hello", "user")
        self.assertIsInstance(bubble, MessageBubble)
        self.assertIsInstance(bubble, QWidget)
    def test_message_bubble_role(self):
        user_bubble = MessageBubble("Hi", "user")
        assistant_bubble = MessageBubble("Hello", "assistant")
        self.assertIsInstance(user_bubble, MessageBubble)
        self.assertIsInstance(assistant_bubble, MessageBubble)
    def test_code_block_widget(self):
        code = CodeBlockWidget('print("Hello")', "python")
        self.assertIsInstance(code, CodeBlockWidget)
        self.assertEqual(code.code, 'print("Hello")')
        self.assertEqual(code.language, "python")
    def test_message_display_instantiation(self):
        display = MessageDisplay()
        self.assertIsInstance(display, MessageDisplay)
    def test_add_message(self):
        display = MessageDisplay()
        display.add_message("Test message", "user")
        self.assertEqual(display.get_message_count(), 1)
    def test_clear_messages(self):
        display = MessageDisplay()
        display.add_message("Message 1", "user")
        display.add_message("Message 2", "assistant")
        display.clear_messages()
        self.assertEqual(display.get_message_count(), 0)
    def test_message_display_with_toolbar(self):
        toolbar_display = MessageDisplayWithToolbar()
        self.assertIsInstance(toolbar_display, MessageDisplayWithToolbar)
        self.assertIsNotNone(toolbar_display.get_display())

class TestSessionPanel(unittest.TestCase):
    def test_session_item_widget(self):
        session_data = {"name": "Test Session", "created_at": "2026-09-04 02:00", "messages": [("Hello", "user"), ("Hi", "assistant")]}
        widget = SessionItemWidget("test_123", session_data)
        self.assertIsInstance(widget, SessionItemWidget)
    def test_session_panel_instantiation(self):
        panel = SessionPanel(sessions_dir="test_sessions")
        self.assertIsInstance(panel, SessionPanel)
    def test_save_and_load_session(self):
        panel = SessionPanel(sessions_dir="test_sessions")
        panel.save_current_session("test_123", "Test", [("Hi", "user")])
        session = panel.load_session("test_123")
        self.assertIsNotNone(session)
        self.assertEqual(session["name"], "Test")
    def test_get_session_count(self):
        panel = SessionPanel(sessions_dir="test_sessions")
        count = panel.get_session_count()
        self.assertIsInstance(count, int)
    def test_session_panel_with_toolbar(self):
        toolbar_panel = SessionPanelWithToolbar(sessions_dir="test_sessions")
        self.assertIsInstance(toolbar_panel, SessionPanelWithToolbar)
        self.assertIsNotNone(toolbar_panel.get_panel())

def run_tests():
    if not ALL_IMPORTED:
        print("❌ Some UI components could not be imported. Check imports above.")
        return False
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    test_classes = [TestStatusBar, TestSettingsDialog, TestToolStatusWidget, TestThemeDialog, TestKnowledgeBaseWidget, TestErrorDialog, TestMessageDisplay, TestSessionPanel]
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*70)
    return result.wasSuccessful()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    success = run_tests()
    sys.exit(0 if success else 1)