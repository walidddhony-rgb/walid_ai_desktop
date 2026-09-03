from tools.file_tools import create_directory, create_file, edit_file, list_directory, move_file, read_file
from tools.memory_tools import get_memory, save_memory
from tools.learning_tools import learn_from_file, learn_from_text, search_knowledge
from tools.exec_tool import EXEC_TOOL_SCHEMA
from search.engine import SearchEngine

AGENT_TOOLS = [
    EXEC_TOOL_SCHEMA,
    {"type": "function", "function": {"name": "list_directory", "description": "List files and directories in a path", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a single file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "create_file", "description": "Create or overwrite a file. Shows a diff review.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Edit a file by replacing old_text with new_text.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the web", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "academic_search", "description": "Search academic sources", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "save_memory", "description": "Save a key-value memory", "parameters": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {"name": "get_memory", "description": "Get all memory", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "create_directory", "description": "Create directory in workspace", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "move_file", "description": "Move file", "parameters": {"type": "object", "properties": {"src": {"type": "string"}, "dest": {"type": "string"}}, "required": ["src", "dest"]}}},
    {"type": "function", "function": {"name": "learn_from_file", "description": "Ingest a file into the knowledge base (RAG)", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}},
    {"type": "function", "function": {"name": "learn_from_text", "description": "Learn facts from text", "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "cid": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "search_knowledge", "description": "Search the local knowledge base (RAG retrieval)", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "spawn_subagent", "description": "Spawn a parallel subagent to work on a task. Returns the agent_id. Max 4 subagents.", "parameters": {"type": "object", "properties": {"task": {"type": "string"}, "mode": {"type": "string", "enum": ["worker", "explorer"]}}, "required": ["task"]}}},
    {"type": "function", "function": {"name": "get_subagent_results", "description": "Get results from all spawned subagents.", "parameters": {"type": "object", "properties": {}}}},
]

EXEC_CALLBACK = None
SUBAGENT_SPAWN_CALLBACK = None
SUBAGENT_RESULTS_CALLBACK = None

def set_exec_callback(cb):
    global EXEC_CALLBACK
    EXEC_CALLBACK = cb

def set_subagent_callbacks(spawn_cb, results_cb):
    global SUBAGENT_SPAWN_CALLBACK, SUBAGENT_RESULTS_CALLBACK
    SUBAGENT_SPAWN_CALLBACK = spawn_cb
    SUBAGENT_RESULTS_CALLBACK = results_cb

def execute_tool(name, args):
    if name == "exec":
        if EXEC_CALLBACK:
            return EXEC_CALLBACK(args.get("language", "python"), args.get("code", ""))
        return "exec callback not set"
    if name == "spawn_subagent":
        if SUBAGENT_SPAWN_CALLBACK:
            return SUBAGENT_SPAWN_CALLBACK(args.get("task", ""), args.get("mode", "worker"))
        return "subagent not available"
    if name == "get_subagent_results":
        if SUBAGENT_RESULTS_CALLBACK:
            return SUBAGENT_RESULTS_CALLBACK()
        return "no results"
    dispatch = {
        "list_directory": lambda a: list_directory(a.get("path", ".")),
        "read_file": lambda a: read_file(a.get("path", "")),
        "create_file": lambda a: create_file(a.get("path", ""), a.get("content", "")),
        "edit_file": lambda a: edit_file(a.get("path", ""), a.get("old_text", ""), a.get("new_text", "")),
        "web_search": lambda a: SearchEngine.web_search(a.get("query", "")),
        "academic_search": lambda a: SearchEngine.academic_search(a.get("query", "")),
        "save_memory": lambda a: save_memory(a.get("key", ""), a.get("value", "")),
        "get_memory": lambda a: get_memory(),
        "create_directory": lambda a: create_directory(a.get("path", "")),
        "move_file": lambda a: move_file(a.get("src", ""), a.get("dest", "")),
        "learn_from_file": lambda a: learn_from_file(a.get("filepath", "")),
        "learn_from_text": lambda a: learn_from_text(a.get("text", ""), a.get("cid", "")),
        "search_knowledge": lambda a: search_knowledge(a.get("query", "")),
    }
    fn = dispatch.get(name)
    if fn is None:
        return "Unknown tool: " + name
    try:
        return fn(args)
    except Exception as e:
        return "Tool error: " + str(e)
