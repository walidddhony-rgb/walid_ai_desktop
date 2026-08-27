"""SQL schema constants."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations(
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS uploaded_files(
    id INTEGER PRIMARY KEY,
    conversation_id TEXT,
    filename TEXT,
    path TEXT,
    file_type TEXT,
    size INTEGER,
    extracted_text TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY,
    message_id INTEGER,
    rating TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS memory(
    id INTEGER PRIMARY KEY,
    key TEXT,
    value TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS search_cache(
    id INTEGER PRIMARY KEY,
    query TEXT,
    scope TEXT,
    results_json TEXT,
    created_at TEXT
);
"""
