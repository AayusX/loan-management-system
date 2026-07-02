import hashlib
import os
import platform
import sqlite3
import sys
import time
from pathlib import Path

def _resolve_app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(os.path.dirname(os.path.abspath(__file__)))


APP_ROOT = _resolve_app_root()
DATA_DIR = APP_ROOT / "data"
DB_PATH = DATA_DIR / "saving_group.db"
DB_CONN = None
SCHEMA_VERSION = 2


def get_db():
    global DB_CONN
    if DB_CONN is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DB_CONN = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
        DB_CONN.row_factory = sqlite3.Row
        DB_CONN.execute("PRAGMA foreign_keys = ON")
        DB_CONN.execute("PRAGMA journal_mode = WAL")
        DB_CONN.execute("PRAGMA synchronous = FULL")
        DB_CONN.execute("PRAGMA busy_timeout = 60000")
    return DB_CONN


def close_db():
    global DB_CONN
    if DB_CONN is not None:
        try:
            DB_CONN.close()
        finally:
            DB_CONN = None


def log_action(user, action, table, record_id, details="", conn=None):
    params = (user, action, table, record_id, details)
    query = "INSERT INTO audit_log (user,action,table_name,record_id,details) VALUES (?,?,?,?,?)"
    for attempt in range(5):
        try:
            if conn is not None:
                conn.execute(query, params)
            else:
                with get_db() as local_conn:
                    local_conn.execute(query, params)
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))


def _ensure_meta_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
    if row is None:
        conn.execute("INSERT INTO app_meta (key, value) VALUES ('schema_version', '1')")
        conn.execute("INSERT OR IGNORE INTO app_meta (key, value) VALUES ('bootstrap_done', '0')")
        return 1
    conn.execute("INSERT OR IGNORE INTO app_meta (key, value) VALUES ('bootstrap_done', '0')")
    try:
        return int(row["value"])
    except ValueError:
        return 1


def _migrate_to_v2(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS statement_periods (
            id INTEGER PRIMARY KEY,
            period_code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            is_locked INTEGER DEFAULT 0 CHECK (is_locked IN (0,1)),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS statement_rows (
            id INTEGER PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES statement_periods(id) ON DELETE CASCADE,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            sn INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            total_loan_issued REAL DEFAULT 0 CHECK (total_loan_issued >= 0),
            total_loan REAL DEFAULT 0 CHECK (total_loan >= 0),
            days INTEGER DEFAULT 0 CHECK (days >= 0),
            installment_this_quarter REAL DEFAULT 0 CHECK (installment_this_quarter >= 0),
            interest_due_this_quarter REAL DEFAULT 0 CHECK (interest_due_this_quarter >= 0),
            installment_plus_interest REAL DEFAULT 0 CHECK (installment_plus_interest >= 0),
            remaining_loan REAL DEFAULT 0 CHECK (remaining_loan >= 0),
            amount_payable_this_quarter REAL DEFAULT 0 CHECK (amount_payable_this_quarter >= 0),
            remarks TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(period_id, member_id)
        );

        CREATE INDEX IF NOT EXISTS idx_loans_member_status_date ON loans(member_id, status, issue_date);
        CREATE INDEX IF NOT EXISTS idx_repayments_loan_date ON repayments(loan_id, paid_date);
        CREATE INDEX IF NOT EXISTS idx_savings_member_quarter_date ON savings(member_id, quarter, paid_date);
        CREATE INDEX IF NOT EXISTS idx_statement_rows_period_member ON statement_rows(period_id, member_id);
        """
    )
    conn.execute("UPDATE app_meta SET value='2' WHERE key='schema_version'")


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT,
                role TEXT DEFAULT 'admin',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                joined_date TEXT DEFAULT (date('now')),
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS savings (
                id INTEGER PRIMARY KEY,
                member_id INTEGER REFERENCES members(id),
                amount REAL NOT NULL,
                quarter TEXT NOT NULL,
                paid_date TEXT DEFAULT (date('now')),
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY,
                member_id INTEGER REFERENCES members(id),
                principal REAL NOT NULL,
                interest_rate REAL DEFAULT 10.0,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS repayments (
                id INTEGER PRIMARY KEY,
                loan_id INTEGER REFERENCES loans(id),
                amount REAL NOT NULL,
                paid_date TEXT DEFAULT (date('now')),
                principal_paid REAL DEFAULT 0,
                interest_paid REAL DEFAULT 0,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY,
                user TEXT,
                action TEXT,
                table_name TEXT,
                record_id INTEGER,
                details TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            );
            """
        )

        # Ensure new optional columns exist in older databases.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "password_salt" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT")

        # Add interest_rate column to loans table if it doesn't exist
        loan_cols = [r[1] for r in conn.execute("PRAGMA table_info(loans)").fetchall()]
        if "interest_rate" not in loan_cols:
            conn.execute("ALTER TABLE loans ADD COLUMN interest_rate REAL DEFAULT 10.0")

        version = _ensure_meta_table(conn)
        if version < 2:
            _migrate_to_v2(conn)

        # Integrity check at startup for early corruption detection.
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"Database integrity check failed: {integrity}")

        ph = hashlib.sha256(b"admin123").hexdigest()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                ("admin", ph, "admin"),
            )
        except sqlite3.IntegrityError:
            pass


def ensure_first_login_bootstrap(username):
    """
    One-time bootstrap hook to record first successful login setup per DB.
    """
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_meta WHERE key='bootstrap_done'").fetchone()
        done = row and row["value"] == "1"
        if done:
            return
        machine = f"{platform.system()}|{platform.node()}|{platform.machine()}"
        machine_hash = hashlib.sha256(machine.encode("utf-8")).hexdigest()[:16]
        now = str(int(time.time()))
        conn.execute("UPDATE app_meta SET value='1' WHERE key='bootstrap_done'")
        conn.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
            ("bootstrap_info", f"{username}|{machine_hash}|{now}"),
        )
