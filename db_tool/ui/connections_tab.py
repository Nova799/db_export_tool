"""Connections tab: CRUD + test for DB connections."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import database as db
from ..connectors import get_connector
from ..config import decrypt_secret
from .tree_sort import enable_sorting
from ..models import ConnectionConfig


DB_TYPES = ["postgres", "mysql", "mssql"]
DEFAULT_PORTS = {"postgres": 5432, "mysql": 3306, "mssql": 1433}


class ConnectionsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Connexions aux bases de données", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(toolbar, text="Nouvelle connexion", command=self.add).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Modifier", command=self.edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Tester", command=self.test).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=2)

        cols = ("id", "name", "type", "host", "port", "database", "username", "last_test")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor=tk.W)
        self.tree.column("id", width=40)
        self.tree.tag_configure("odd", background="#f3f4f6")
        enable_sorting(self.tree, cols)
        self.tree.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(self.tree.item(sel[0], "values")[0])

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        conn = db.get_connection()
        try:
            for i, c in enumerate(db.list_connections(conn)):
                self.tree.insert("", tk.END, values=(
                    c["id"], c["name"], c["type"], c["host"], c["port"], c["database"], c["username"], c["last_test"],
                ), tags=("odd" if i % 2 else "",))
        finally:
            conn.close()

    def add(self):
        self._dialog(None)

    def edit(self):
        cid = self._selected_id()
        if cid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une connexion.")
            return
        conn = db.get_connection()
        try:
            row = db.get_connection_by_id(conn, cid)
        finally:
            conn.close()
        self._dialog(row)

    def delete(self):
        cid = self._selected_id()
        if cid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une connexion.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer cette connexion ?"):
            return
        conn = db.get_connection()
        try:
            db.delete_connection(conn, cid)
        finally:
            conn.close()
        self.refresh()

    def test(self):
        cid = self._selected_id()
        if cid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une connexion.")
            return
        conn = db.get_connection()
        try:
            row = db.get_connection_by_id(conn, cid)
        finally:
            conn.close()
        if not row:
            return
        app = self.winfo_toplevel()
        app.start_progress("Test de connexion en cours...")
        def work():
            password = decrypt_secret(row["password_hash"])
            port = row["port"] or DEFAULT_PORTS.get(row["type"], 5432)
            connector = get_connector(row["type"], row["host"], port, row["database"], row["username"], password)
            return connector.test()
        def done(res):
            app.stop_progress()
            ok, msg = res if not isinstance(res, dict) else (False, res.get("_exception", "Erreur"))
            if ok:
                c = db.get_connection()
                try:
                    db.update_connection_last_test(c, cid, True)
                finally:
                    c.close()
                messagebox.showinfo("Test", msg)
            else:
                messagebox.showerror("Test", msg)
            self.refresh()
        app.run_in_background(work, done)

    def _dialog(self, row):
        win = tk.Toplevel(self)
        win.title("Connexion" if row is None else "Modifier la connexion")
        win.geometry("420x360")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        from .tree_sort import center_window
        self.after(10, lambda: center_window(win, self.winfo_toplevel()))
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        vars_ = {}
        fields = [
            ("Nom", "name", row["name"] if row else ""),
            ("Type", "type", row["type"] if row else "postgres"),
            ("Hôte", "host", row["host"] if row else ""),
            ("Port", "port", row["port"] if row else ""),
            ("Base", "database", row["database"] if row else ""),
            ("Utilisateur", "username", row["username"] if row else ""),
            ("Mot de passe", "password", ""),
        ]
        for i, (label, key, val) in enumerate(fields):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky=tk.W, pady=4)
            if key == "type":
                v = tk.StringVar(value=val)
                cb = ttk.Combobox(frm, textvariable=v, values=DB_TYPES, state="readonly")
                cb.grid(row=i, column=1, sticky=tk.EW, pady=4)
                vars_[key] = v
            else:
                v = tk.StringVar(value="" if val is None else str(val))
                e = ttk.Entry(frm, textvariable=v, show="*" if key == "password" else "")
                e.grid(row=i, column=1, sticky=tk.EW, pady=4)
                vars_[key] = v
        frm.columnconfigure(1, weight=1)

        def save():
            name = vars_["name"].get().strip()
            db_type = vars_["type"].get().strip()
            host = vars_["host"].get().strip()
            port_txt = vars_["port"].get().strip()
            port = int(port_txt) if port_txt else None
            database = vars_["database"].get().strip()
            username = vars_["username"].get().strip()
            password = vars_["password"].get()
            if not (name and host and database and username):
                messagebox.showwarning("Validation", "Nom, hôte, base et utilisateur sont obligatoires.")
                return
            conn = db.get_connection()
            try:
                if row is None:
                    if not password:
                        messagebox.showwarning("Validation", "Mot de passe obligatoire.")
                        return
                    db.create_connection(conn, name, db_type, host, port, database, username, password)
                else:
                    db.update_connection(conn, row["id"], name, db_type, host, port, database, username, password or None)
            finally:
                conn.close()
            win.destroy()
            self.refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Enregistrer", command=save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Annuler", command=win.destroy).pack(side=tk.LEFT, padx=4)
