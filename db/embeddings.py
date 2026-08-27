import json
import math
import sqlite3
import requests

from core.config import EMBED_MODEL, OLLAMA_EMBED_URL


def get_embedding(text: str):
    try:
        resp = requests.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("embedding", [])
    except Exception:
        return []


def cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve_relevant_chunks(query, db_path, top_k=5):
    query_emb = get_embedding(query)
    if not query_emb:
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT chunk_text,embedding FROM knowledge_chunks").fetchall()
    conn.close()
    scored = []
    for r in rows:
        try:
            emb = json.loads(r['embedding']) if r['embedding'] else []
        except Exception:
            emb = []
        scored.append((cosine_similarity(query_emb, emb), r['chunk_text']))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]
