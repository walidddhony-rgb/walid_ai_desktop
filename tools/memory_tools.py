from db.database import Database


def save_memory(key, value):
    db = Database()
    db.add_memory(key, value)
    return 'Saved to memory successfully'


def get_memory():
    db = Database()
    return db.get_all_memory()
