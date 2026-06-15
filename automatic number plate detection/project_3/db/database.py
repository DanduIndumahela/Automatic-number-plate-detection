import sqlite3
import threading
from config import ANPR_DB_PATH, USER_DB_PATH

DB_LOCK = threading.Lock()

def get_db_conn(db_path: str):
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn

def db_fetch_one(db_path: str, query: str, params=()):
    with get_db_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchone()

def db_fetch_all(db_path: str, query: str, params=()):
    with get_db_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()

def db_execute(db_path: str, query: str, params=()):
    with DB_LOCK:
        with get_db_conn(db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur.lastrowid

def add_column_if_missing(db_path, table, col, coltype):
    with DB_LOCK:
        with get_db_conn(db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                conn.commit()

def init_databases():
    with DB_LOCK:
        with get_db_conn(ANPR_DB_PATH) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT,
                plate_number TEXT,
                timestamp TEXT,
                UNIQUE(location, plate_number, timestamp)
            )
            """)
            conn.commit()

        with get_db_conn(USER_DB_PATH) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT UNIQUE,
                vehicle_no TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_store (
                email TEXT PRIMARY KEY,
                otp_hash TEXT,
                expires_at INTEGER
            )
            """)
            conn.commit()

    add_column_if_missing(USER_DB_PATH, "users", "license_img_path", "TEXT")
    add_column_if_missing(USER_DB_PATH, "users", "rc_img_path", "TEXT")