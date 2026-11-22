"""Recoveries tab: CRUD for data recoveries."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .tree_sort import enable_sorting

from .. import database as db
from ..models import Recovery


FREQUENCIES = ["manual", "weekly", "monthly", "quarterly"]


class RecoveriesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Récupérations (requêtes planifiées)", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(toolbar, text="Nouvelle récupération", command=self.add).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Modifier", command=self.edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Variables", command=self.manage_variables).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=2)

        cols = ("id", "name", "connection", "script_path", "sharepoint_folder", "frequency", "status", "last_execution")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=130, anchor=tk.W)
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
            for i, r in enumerate(db.list_recoveries(conn)):
                self.tree.insert("", tk.END, values=(
                    r["id"], r["name"], r.get("connection_name"), r["script_path"],
                    r.get("sharepoint_folder_name"), r["frequency"], r["status"], r["last_execution"],
                ), tags=("odd" if i % 2 else "",))
        finally:
            conn.close()

    def add(self):
        self._dialog(None)

    def edit(self):
        rid = self._selected_id()
        if rid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une récupération.")
            return
        conn = db.get_connection()
        try:
            row = db.get_recovery(conn, rid)
        finally:
            conn.close()
        self._dialog(row)

    def delete(self):
        rid = self._selected_id()
        if rid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une récupération.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer cette récupération ?"):
            return
        conn = db.get_connection()
        try:
            db.delete_recovery(conn, rid)
        finally:
            conn.close()
        self.refresh()

    def _dialog(self, row):
        conn = db.get_connection()
        try:
            connections = db.list_connections(conn)
            sp_folders = db.list_sharepoint_folders(conn)
        finally:
            conn.close()

        win = tk.Toplevel(self)
        win.title("Récupération" if row is None else "Modifier la récupération")
        win.geometry("560x420")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        from .tree_sort import center_window
        self.after(10, lambda: center_window(win, self.winfo_toplevel()))
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        v_name = tk.StringVar(value=row["name"] if row else "")
        v_conn = tk.StringVar()
        v_script = tk.StringVar(value=row["script_path"] if row else "")
        v_sp = tk.StringVar()
        v_freq = tk.StringVar(value=row["frequency"] if row else "manual")
        v_sppath = tk.StringVar(value=row.get("sharepoint_path") or "" if row else "")

        # connection combobox
        conn_map = {f"{c['id']} - {c['name']}": c["id"] for c in connections}
        conn_values = list(conn_map.keys())
        if row:
            for k, v in conn_map.items():
                if v == row["connection_id"]:
                    v_conn.set(k)
        if not v_conn.get() and conn_values:
            v_conn.set(conn_values[0])

        sp_map = {f"{f['id']} - {f['name']}": f["id"] for f in sp_folders}
        sp_values = ["(aucun)"] + list(sp_map.keys())
        if row and row.get("sharepoint_folder_id"):
            for k, v in sp_map.items():
                if v == row["sharepoint_folder_id"]:
                    v_sp.set(k)
        if not v_sp.get():
            v_sp.set("(aucun)")

        r = 0
        ttk.Label(frm, text="Nom").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        ttk.Entry(frm, textvariable=v_name).grid(row=r-1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Connexion").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        ttk.Combobox(frm, textvariable=v_conn, values=conn_values, state="readonly").grid(row=r-1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Script SQL").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        sf = ttk.Frame(frm)
        sf.grid(row=r-1, column=1, sticky=tk.EW, pady=4)
        ttk.Entry(sf, textvariable=v_script).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sf, text="Parcourir", command=lambda: self._pick_script(v_script)).pack(side=tk.LEFT, padx=4)

        ttk.Label(frm, text="Dossier SharePoint").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        ttk.Combobox(frm, textvariable=v_sp, values=sp_values, state="readonly").grid(row=r-1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Fréquence").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        ttk.Combobox(frm, textvariable=v_freq, values=FREQUENCIES, state="readonly").grid(row=r-1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Chemin SP (optionnel)").grid(row=r, column=0, sticky=tk.W, pady=4); r += 1
        ttk.Entry(frm, textvariable=v_sppath).grid(row=r-1, column=1, sticky=tk.EW, pady=4)

        frm.columnconfigure(1, weight=1)

        def save():
            name = v_name.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Nom obligatoire.")
                return
            if v_conn.get() not in conn_map:
                messagebox.showwarning("Validation", "Sélectionnez une connexion.")
                return
            script_path = v_script.get().strip()
            if not script_path:
                messagebox.showwarning("Validation", "Script SQL obligatoire.")
                return
            connection_id = conn_map[v_conn.get()]
            sp_val = v_sp.get()
            sp_folder_id = sp_map.get(sp_val) if sp_val != "(aucun)" else None
            frequency = v_freq.get().strip() or "manual"
            conn = db.get_connection()
            try:
                if row is None:
                    db.create_recovery(conn, name, connection_id, script_path, sp_folder_id, v_sppath.get().strip() or None, frequency)
                else:
                    db.update_recovery(conn, row["id"], name, connection_id, script_path, sp_folder_id, v_sppath.get().strip() or None, frequency)
            finally:
                conn.close()
            win.destroy()
            self.refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Enregistrer", command=save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Annuler", command=win.destroy).pack(side=tk.LEFT, padx=4)

    def manage_variables(self):
        rid = self._selected_id()
        if rid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une récupération.")
            return
        VariablesDialog(self, rid)

    @staticmethod
    def _pick_script(var):
        path = filedialog.askopenfilename(title="Choisir un script SQL", filetypes=[("SQL", "*.sql"), ("Tous", "*.*")])
        if path:
            var.set(path)


class VariablesDialog(tk.Toplevel):
    def __init__(self, parent, recovery_id):
        super().__init__(parent)
        self.title("Variables de la récupération")
        self.geometry("640x420")
        self.transient(parent.winfo_toplevel())
        self.recovery_id = recovery_id
        self._build()
        self.refresh()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=6, padx=6)
        ttk.Button(toolbar, text="Ajouter", command=self.add).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Modifier", command=self.edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=2)

        cols = ("id", "name", "var_type", "value", "format")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor=tk.W)
        self.tree.column("id", width=40)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6)

        info = ttk.Label(self, text="Variables auto : today, yesterday, now, period_start, period_end, month_start, month_end, week_start, week_end, year_start, year_end, recovery_name, connection_name, timestamp. Utilisez {{nom}} dans le SQL (mettez les quotes vous-même : '{{period_start}}').")
        info.pack(fill=tk.X, padx=6, pady=6)

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
            for v in db.list_recovery_variables(conn, self.recovery_id):
                self.tree.insert("", tk.END, values=(v["id"], v["name"], v["var_type"], v["value"], v["format"]))
        finally:
            conn.close()

    def add(self):
        self._dialog(None)

    def edit(self):
        vid = self._selected_id()
        if vid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une variable.")
            return
        conn = db.get_connection()
        try:
            rows = [r for r in db.list_recovery_variables(conn, self.recovery_id) if r["id"] == vid]
            row = rows[0] if rows else None
        finally:
            conn.close()
        self._dialog(row)

    def delete(self):
        vid = self._selected_id()
        if vid is None:
            messagebox.showwarning("Sélection", "Sélectionnez une variable.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer cette variable ?"):
            return
        conn = db.get_connection()
        try:
            db.delete_recovery_variable(conn, vid)
        finally:
            conn.close()
        self.refresh()

    def _dialog(self, row):
        win = tk.Toplevel(self)
        win.title("Variable" if row is None else "Modifier la variable")
        win.geometry("420x260")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        from .tree_sort import center_window
        self.after(10, lambda: center_window(win, self.winfo_toplevel()))
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        v_name = tk.StringVar(value=row["name"] if row else "")
        v_type = tk.StringVar(value=row["var_type"] if row else "text")
        v_value = tk.StringVar(value=row["value"] if row else "")
        v_format = tk.StringVar(value=row["format"] if row else "")

        for i, (label, var, widget) in enumerate([
            ("Nom", v_name, "entry"),
            ("Type", v_type, "combo"),
            ("Valeur", v_value, "entry"),
            ("Format (date)", v_format, "entry"),
        ]):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky=tk.W, pady=4)
            if widget == "combo":
                ttk.Combobox(frm, textvariable=var, values=["text", "date"], state="readonly").grid(row=i, column=1, sticky=tk.EW, pady=4)
            else:
                ttk.Entry(frm, textvariable=var).grid(row=i, column=1, sticky=tk.EW, pady=4)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Pour type 'date', valeur = date ISO (YYYY-MM-DD). Format = strftime (ex: %d/%m/%Y).").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=4)

        def save():
            name = v_name.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Nom obligatoire.")
                return
            conn = db.get_connection()
            try:
                if row is None:
                    db.create_recovery_variable(conn, self.recovery_id, name, v_type.get(), v_value.get(), v_format.get().strip() or None)
                else:
                    db.update_recovery_variable(conn, row["id"], name, v_type.get(), v_value.get(), v_format.get().strip() or None)
            finally:
                conn.close()
            win.destroy()
            self.refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Enregistrer", command=save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Annuler", command=win.destroy).pack(side=tk.LEFT, padx=4)
