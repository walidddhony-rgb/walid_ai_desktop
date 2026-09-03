"""Smoke test: tool registry and file tools."""

from tools.file_tools import create_directory, create_file, list_directory, read_file
from tools.registry import AGENT_TOOLS, execute_tool


def test_agent_tools_count():
    assert len(AGENT_TOOLS) == 11


def test_tool_names():
    names = {t["function"]["name"] for t in AGENT_TOOLS}
    assert "list_directory" in names
    assert "read_file" in names
    assert "web_search" in names
    assert "save_memory" in names
    assert "create_file" in names
    assert "move_file" in names
    assert "archive_folder" in names


def test_execute_unknown_tool():
    result = execute_tool("nonexistent", {})
    assert "Unknown tool" in result


def test_create_and_read_file(tmp_path):
    fp = str(tmp_path / "test.txt")
    result = create_file(fp, "hello world")
    assert "Created" in result
    content = read_file(fp)
    assert "hello world" in content


def test_list_directory(tmp_path):
    create_file(str(tmp_path / "a.txt"), "a")
    create_directory(str(tmp_path / "subdir"))
    result = list_directory(str(tmp_path))
    assert "a.txt" in result
    assert "subdir" in result
