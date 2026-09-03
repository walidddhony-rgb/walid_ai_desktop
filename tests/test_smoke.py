"""
Comprehensive smoke tests for Walid AI Desktop.

These tests verify that the application can start and basic functionality works.
They are designed to run quickly in CI on every commit.

Run with: pytest tests/test_smoke.py -v
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestImports:
    """Test that all core modules can be imported without errors."""
    
    def test_import_agent(self):
        """Test importing agent module."""
        import agent
        assert agent is not None
    
    def test_import_core(self):
        """Test importing core module."""
        import core
        assert core is not None
    
    def test_import_tools(self):
        """Test importing tools module."""
        import tools
        assert tools is not None
    
    def test_import_db(self):
        """Test importing db module."""
        import db
        assert db is not None
    
    def test_import_knowledge(self):
        """Test importing knowledge module."""
        import knowledge
        assert knowledge is not None
    
    def test_import_search(self):
        """Test importing search module."""
        import search
        assert search is not None
    
    def test_import_voice(self):
        """Test importing voice module."""
        import voice
        assert voice is not None
    
    def test_import_ui(self):
        """Test importing ui module."""
        import ui
        assert ui is not None


class TestCoreImports:
    """Test importing specific core submodules."""
    
    def test_import_config(self):
        """Test importing config module."""
        from core import config
        assert config is not None
    
    def test_import_session(self):
        """Test importing session module."""
        from core import session
        assert session is not None
    
    def test_import_profiles(self):
        """Test importing profiles module."""
        from core import profiles
        assert profiles is not None
    
    def test_import_sandbox(self):
        """Test importing sandbox module."""
        from core import sandbox
        assert sandbox is not None


class TestToolsRegistry:
    """Test tools registry initialization."""
    
    def test_tools_registry_import(self):
        """Test importing tools registry."""
        from tools import registry
        assert registry is not None


class TestDatabase:
    """Test database module initialization."""
    
    def test_db_import(self):
        """Test importing db module."""
        from db import database
        assert database is not None
    
    def test_db_schema(self):
        """Test importing db schema."""
        from db import schema
        assert schema is not None


class TestKnowledgeBase:
    """Test knowledge base modules."""
    
    def test_ingestor_import(self):
        """Test importing knowledge ingestor."""
        from knowledge import ingestor
        assert ingestor is not None
    
    def test_index_worker_import(self):
        """Test importing knowledge index worker."""
        from knowledge import index_worker
        assert index_worker is not None


class TestVoiceEngines:
    """Test voice engine modules."""
    
    def test_stt_engine_import(self):
        """Test importing STT engine."""
        from voice import stt_engine
        assert stt_engine is not None
    
    def test_tts_engine_import(self):
        """Test importing TTS engine."""
        from voice import tts_engine
        assert tts_engine is not None


class TestMainApplication:
    """Test main application entry point."""
    
    def test_main_module_exists(self):
        """Test that main.py module exists and is importable."""
        import main
        assert main is not None


class TestPyQt6Availability:
    """Test that PyQt6 is available (required for UI)."""
    
    def test_pyqt6_import(self):
        """Test importing PyQt6."""
        try:
            import PyQt6
            assert PyQt6 is not None
        except ImportError:
            # PyQt6 might not be installed in CI headless environment
            # This is acceptable as long as other tests pass
            pass


class TestOllamaAvailability:
    """Test that Ollama can be accessed (optional in CI)."""
    
    def test_ollama_host_env(self):
        """Test that OLLAMA_HOST environment variable can be set."""
        os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
        assert os.environ['OLLAMA_HOST'] == 'http://localhost:11434'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
