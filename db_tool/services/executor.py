"""Execution service: run a recovery end-to-end."""

import csv
import os
import time
from datetime import datetime

from ..config import decrypt_secret
from .scheduler import compute_next_execution
from .variables import auto_variables, resolve_variables, extract_variables
from ..database import (
    get_connection as get_db,
    get_connection_by_id,
    get_recovery,
    get_sharepoint_folder,
    create_execution,
    update_recovery_execution,
    list_recovery_variables,
)
from ..connectors import get_connector
from ..sharepoint.graph import GraphSharePointClient, build_client


EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app_data", "exports")


def _ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


def run_recovery(recovery_id, sharepoint_secret_plain=None, overrides=None):
    """Execute a recovery. Returns dict with status, rows, csv_path, web_url, error."""
    db = get_db()
    try:
        rec = get_recovery(db, recovery_id)
        if not rec:
            return {"status": "error", "error": "Récupération introuvable"}
        conn_row = get_connection_by_id(db, rec["connection_id"])
        if not conn_row:
            return {"status": "error", "error": "Connexion introuvable"}

        # Read SQL script
        script_path = rec["script_path"]
        if not script_path or not os.path.exists(script_path):
            return {"status": "error", "error": f"Script SQL introuvable : {script_path}"}
        with open(script_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        # Resolve variables
        custom_vars = list_recovery_variables(db, recovery_id)
        context_vars = auto_variables(
            frequency=rec.get("frequency"),
            recovery_name=rec.get("name"),
            connection_name=conn_row.get("name"),
        )
        sql = resolve_variables(raw_sql, context_vars, overrides=overrides, custom_vars=custom_vars)
        detected = extract_variables(raw_sql)

        # Connect & execute
        password = decrypt_secret(conn_row["password_hash"])
        port = conn_row["port"] or {"postgres": 5432, "mysql": 3306, "mssql": 1433}.get(conn_row["type"], 5432)
        connector = get_connector(conn_row["type"], conn_row["host"], port, conn_row["database"], conn_row["username"], password)

        t0 = time.time()
        try:
            rows = connector.execute_query(sql)
        except Exception as e:
            dur = int((time.time() - t0) * 1000)
            create_execution(db, recovery_id, 0, "error", dur, None)
            update_recovery_execution(db, recovery_id, "error")
            return {"status": "error", "error": str(e), "duree_ms": dur}

        dur = int((time.time() - t0) * 1000)

        # Read CSV format settings
        from ..database import get_setting
        sep = get_setting(db, "csv_separator", ",")
        if sep == "\\t":
            sep = "\t"
        enc = get_setting(db, "csv_encoding", "utf-8-sig")
        header = get_setting(db, "csv_header", "1") == "1"
        quoting_name = get_setting(db, "csv_quoting", "minimal")
        quoting_map = {
            "minimal": csv.QUOTE_MINIMAL,
            "all": csv.QUOTE_ALL,
            "nonnumeric": csv.QUOTE_NONNUMERIC,
            "none": csv.QUOTE_NONE,
        }
        quoting = quoting_map.get(quoting_name, csv.QUOTE_MINIMAL)
        lineterm = get_setting(db, "csv_lineterminator", "\\n")
        if lineterm == "\\r\\n":
            lineterm = "\r\n"
        elif lineterm == "\\n":
            lineterm = "\n"

        # Write CSV
        _ensure_export_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (rec["name"] or "export"))
        csv_filename = f"{safe_name}_{ts}.csv"
        csv_path = os.path.join(EXPORT_DIR, csv_filename)
        if rows:
            with open(csv_path, "w", newline="", encoding=enc) as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=sep,
                                       quoting=quoting, lineterminator=lineterm)
                if header:
                    writer.writeheader()
                for r in rows:
                    writer.writerow(r)
        else:
            with open(csv_path, "w", encoding=enc) as f:
                f.write("")

        # Upload to SharePoint if configured
        web_url = None
        sp_folder_id = rec.get("sharepoint_folder_id")
        sp_error = None
        if sp_folder_id:
            folder_row = get_sharepoint_folder(db, sp_folder_id)
            if folder_row:
                secret = sharepoint_secret_plain
                if secret is None:
                    secret = decrypt_secret(folder_row.get("client_secret_hash") or "")
                client = GraphSharePointClient(
                    site_url=folder_row["site_url"],
                    drive_id=folder_row.get("drive_id"),
                    folder_path=folder_row.get("folder_path") or "/",
                    tenant_id=folder_row.get("tenant_id"),
                    client_id=folder_row.get("client_id"),
                    client_secret=secret,
                )
                try:
                    web_url = client.upload_file(csv_path, csv_filename)
                except Exception as e:
                    sp_error = str(e)

        next_exec = compute_next_execution(rec.get("frequency", "manual"))
        create_execution(db, recovery_id, len(rows), "success" if not sp_error else "partial", dur, csv_filename)
        update_recovery_execution(db, recovery_id, "success" if not sp_error else "partial", next_exec)

        result = {
            "status": "success" if not sp_error else "partial",
            "rows": len(rows),
            "csv_path": csv_path,
            "csv_filename": csv_filename,
            "web_url": web_url,
            "duree_ms": dur,
            "resolved_sql": sql,
            "variables": detected,
        }
        if sp_error:
            result["sp_error"] = sp_error
        return result
    finally:
        db.close()


def preview_resolved_sql(recovery_id, overrides=None):
    """Return the SQL with variables resolved, without executing."""
    db = get_db()
    try:
        rec = get_recovery(db, recovery_id)
        if not rec:
            return None
        conn_row = get_connection_by_id(db, rec["connection_id"])
        if not conn_row:
            return None
        script_path = rec["script_path"]
        if not script_path or not os.path.exists(script_path):
            return None
        with open(script_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()
        custom_vars = list_recovery_variables(db, recovery_id)
        context_vars = auto_variables(
            frequency=rec.get("frequency"),
            recovery_name=rec.get("name"),
            connection_name=conn_row.get("name"),
        )
        return resolve_variables(raw_sql, context_vars, overrides=overrides, custom_vars=custom_vars)
    finally:
        db.close()


def list_detected_variables(recovery_id):
    """Return (detected placeholders, custom vars, context vars) for UI."""
    db = get_db()
    try:
        rec = get_recovery(db, recovery_id)
        if not rec:
            return [], [], {}
        conn_row = get_connection_by_id(db, rec["connection_id"])
        custom_vars = list_recovery_variables(db, recovery_id)
        context_vars = auto_variables(
            frequency=rec.get("frequency"),
            recovery_name=rec.get("name"),
            connection_name=conn_row.get("name") if conn_row else None,
        )
        script_path = rec["script_path"]
        raw_sql = ""
        if script_path and os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                raw_sql = f.read()
        detected = extract_variables(raw_sql)
        return detected, custom_vars, context_vars
    finally:
        db.close()
