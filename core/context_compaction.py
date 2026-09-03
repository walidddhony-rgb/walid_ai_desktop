import json
import requests
from core.config import DEFAULT_MODEL, OLLAMA_URL


def estimate_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += len(content) // 4
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += len(str(part.get("text", ""))) // 4
        total += 20
    return total


def should_compact(messages: list, max_tokens: int = 24000) -> bool:
    current = estimate_tokens(messages)
    return current > max_tokens


def compact_messages(messages: list, keep_recent: int = 4) -> list:
    if len(messages) <= keep_recent + 2:
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if len(non_system) <= keep_recent:
        return messages

    to_summarize = non_system[:-keep_recent]
    recent = non_system[-keep_recent:]

    summary = _generate_summary(to_summarize)

    compacted = system_msgs[:]
    compacted.append({
        "role": "system",
        "content": f"ملخص المحادثة السابقة:\n{summary}\n\nهذه أحدث {keep_recent} رسائل:"
    })
    compacted.extend(recent)
    return compacted


def _generate_summary(messages: list) -> str:
    conversation_text = ""
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if isinstance(content, str) and content.strip():
            conversation_text += f"[{role}]: {content[:500]}\n\n"

    if not conversation_text.strip():
        return "لا يوجد محتوى للتلخيص."

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": DEFAULT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Summarize the following conversation concisely in Arabic. "
                            "Keep all important facts, code results, file names, and decisions. "
                            "Be brief but complete. Maximum 10 lines."
                        ),
                    },
                    {"role": "user", "content": conversation_text[:8000]},
                ],
                "stream": False,
                "options": {"num_ctx": 4096, "temperature": 0.3},
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "تعذر التلخيص.")
    except Exception as e:
        return f"تعذر التلخيص: {e}"


def auto_compact_if_needed(messages: list, max_tokens: int = 24000, keep_recent: int = 4) -> tuple:
    if not should_compact(messages, max_tokens):
        return messages, False
    compacted = compact_messages(messages, keep_recent)
    return compacted, True
