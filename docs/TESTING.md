# Testing Guide

This guide explains how to run tests and contribute new tests to Walid AI Desktop.

## Quick Start

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # macOS/Linux

# Run all tests
pytest tests/ -v

# Run smoke tests only
pytest tests/test_smoke.py -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py              # Test package marker
├── test_smoke.py            # Comprehensive smoke tests (CI)
├── test_smoke_db.py         # Database smoke tests
├── test_smoke_imports.py    # Import smoke tests
├── test_smoke_main.py       # Main app smoke tests
├── test_smoke_tools.py      # Tools smoke tests
├── test_smoke_utils.py      # Utils smoke tests
└── ...                      # Future: unit tests, integration tests
```

## Smoke Tests

Smoke tests verify that the application can start and basic functionality works. They are designed to:

- **Run quickly** (< 30 seconds in CI)
- **Catch major issues** (broken imports, missing dependencies, configuration errors)
- **Work in headless environments** (no GUI required)

### Running Smoke Tests

```bash
# Run all smoke tests
pytest tests/test_smoke.py -v

# Run specific test class
pytest tests/test_smoke.py::TestImports -v

# Run specific test
pytest tests/test_smoke.py::TestImports::test_import_agent -v

# Run with detailed output
pytest tests/test_smoke.py -vv --tb=long
```

### Smoke Test Categories

1. **TestImports**: Verifies all core modules can be imported
2. **TestCoreImports**: Tests specific core submodules (config, session, profiles, sandbox)
3. **TestToolsRegistry**: Tests tools registry initialization
4. **TestDatabase**: Tests database module imports
5. **TestKnowledgeBase**: Tests RAG knowledge base modules
6. **TestVoiceEngines**: Tests STT/TTS engine imports
7. **TestMainApplication**: Tests main.py entry point
8. **TestPyQt6Availability**: Tests PyQt6 availability (optional in CI)
9. **TestOllamaAvailability**: Tests Ollama configuration (optional in CI)

## Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py` (e.g., `test_smoke.py`, `test_agent.py`)
- Test classes: `Test*` (e.g., `TestImports`, `TestDatabase`)
- Test functions: `test_*` (e.g., `test_import_agent`, `test_db_connection`)

### Example Test

```python
"""Example test file for agent module."""

import pytest


class TestAgent:
    """Test agent module functionality."""
    
    def test_agent_initialization(self):
        """Test that agent can be initialized."""
        from agent import agent_loop
        assert agent_loop is not None
    
    def test_agent_prompt_generation(self):
        """Test agent prompt generation."""
        from agent import prompts
        prompt = prompts.system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
```

### Best Practices

1. **Keep tests independent**: Each test should run in isolation
2. **Use fixtures**: Share setup code with pytest fixtures
3. **Mock external dependencies**: Don't rely on network or external services
4. **Test one thing per test**: Each test should verify a single behavior
5. **Use descriptive names**: Test names should explain what they verify
6. **Add docstrings**: Explain what each test does
7. **Clean up after tests**: Remove temporary files, close connections

## CI Integration

Tests run automatically on every push and pull request via GitHub Actions.

### CI Workflow

The CI workflow (`.github/workflows/ci.yml`) runs:

1. **Lint**: Ruff check and format
2. **Type check**: Mypy static type checking
3. **Tests**: Pytest with verbose output
4. **Smoke tests**: Import verification

### Passing CI

For a PR to be merged, CI must pass:

- ✅ All lint checks (no errors or warnings)
- ✅ Type checking (no type errors)
- ✅ All tests (no failures)
- ✅ Smoke tests (all imports work)

## Troubleshooting

### Test Fails Locally but Passes in CI

1. Check Python version: `python --version` (should be 3.11)
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Clear pytest cache: `pytest --cache-clear`
4. Check for local configuration: `.env`, `pytest.ini`

### Import Errors

```bash
# ModuleNotFoundError: No module named 'PyQt6'
pip install PyQt6

# ModuleNotFoundError: No module named 'ollama'
pip install ollama
```

### Test Takes Too Long

1. Check for infinite loops or large data processing
2. Mock slow operations (network calls, file I/O)
3. Use pytest timeouts: `@pytest.mark.timeout(5)`

### Coverage Issues

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# Open coverage report
# Open `htmlcov/index.html` in browser
```

## Future Test Categories

As the project grows, additional test categories will be added:

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test interactions between modules
- **UI tests**: Test PyQt6 interface (requires GUI)
- **Performance tests**: Benchmark critical operations
- **End-to-end tests**: Full workflow tests

## Resources

- [Pytest documentation](https://docs.pytest.org/)
- [Pytest best practices](https://docs.pytest.org/en/latest/explanation/best-practices.html)
- [Python testing best practices](https://docs.python-guide.org/writing/tests/)

---

**Last updated:** September 2026
