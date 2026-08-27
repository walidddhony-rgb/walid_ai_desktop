"""Agent tool registry and dispatcher."""
from __future__ import annotations
import json
from tools.file_tools import (
    list_directory, read_file, read_project_files,
    create_file, create_directory, move_file, archive_folder,
)
from tools.memory_tools import save_memory, get_memory
from search.engine import SearchEngine

AGENT_TOOLS = [
    {"type": "function", "function": {
        "name": "list_directory",
        "description": "List files and directories in a path",
        "parameters": {"type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read the content of a single file",
        "parameters": {"type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_project_files",
        "description": "Read ALL code files in a project directory recursively",
        "parameters": {"type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root directory"},
                "extensions": {"type": "array", "items": {"type": "string"},
                    "description": "File extensions, e.g. ['py','js','html']"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web for current information",
        "parameters": {"type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "academic_search",
        "description": "Search academic sources: PubMed, DOI, Semantic Scholar",
        "parameters": {"type": "object",
            "properties": {"query": {"type": "string", "description": "Academic search query"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "save_memory",
        "description": "Save information to long-term memory for future use",
        "parameters": {"type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short title in Arabic"},
                "value": {"type": "string", "description": "The information to remember"}},
            "required": ["key", "value"]}}},
    {"type": "function", "function": {
        "name": "get_memory",
        "description": "Retrieve all saved memories",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "create_file",
        "description": "Create a new file with content",
        "parameters": {"type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "create_directory",
        "description": "Create a new directory",
        "parameters": {"type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "move_file",
        "description": "Move or rename a file",
        "parameters": {"type": "object",
            "properties": {
                "src": {"type": "string", "description": "Source path"},
                "dest": {"type": "string", "description": "Destination path"}},
            "required": ["src", "dest"]}}},
    {"type": "function", "function": {
        "name": "archive_folder",
        "description": "Archive a folder into a zip file",
        "parameters": {"type": "object",
            "properties": {
                "src": {"type": "string", "description": "Source folder"},
                "dest": {"type": "string", "description": "Destination directory"}},
            "required": ["src", "dest"]}}},
]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with validated arguments."""
    try:
        if name == "list_directory":
            return list_directory(args.get("path", "."))
        elif name == "read_file":
            return read_file(args.get("path", ""))
        elif name == "read_project_files":
            return read_project_files(args.get("path", "."), args.get("extensions"))
        elif name == "web_search":
            return json.dumps(SearchEngine.web_search(args.get("query", "")), ensure_ascii=False)
        elif name == "academic_search":
            return json.dumps(SearchEngine.academic_search(args.get("query", "")), ensure_ascii=False)
        elif name == "save_memory":
            return save_memory(args.get("key", ""), args.get("value", ""))
        elif name == "get_memory":
            return get_memory()
        elif name == "create_file":
            return create_file(args.get("path", ""), args.get("content", ""))
        elif name == "create_directory":
            return create_directory(args.get("path", ""))
        elif name == "move_file":
            return move_file(args.get("src", ""), args.get("dest", ""))
        elif name == "archive_folder":
            return archive_folder(args.get("src", ""), args.get("dest", "."))
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error ({name}): {e}"
