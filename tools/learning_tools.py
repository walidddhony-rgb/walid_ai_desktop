from db.database import Database
from knowledge.ingestor import ingest_file


def learn_from_file(filepath):
    count = ingest_file(filepath)
    return f"Ingested {count} chunks from {filepath}"


def learn_from_text(text, cid=''):
    db = Database()
    facts = [line.strip() for line in text.split('\n') if line.strip()]
    for fact in facts:
        db.add_learned_fact(cid, fact)
    return f"Learned {len(facts)} facts"


def search_knowledge(query):
    from db.embeddings import retrieve_relevant_chunks
    from core.config import DB_PATH
    chunks = retrieve_relevant_chunks(query, DB_PATH, top_k=5)
    if not chunks:
        return 'No relevant knowledge found.'
    return '\n---\n'.join(chunks)
