# Walid AI Desktop

Local desktop AI agent built with PyQt6 and Ollama.

## Current entrypoint

The real production entrypoint is `main.py`. The old Flask prototype lives in `legacy/app.py`.

## Features

- **Streaming chat** with Ollama (real-time token output)
- **Agent Mode** with 11 local tools (file ops, web/academic search, memory)
- **Tool calling** via Ollama function-calling API with streaming detection
- **Path traversal protection** on all file operations
- **Human-in-the-loop** confirmation for destructive tools
- **Connection retry** for transient Ollama failures
- **Context window** `num_ctx=32768` for better tool calling
- **SQLite** storage for conversations, messages, files, feedback, memory, search cache
- **Web & academic search** via DuckDuckGo (PubMed, DOI, Semantic Scholar)
- **File upload** with text extraction (PDF, DOCX, TXT, MD, audio)
- **Voice input** via OpenAI Whisper
- **Theme persistence** (dark/light) saved to JSON config
- **Input validation** with length limits and argument checking
- **Guardrails**: max 15 agent iterations, tool argument validation, timeout protection

## Project structure

```
walid_ai_desktop/
├── main.py              # Thin launcher
├── core/
│   ├── config.py        # Constants, env vars, config load/save
│   ├── paths.py         # Centralised path constants
│   ├── utils.py         # safe_filename, truncate, sanitize_path, validate_path_safe
│   └── exceptions.py    # Custom exceptions
├── db/
│   ├── database.py      # Database class (SQLite manager)
│   └── schema.py        # SQL schema constants
├── search/
│   └── engine.py        # SearchEngine (web + academic search)
├── tools/
│   ├── file_tools.py    # list_directory, read_file, read_project_files, create/move/archive
│   ├── memory_tools.py  # save_memory, get_memory
│   ├── registry.py      # AGENT_TOOLS schema + execute_tool dispatcher
│   └── system_agent.py  # SystemAgent static file ops
├── agent/
│   ├── worker.py        # AgentWorker, StreamWorker, SearchWorker, LearnWorker
│   └── prompts.py       # System prompt templates
├── ui/
│   ├── app.py           # run_app() entrypoint
│   ├── main_window.py   # MainWindow (full UI)
│   ├── message_frame.py # MessageFrame widget
│   ├── dialogs.py       # SearchResultsDialog
│   └── themes.py        # Dark/Light QSS themes
├── legacy/
│   └── app.py           # Old Flask/SocketIO prototype (not production)
├── tests/
│   ├── test_smoke_imports.py
│   ├── test_smoke_db.py
│   ├── test_smoke_tools.py
│   ├── test_smoke_utils.py
│   └── test_smoke_main.py
├── packaging/
│   └── walid_ai_desktop.spec  # PyInstaller spec
├── data/                # SQLite DB + config.json (auto-created)
├── uploads/             # Uploaded files (auto-created)
├── voices/              # TTS audio output (auto-created)
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── pyproject.toml
```

## Windows setup

### 1) Create a virtual environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3) Start Ollama

```powershell
ollama pull qwen2.5:7b
ollama serve
```

### 4) Run the application

```powershell
python main.py
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `WALID_OLLAMA_URL` | `http://127.0.0.1:11434/api/chat` | Ollama API endpoint |
| `WALID_MODEL` | `qwen2.5:7b` | Default Ollama model |
| `WALID_WHISPER_MODEL` | `base` | Whisper model size |
| `WALID_DB_PATH` | `data/walid_ai.db` | SQLite database path |
| `WALID_CONFIG_PATH` | `data/config.json` | Config file path |

## Tools available to agent

1. `list_directory(path)`
2. `read_file(path)`
3. `read_project_files(path, extensions)`
4. `web_search(query)`
5. `academic_search(query)`
6. `save_memory(key, value)`
7. `get_memory()`
8. `create_file(path, content)`
9. `create_directory(path)`
10. `move_file(src, dest)`
11. `archive_folder(src, dest)`

## Tests

```powershell
pytest -q
```

## Build EXE

```powershell
pyinstaller packaging\walid_ai_desktop.spec
```

The built executable will be in `dist/WalidAIDesktop.exe`.
