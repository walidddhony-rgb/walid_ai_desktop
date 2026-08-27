"""Smoke test: all modules import cleanly."""


def test_import_core():
    import core.config
    import core.utils
    import core.paths
    import core.exceptions


def test_import_db():
    import db.database
    import db.schema


def test_import_search():
    import search.engine


def test_import_tools():
    import tools.file_tools
    import tools.memory_tools
    import tools.registry
    import tools.system_agent


def test_import_agent():
    import agent.worker
    import agent.prompts


def test_import_ui():
    import ui.themes
    import ui.message_frame
    import ui.dialogs
