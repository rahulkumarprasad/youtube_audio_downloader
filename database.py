import sqlite3
from config import DB_NAME

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS downloads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT,
        url TEXT UNIQUE,
        folder TEXT
    )''')
    con.commit()
    con.close()

def update_database_table_for_prepared_zip_files():
    con = get_db()
    cur = con.cursor()
    cur.execute('''ALTER TABLE downloads ADD COLUMN zip_file TEXT DEFAULT NULL''')
    con.commit()
    con.close()

def is_duplicate(url):
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("SELECT id FROM downloads WHERE url=?", (url,))
        result = cur.fetchone()
        return result is not None
    except Exception:
        # Table may not exist yet — create it and retry once
        try:
            init_db()
            cur.execute("SELECT id FROM downloads WHERE url=?", (url,))
            result = cur.fetchone()
            return result is not None
        except Exception:
            return False
    finally:
        con.close()
