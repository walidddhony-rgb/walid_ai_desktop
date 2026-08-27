# Walid AI Desktop v9 — Intelligent Agent

## New: Agent Mode

Toggle the 🤖 button to activate Agent Mode. The agent can autonomously:

### Project Evaluation
- Ask: "قم بتقييم مشروع في D:/myproject"
- Agent calls `read_project_files` to read ALL code files
- Analyzes architecture, quality, security
- Provides detailed professional evaluation

### Learning from Sources
- Ask: "اطلع على مصادر علمية عن تحليل الشبكات ثم أعد التقييم"
- Agent searches web + academic sources
- Saves learned knowledge to memory via `save_memory`
- Re-evaluates with new knowledge

### File Management
- Ask: "قم بتنظيم ملفات المشروع"
- Agent uses `list_directory`, `create_file`, `create_directory`

## Tools Available to Agent
1. list_directory(path)
2. read_file(path)
3. read_project_files(path, extensions)
4. web_search(query)
5. academic_search(query)
6. save_memory(key, value)
7. get_memory()
8. create_file(path, content)
9. create_directory(path)
10. move_file(src, dest)
11. archive_folder(src, dest)

## Run
```
ollama pull qwen2.5:7b
pip install -r requirements.txt
python main.py
```
