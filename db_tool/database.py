"""Database module for managing connections, recoveries, executions and SharePoint folders."""

import sqlite3
import os
from datetime import datetime

from .config import hash_password, verify_password, encrypt_secret, decrypt_secret

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data", "tool.db")


def get_connection():
    """Get or create the SQLite database connection and ensure tables exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    _migrate(conn)
    return conn


def _create_tables(conn):
    """Create all needed tables if they don't exist."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'postgres',
        host TEXT NOT NULL,
        port INTEGER,
        database TEXT NOT NULL,
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_test TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sharepoint_folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        site_url TEXT NOT NULL,
        drive_id TEXT,
        folder_path TEXT NOT NULL DEFAULT '/',
        auth_mode TEXT NOT NULL DEFAULT 'app',
        tenant_id TEXT,
        client_id TEXT,
        client_secret_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_test TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS recoveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        connection_id INTEGER NOT NULL,
        script_path TEXT NOT NULL,
        sharepoint_folder_id INTEGER,
        sharepoint_path TEXT,
        frequency TEXT DEFAULT 'manual',
        last_execution TIMESTAMP,
        next_execution TIMESTAMP,
        status VARCHAR(20) DEFAULT 'pending',
        FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE,
        FOREIGN KEY (sharepoint_folder_id) REFERENCES sharepoint_folders(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recovery_id INTEGER NOT NULL,
        date_execution TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        lignes_exportees INTEGER DEFAULT 0,
        statut VARCHAR(20),
        duree_ms INTEGER,
        csv_filename TEXT,
        FOREIGN KEY (recovery_id) REFERENCES recoveries(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS recovery_variables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recovery_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        var_type TEXT NOT NULL DEFAULT 'text',
        value TEXT,
        format TEXT,
        FOREIGN KEY (recovery_id) REFERENCES recoveries(id) ON DELETE CASCADE
    );
    """)
    conn.commit()


def _migrate(conn):
    """Apply lightweight migrations for older databases."""
    # recoveries: ensure sharepoint_folder_id column exists
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(recoveries)").fetchall()]
    if "sharepoint_folder_id" not in cols:
        conn.execute("ALTER TABLE recoveries ADD COLUMN sharepoint_folder_id INTEGER")
    if "sharepoint_path" not in cols:
        conn.execute("ALTER TABLE recoveries ADD COLUMN sharepoint_path TEXT")
    conn.commit()


# ---------- Connections CRUD ----------

def create_connection(conn, name, db_type, host, port, database, username, password):
    cur = conn.execute(
        """INSERT INTO connections (name, type, host, port, database, username, password_hash)
           VALUES (?,?,?,?,?,?,?)""",
        (name, db_type, host, port, database, username, encrypt_secret(password)),
    )
    conn.commit()
    return cur.lastrowid


def list_connections(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM connections ORDER BY name").fetchall()]


def get_connection_by_id(conn, cid):
    r = conn.execute("SELECT * FROM connections WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def update_connection(conn, cid, name, db_type, host, port, database, username, password=None):
    if password:
        conn.execute(
            """UPDATE connections SET name=?, type=?, host=?, port=?, database=?, username=?, password_hash=?
               WHERE id=?""",
            (name, db_type, host, port, database, username, encrypt_secret(password), cid),
        )
    else:
        conn.execute(
            """UPDATE connections SET name=?, type=?, host=?, port=?, database=?, username=?
               WHERE id=?""",
            (name, db_type, host, port, database, username, cid),
        )
    conn.commit()


def delete_connection(conn, cid):
    conn.execute("DELETE FROM connections WHERE id=?", (cid,))
    conn.commit()


def update_connection_last_test(conn, cid, ok):
    conn.execute("UPDATE connections SET last_test=? WHERE id=?", (datetime.now().isoformat(), cid))
    conn.commit()


# ---------- SharePoint folders CRUD ----------

def create_sharepoint_folder(conn, name, site_url, drive_id, folder_path, auth_mode, tenant_id, client_id, client_secret):
    cur = conn.execute(
        """INSERT INTO sharepoint_folders (name, site_url, drive_id, folder_path, auth_mode, tenant_id, client_id, client_secret_hash)
           VALUES (?,?,?,?,?,?,?,?)""",
        (name, site_url, drive_id, folder_path, auth_mode, tenant_id, client_id,
         encrypt_secret(client_secret) if client_secret else None),
    )
    conn.commit()
    return cur.lastrowid


def list_sharepoint_folders(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM sharepoint_folders ORDER BY name").fetchall()]


def get_sharepoint_folder(conn, fid):
    r = conn.execute("SELECT * FROM sharepoint_folders WHERE id=?", (fid,)).fetchone()
    return dict(r) if r else None


def delete_sharepoint_folder(conn, fid):
    conn.execute("DELETE FROM sharepoint_folders WHERE id=?", (fid,))
    conn.commit()


# ---------- Recoveries CRUD ----------

def create_recovery(conn, name, connection_id, script_path, sharepoint_folder_id=None, sharepoint_path=None, frequency="manual"):
    cur = conn.execute(
        """INSERT INTO recoveries (name, connection_id, script_path, sharepoint_folder_id, sharepoint_path, frequency)
           VALUES (?,?,?,?,?,?)""",
        (name, connection_id, script_path, sharepoint_folder_id, sharepoint_path, frequency),
    )
    conn.commit()
    return cur.lastrowid


def list_recoveries(conn):
    return [dict(r) for r in conn.execute(
        """SELECT r.*, c.name AS connection_name, s.name AS sharepoint_folder_name
           FROM recoveries r
           LEFT JOIN connections c ON c.id = r.connection_id
           LEFT JOIN sharepoint_folders s ON s.id = r.sharepoint_folder_id
           ORDER BY r.name"""
    ).fetchall()]


def get_recovery(conn, rid):
    r = conn.execute("SELECT * FROM recoveries WHERE id=?", (rid,)).fetchone()
    return dict(r) if r else None


def update_recovery(conn, rid, name, connection_id, script_path, sharepoint_folder_id=None, sharepoint_path=None, frequency="manual"):
    conn.execute(
        """UPDATE recoveries SET name=?, connection_id=?, script_path=?, sharepoint_folder_id=?, sharepoint_path=?, frequency=?
           WHERE id=?""",
        (name, connection_id, script_path, sharepoint_folder_id, sharepoint_path, frequency, rid),
    )
    conn.commit()


def delete_recovery(conn, rid):
    conn.execute("DELETE FROM recoveries WHERE id=?", (rid,))
    conn.commit()


def update_recovery_execution(conn, rid, status, next_execution=None):
    conn.execute(
        "UPDATE recoveries SET status=?, last_execution=?, next_execution=? WHERE id=?",
        (status, datetime.now().isoformat(), next_execution, rid),
    )
    conn.commit()


# ---------- Executions ----------

def create_execution(conn, recovery_id, lignes_exportees, statut, duree_ms, csv_filename):
    cur = conn.execute(
        """INSERT INTO executions (recovery_id, lignes_exportees, statut, duree_ms, csv_filename)
           VALUES (?,?,?,?,?)""",
        (recovery_id, lignes_exportees, statut, duree_ms, csv_filename),
    )
    conn.commit()
    return cur.lastrowid


def list_executions(conn, recovery_id=None, limit=100):
    if recovery_id:
        q = "SELECT * FROM executions WHERE recovery_id=? ORDER BY date_execution DESC LIMIT ?"
        params = (recovery_id, limit)
    else:
        q = "SELECT * FROM executions ORDER BY date_execution DESC LIMIT ?"
        params = (limit,)
    return [dict(r) for r in conn.execute(q, params).fetchall()]


# ---------- Settings ----------

def get_setting(conn, key, default=None):
    r = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(conn, key, value):
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()


# ---------- Recovery variables ----------

def list_recovery_variables(conn, recovery_id):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM recovery_variables WHERE recovery_id=? ORDER BY name", (recovery_id,)
    ).fetchall()]


def create_recovery_variable(conn, recovery_id, name, var_type="text", value="", format=None):
    cur = conn.execute(
        "INSERT INTO recovery_variables (recovery_id, name, var_type, value, format) VALUES (?,?,?,?,?)",
        (recovery_id, name, var_type, value, format),
    )
    conn.commit()
    return cur.lastrowid


def update_recovery_variable(conn, vid, name, var_type, value, format=None):
    conn.execute(
        "UPDATE recovery_variables SET name=?, var_type=?, value=?, format=? WHERE id=?",
        (name, var_type, value, format, vid),
    )
    conn.commit()


def delete_recovery_variable(conn, vid):
    conn.execute("DELETE FROM recovery_variables WHERE id=?", (vid,))
    conn.commit()


def test_connection_db(conn, cid):
    """Placeholder kept for backward compat; real test is in connectors."""
    c = get_connection_by_id(conn, cid)
    if c and c.get("password_hash"):
        return True, "Configuration trouvée"
    return False, "Aucune connexion configurée"
