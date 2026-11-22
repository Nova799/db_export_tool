"""Execution tab: run a recovery manually, with variable overrides."""

import tkinter as tk
from tkinter import ttk, messagebox

from .. import database as db
from ..services import run_recovery, list_detected_variables, preview_resolved_sql


class ExecutionTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.refresh_list()

    def _build(self):
        ttk.Label(self, text="Exécution manuelle des récupérations", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 8))
        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="Récupération :").pack(side=tk.LEFT, padx=4)
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(top, textvariable=self.combo_var, state="readonly", width=40)
        self.combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Exécuter...", command=self.open_exec_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Rafraîchir", command=self.refresh_list).pack(side=tk.LEFT, padx=4)

        self.log = tk.Text(self, height=20, state=tk.DISABLED, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, pady=8)

    def refresh_list(self):
        conn = db.get_connection()
        try:
            recs = db.list_recoveries(conn)
        finally:
            conn.close()
        self._map = {f"{r['id']} - {r['name']}": r["id"] for r in recs}
        self.combo["values"] = list(self._map.keys())
        if self.combo["values"]:
            self.combo.current(0)

    def _append(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def open_exec_dialog(self):
        sel = self.combo_var.get()
        if sel not in getattr(self, "_map", {}):
            messagebox.showwarning("Sélection", "Sélectionnez une récupération.")
            return
        rid = self._map[sel]
        ExecuteDialog(self, rid, self._on_done)

    def _on_done(self, res):
        self._append(f"--- Exécution ---")
        self._append(f"Statut : {res.get('status')}")
        if "rows" in res:
            self._append(f"Lignes exportées : {res['rows']}")
        if "csv_path" in res:
            self._append(f"CSV : {res['csv_path']}")
        if "web_url" in res and res["web_url"]:
            self._append(f"SharePoint : {res['web_url']}")
        if "sp_error" in res:
            self._append(f"Erreur SharePoint : {res['sp_error']}")
        if "error" in res:
            self._append(f"Erreur : {res['error']}")
        if "resolved_sql" in res:
            self._append("SQL résolu :")
            self._append(res["resolved_sql"])
        self._append("")


class ExecuteDialog(tk.Toplevel):
    def __init__(self, parent, recovery_id, callback):
        super().__init__(parent)
        self.title("Exécution avec variables")
        self.geometry("760x620")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        from .tree_sort import center_window
        parent.after(10, lambda: center_window(self, parent.winfo_toplevel()))
        self.recovery_id = recovery_id
        self.callback = callback
        self.overrides = {}
        self._detected, self._custom, self._context = list_detected_variables(recovery_id)
        self._build()
        self._refresh_preview()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Variables détectées (modifiables pour cette exécution) :").pack(anchor=tk.W)

        # Build entries for each variable
        self.var_entries = {}
        vars_frame = ttk.Frame(frm)
        vars_frame.pack(fill=tk.X, pady=6)
        # collect unique variable names from detected + custom + context
        names = []
        seen = set()
        for name, _fmt in self._detected:
            if name not in seen:
                seen.add(name); names.append(name)
        for cv in self._custom:
            if cv["name"] not in seen:
                seen.add(cv["name"]); names.append(cv["name"])
        # context vars also available
        for name in self._context:
            if name not in seen:
                seen.add(name); names.append(name)

        for i, name in enumerate(names):
            row = ttk.Frame(vars_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=name, width=22).pack(side=tk.LEFT)
            # default value
            default = ""
            if name in self._context:
                default = self._context[name]
            for cv in self._custom:
                if cv["name"] == name:
                    default = cv.get("value", "")
            entry = ttk.Entry(row, width=40)
            entry.insert(0, str(default))
            entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
            self.var_entries[name] = entry

        ttk.Label(frm, text="Aperçu du SQL résolu :").pack(anchor=tk.W, pady=(8, 2))
        self.preview = tk.Text(frm, height=16, wrap=tk.WORD)
        self.preview.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=8)
        ttk.Button(btns, text="Aperçu", command=self._refresh_preview).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Exécuter", command=self._run).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Annuler", command=self.destroy).pack(side=tk.LEFT, padx=4)

    def _collect_overrides(self):
        overrides = {}
        for name, entry in self.var_entries.items():
            overrides[name] = entry.get()
        return overrides

    def _refresh_preview(self):
        overrides = self._collect_overrides()
        sql = preview_resolved_sql(self.recovery_id, overrides=overrides)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, sql or "(impossible de résoudre)")

    def _run(self):
        overrides = self._collect_overrides()
        app = self.winfo_toplevel()
        self.destroy()
        app.start_progress("Exécution en cours...")
        def work():
            try:
                return run_recovery(self.recovery_id, overrides=overrides)
            except Exception as e:
                return {"status": "error", "error": str(e)}
        self._cb = self.callback
        def done(res):
            app.stop_progress("Exécution terminée.")
            try:
                self._cb(res)
            except Exception:
                pass
        app.run_in_background(work, done)
