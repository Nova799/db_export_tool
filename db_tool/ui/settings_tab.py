"""Settings tab: CSV export format and other app settings."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import database as db

SEP_OPTIONS = [",", ";", "\\t", "|"]
ENC_OPTIONS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
QUOTE_OPTIONS = ["minimal", "all", "nonnumeric", "none"]
LINE_OPTIONS = ["\\n", "\\r\\n"]


class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.load()

    def _build(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Format d'export CSV", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

        self.vars = {}
        row = 1
        # separator
        ttk.Label(frm, text="Séparateur").grid(row=row, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=v, values=SEP_OPTIONS, state="readonly", width=10)
        cb.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.vars["csv_separator"] = v
        row += 1

        ttk.Label(frm, text="Encodage").grid(row=row, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=v, values=ENC_OPTIONS, state="readonly", width=12)
        cb.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.vars["csv_encoding"] = v
        row += 1

        ttk.Label(frm, text="En-tête").grid(row=row, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=v, values=["oui", "non"], state="readonly", width=10)
        cb.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.vars["csv_header"] = v
        row += 1

        ttk.Label(frm, text="Quoting").grid(row=row, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=v, values=QUOTE_OPTIONS, state="readonly", width=12)
        cb.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.vars["csv_quoting"] = v
        row += 1

        ttk.Label(frm, text="Fin de ligne").grid(row=row, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=v, values=LINE_OPTIONS, state="readonly", width=10)
        cb.grid(row=row, column=1, sticky=tk.W, pady=4)
        self.vars["csv_lineterminator"] = v
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, pady=12, sticky=tk.W)
        ttk.Button(btns, text="Enregistrer tout", command=self.save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Réinitialiser", command=self.reset).pack(side=tk.LEFT, padx=4)

        ttk.Label(frm, text="Les paramètres s'appliquent aux prochaines exécutions.").grid(row=row+1, column=0, columnspan=2, sticky=tk.W, pady=4)

        # ---------- SMTP / Notifications ----------
        r = row + 3
        ttk.Label(frm, text="Notifications par email (SMTP)", font=("Helvetica", 12, "bold")).grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=(12, 8)); r += 1

        smtp_fields = [
            ("Serveur SMTP", "smtp_host", "entry"),
            ("Port", "smtp_port", "entry"),
            ("Utilisateur", "smtp_user", "entry"),
            ("Mot de passe", "smtp_password", "password"),
            ("Expéditeur", "smtp_from", "entry"),
            ("Destinataire", "smtp_to", "entry"),
        ]
        for label, key, kind in smtp_fields:
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky=tk.W, pady=4)
            v = tk.StringVar()
            e = ttk.Entry(frm, textvariable=v, show="*" if kind == "password" else "")
            e.grid(row=r, column=1, sticky=tk.EW, pady=4)
            self.vars[key] = v
            r += 1

        ttk.Label(frm, text="TLS").grid(row=r, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        ttk.Combobox(frm, textvariable=v, values=["oui", "non"], state="readonly", width=10).grid(row=r, column=1, sticky=tk.W, pady=4)
        self.vars["smtp_use_tls"] = v
        r += 1

        ttk.Label(frm, text="Notifier si erreur").grid(row=r, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        ttk.Combobox(frm, textvariable=v, values=["oui", "non"], state="readonly", width=10).grid(row=r, column=1, sticky=tk.W, pady=4)
        self.vars["notify_on_error"] = v
        r += 1

        ttk.Label(frm, text="Notifier si succès").grid(row=r, column=0, sticky=tk.W, pady=4)
        v = tk.StringVar()
        ttk.Combobox(frm, textvariable=v, values=["oui", "non"], state="readonly", width=10).grid(row=r, column=1, sticky=tk.W, pady=4)
        self.vars["notify_on_success"] = v
        r += 1

        ttk.Button(frm, text="Tester l'envoi", command=self.test_email).grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=8)

    def load(self):
        conn = db.get_connection()
        try:
            self.vars["csv_separator"].set(db.get_setting(conn, "csv_separator", ","))
            self.vars["csv_encoding"].set(db.get_setting(conn, "csv_encoding", "utf-8-sig"))
            self.vars["csv_header"].set("oui" if db.get_setting(conn, "csv_header", "1") == "1" else "non")
            self.vars["csv_quoting"].set(db.get_setting(conn, "csv_quoting", "minimal"))
            self.vars["csv_lineterminator"].set(db.get_setting(conn, "csv_lineterminator", "\\n"))

            self.vars["smtp_host"].set(db.get_setting(conn, "smtp_host", ""))
            self.vars["smtp_port"].set(db.get_setting(conn, "smtp_port", "587"))
            self.vars["smtp_user"].set(db.get_setting(conn, "smtp_user", ""))
            # password stored encrypted
            from ..config import decrypt_secret
            self.vars["smtp_password"].set(decrypt_secret(db.get_setting(conn, "smtp_password", "") or ""))
            self.vars["smtp_from"].set(db.get_setting(conn, "smtp_from", ""))
            self.vars["smtp_to"].set(db.get_setting(conn, "smtp_to", ""))
            self.vars["smtp_use_tls"].set("oui" if db.get_setting(conn, "smtp_use_tls", "1") == "1" else "non")
            self.vars["notify_on_error"].set("oui" if db.get_setting(conn, "notify_on_error", "1") == "1" else "non")
            self.vars["notify_on_success"].set("oui" if db.get_setting(conn, "notify_on_success", "0") == "1" else "non")
        finally:
            conn.close()

    def save(self):
        conn = db.get_connection()
        try:
            db.set_setting(conn, "csv_separator", self.vars["csv_separator"].get())
            db.set_setting(conn, "csv_encoding", self.vars["csv_encoding"].get())
            db.set_setting(conn, "csv_header", "1" if self.vars["csv_header"].get() == "oui" else "0")
            db.set_setting(conn, "csv_quoting", self.vars["csv_quoting"].get())
            db.set_setting(conn, "csv_lineterminator", self.vars["csv_lineterminator"].get())

            db.set_setting(conn, "smtp_host", self.vars["smtp_host"].get().strip())
            db.set_setting(conn, "smtp_port", self.vars["smtp_port"].get().strip())
            db.set_setting(conn, "smtp_user", self.vars["smtp_user"].get().strip())
            from ..config import encrypt_secret
            db.set_setting(conn, "smtp_password", encrypt_secret(self.vars["smtp_password"].get()))
            db.set_setting(conn, "smtp_from", self.vars["smtp_from"].get().strip())
            db.set_setting(conn, "smtp_to", self.vars["smtp_to"].get().strip())
            db.set_setting(conn, "smtp_use_tls", "1" if self.vars["smtp_use_tls"].get() == "oui" else "0")
            db.set_setting(conn, "notify_on_error", "1" if self.vars["notify_on_error"].get() == "oui" else "0")
            db.set_setting(conn, "notify_on_success", "1" if self.vars["notify_on_success"].get() == "oui" else "0")
        finally:
            conn.close()
        messagebox.showinfo("Paramètres", "Paramètres enregistrés.")

    def reset(self):
        conn = db.get_connection()
        try:
            db.set_setting(conn, "csv_separator", ",")
            db.set_setting(conn, "csv_encoding", "utf-8-sig")
            db.set_setting(conn, "csv_header", "1")
            db.set_setting(conn, "csv_quoting", "minimal")
            db.set_setting(conn, "csv_lineterminator", "\\n")
        finally:
            conn.close()
        self.load()
        messagebox.showinfo("Paramètres", "Paramètres réinitialisés.")

    def test_email(self):
        self.save()
        app = self.winfo_toplevel()
        app.start_progress("Envoi de l'email de test...")
        def work():
            from ..services.notifications import send_email
            return send_email("[DB Export] Test", "Ceci est un email de test.")
        def done(res):
            app.stop_progress()
            ok, msg = res if not isinstance(res, dict) else (False, res.get("_exception", "Erreur"))
            if ok:
                messagebox.showinfo("Email", msg)
            else:
                messagebox.showerror("Email", msg)
        app.run_in_background(work, done)
