"""SharePoint folders tab: CRUD + test."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import database as db
from ..sharepoint import GraphSharePointClient
from ..config import decrypt_secret
from .tree_sort import enable_sorting


class SharePointTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Dossiers SharePoint", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(toolbar, text="Nouveau dossier", command=self.add).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Tester", command=self.test).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=2)

        cols = ("id", "name", "site_url", "folder_path", "auth_mode", "last_test")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150, anchor=tk.W)
        self.tree.column("id", width=40)
        self.tree.tag_configure("odd", background="#f3f4f6")
        enable_sorting(self.tree, cols)
        self.tree.pack(fill=tk.BOTH, expand=True)

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
            for i, f in enumerate(db.list_sharepoint_folders(conn)):
                self.tree.insert("", tk.END, values=(
                    f["id"], f["name"], f["site_url"], f["folder_path"], f["auth_mode"], f["last_test"],
                ), tags=("odd" if i % 2 else "",))
        finally:
            conn.close()

    def add(self):
        self._dialog()

    def delete(self):
        fid = self._selected_id()
        if fid is None:
            messagebox.showwarning("Sélection", "Sélectionnez un dossier.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer ce dossier ?"):
            return
        conn = db.get_connection()
        try:
            db.delete_sharepoint_folder(conn, fid)
        finally:
            conn.close()
        self.refresh()

    def test(self):
        fid = self._selected_id()
        if fid is None:
            messagebox.showwarning("Sélection", "Sélectionnez un dossier.")
            return
        conn = db.get_connection()
        try:
            row = db.get_sharepoint_folder(conn, fid)
        finally:
            conn.close()
        if not row:
            return
        app = self.winfo_toplevel()
        app.start_progress("Test SharePoint en cours...")
        def work():
            secret = decrypt_secret(row.get("client_secret_hash") or "")
            client = GraphSharePointClient(
                site_url=row["site_url"],
                drive_id=row.get("drive_id"),
                folder_path=row.get("folder_path") or "/",
                tenant_id=row.get("tenant_id"),
                client_id=row.get("client_id"),
                client_secret=secret,
            )
            return client.test()
        def done(res):
            app.stop_progress()
            ok, msg = res if not isinstance(res, dict) else (False, res.get("_exception", "Erreur"))
            if ok:
                messagebox.showinfo("Test", msg)
            else:
                messagebox.showerror("Test", msg)
        app.run_in_background(work, done)

    def _dialog(self):
        win = tk.Toplevel(self)
        win.title("Nouveau dossier SharePoint")
        win.geometry("520x420")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        from .tree_sort import center_window
        self.after(10, lambda: center_window(win, self.winfo_toplevel()))
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        vars_ = {}
        fields = [
            ("Nom", "name", ""),
            ("URL du site", "site_url", "https://tenant.sharepoint.com/sites/MonSite"),
            ("Drive ID (optionnel)", "drive_id", ""),
            ("Chemin dossier", "folder_path", "/"),
            ("Mode auth", "auth_mode", "app"),
            ("Tenant ID", "tenant_id", ""),
            ("Client ID", "client_id", ""),
            ("Client secret", "client_secret", ""),
        ]
        for i, (label, key, val) in enumerate(fields):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky=tk.W, pady=4)
            if key == "auth_mode":
                v = tk.StringVar(value=val)
                cb = ttk.Combobox(frm, textvariable=v, values=["app", "oauth"], state="readonly")
                cb.grid(row=i, column=1, sticky=tk.EW, pady=4)
                vars_[key] = v
            else:
                v = tk.StringVar(value=val)
                e = ttk.Entry(frm, textvariable=v, show="*" if key == "client_secret" else "")
                e.grid(row=i, column=1, sticky=tk.EW, pady=4)
                vars_[key] = v
        frm.columnconfigure(1, weight=1)

        def save():
            name = vars_["name"].get().strip()
            site_url = vars_["site_url"].get().strip()
            if not (name and site_url):
                messagebox.showwarning("Validation", "Nom et URL du site obligatoires.")
                return
            conn = db.get_connection()
            try:
                db.create_sharepoint_folder(
                    conn,
                    name=name,
                    site_url=site_url,
                    drive_id=vars_["drive_id"].get().strip() or None,
                    folder_path=vars_["folder_path"].get().strip() or "/",
                    auth_mode=vars_["auth_mode"].get().strip() or "app",
                    tenant_id=vars_["tenant_id"].get().strip() or None,
                    client_id=vars_["client_id"].get().strip() or None,
                    client_secret=vars_["client_secret"].get(),
                )
            finally:
                conn.close()
            win.destroy()
            self.refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Enregistrer", command=save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Annuler", command=win.destroy).pack(side=tk.LEFT, padx=4)
