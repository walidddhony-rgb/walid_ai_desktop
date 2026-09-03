EXEC_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "exec",
        "description": "Execute code locally. Use this to run Python, Shell, or JavaScript code to accomplish tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": ["python", "shell", "javascript"],
                    "description": "The programming language to execute",
                },
                "code": {"type": "string", "description": "The code to execute"},
            },
            "required": ["language", "code"],
        },
    },
}
