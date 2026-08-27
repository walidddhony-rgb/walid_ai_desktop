# Walid AI Desktop v6 — Multi-Step Agent

## New in v6
- **Multi-step agent loop**: The agent can write and execute multiple code blocks in sequence until the task is complete.
- **Chat streaming fixed**: Agent responses now appear in the chat panel.
- **Fully resizable panels**: All panels (chat, task log, preview, files, left sidebar) can be resized by dragging.
- **Vertical splitter on right**: Files, preview, and task log can be resized independently.

## Multi-step behavior
The agent now works in a loop:
1. Write code and call exec()
2. Read the output
3. If more work is needed, write and execute more code
4. Give a final summary when done

Up to 15 steps per message.

## Windows run
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
ollama serve
python main.py
```
