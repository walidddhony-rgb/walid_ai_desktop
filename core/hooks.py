import importlib.util
from pathlib import Path


HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "SessionStart",
    "SessionStop",
]


def get_hooks_dir(workspace_path):
    return Path(workspace_path) / ".agents" / "hooks"


def discover_hooks(workspace_path):
    hooks_dir = get_hooks_dir(workspace_path)
    hooks = {}
    if not hooks_dir.exists():
        return hooks
    for event in HOOK_EVENTS:
        event_dir = hooks_dir / event
        if event_dir.exists() and event_dir.is_dir():
            scripts = sorted(event_dir.glob("*.py"))
            if scripts:
                hooks[event] = [str(s) for s in scripts]
    return hooks


def run_hook(hook_path, context):
    result = {"approved": True, "message": "", "modified_context": context}
    try:
        spec = importlib.util.spec_from_file_location("hook_module", hook_path)
        if spec is None or spec.loader is None:
            return result
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "main"):
            hook_result = module.main(context)
            if isinstance(hook_result, dict):
                if "approved" in hook_result:
                    result["approved"] = hook_result["approved"]
                if "message" in hook_result:
                    result["message"] = hook_result["message"]
                if "modified_context" in hook_result:
                    result["modified_context"] = hook_result["modified_context"]
            elif isinstance(hook_result, bool):
                result["approved"] = hook_result
    except Exception as e:
        result["message"] = "Hook error: " + str(e)
    return result


def run_event_hooks(event, context, workspace_path):
    hooks = discover_hooks(workspace_path)
    results = []
    for hook_path in hooks.get(event, []):
        result = run_hook(hook_path, context)
        results.append({"path": hook_path, "approved": result["approved"], "message": result["message"]})
        context = result["modified_context"]
        if not result["approved"]:
            break
    return results


def create_hook_template(workspace_path, event, name="example"):
    hooks_dir = get_hooks_dir(workspace_path) / event
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / (name + ".py")

    if event == "PreToolUse":
        template = (
            '"""PreToolUse hook: runs before any tool execution.\n'
            'Return {"approved": False} to block the tool.\n'
            '"""\n'
            'def main(context):\n'
            '    tool_name = context.get("tool_name", "")\n'
            '    tool_args = context.get("tool_args", {})\n'
            '    if tool_name == "exec" and tool_args.get("language") == "shell":\n'
            '        code = tool_args.get("code", "")\n'
            '        if "rm -rf" in code or "format" in code:\n'
            '            return {"approved": False, "message": "Blocked dangerous command"}\n'
            '    return {"approved": True}\n'
        )
    elif event == "PostToolUse":
        template = (
            '"""PostToolUse hook: runs after a tool completes."""\n'
            'def main(context):\n'
            '    tool_name = context.get("tool_name", "")\n'
            '    tool_result = context.get("tool_result", "")\n'
            '    return {"approved": True}\n'
        )
    elif event == "UserPromptSubmit":
        template = (
            '"""UserPromptSubmit hook: runs when user sends a message."""\n'
            'def main(context):\n'
            '    user_message = context.get("user_message", "")\n'
            '    if "password" in user_message.lower() or "api key" in user_message.lower():\n'
            '        return {"approved": False, "message": "Warning: sensitive info detected"}\n'
            '    return {"approved": True}\n'
        )
    elif event == "SessionStart":
        template = (
            '"""SessionStart hook."""\n'
            'def main(context):\n'
            '    return {"approved": True}\n'
        )
    elif event == "SessionStop":
        template = (
            '"""SessionStop hook."""\n'
            'def main(context):\n'
            '    return {"approved": True}\n'
        )
    else:
        template = 'def main(context):\n    return {"approved": True}\n'

    hook_path.write_text(template, encoding="utf-8")
    return str(hook_path)