"""Email notifications via aiosmtplib."""

import asyncio
import os

from ..database import get_setting, get_connection as get_db
from ..config import encrypt_secret, decrypt_secret


def _smtp_config():
    conn = get_db()
    try:
        cfg = {
            "host": get_setting(conn, "smtp_host", ""),
            "port": int(get_setting(conn, "smtp_port", "587") or 587),
            "username": get_setting(conn, "smtp_user", ""),
            "password": decrypt_secret(get_setting(conn, "smtp_password", "") or ""),
            "from_addr": get_setting(conn, "smtp_from", ""),
            "to_addr": get_setting(conn, "smtp_to", ""),
            "use_tls": get_setting(conn, "smtp_use_tls", "1") == "1",
            "notify_error": get_setting(conn, "notify_on_error", "1") == "1",
            "notify_success": get_setting(conn, "notify_on_success", "0") == "1",
        }
    finally:
        conn.close()
    return cfg


async def _send_async(cfg, subject, body):
    import aiosmtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"] or cfg["username"]
    msg["To"] = cfg["to_addr"]
    msg["Subject"] = subject
    msg.set_content(body)
    await aiosmtplib.send(
        msg,
        hostname=cfg["host"],
        port=cfg["port"],
        username=cfg["username"] or None,
        password=cfg["password"] or None,
        start_tls=cfg["use_tls"],
        timeout=30,
    )


def send_email(subject, body):
    """Send an email using configured SMTP. Returns (ok, message)."""
    cfg = _smtp_config()
    if not (cfg["host"] and cfg["to_addr"]):
        return False, "SMTP non configuré (host/destinataire manquants)."
    try:
        asyncio.run(_send_async(cfg, subject, body))
        return True, "Email envoyé."
    except Exception as e:
        return False, str(e)


def notify_run_result(recovery_name, status, details=""):
    """Send notification based on status and settings."""
    cfg = _smtp_config()
    if status in ("error", "partial") and not cfg["notify_error"]:
        return False, "Notification d'erreur désactivée."
    if status == "success" and not cfg["notify_success"]:
        return False, "Notification de succès désactivée."
    subject = f"[DB Export] {recovery_name} — {status}"
    body = f"Récupération : {recovery_name}\nStatut : {status}\n\n{details}"
    return send_email(subject, body)
