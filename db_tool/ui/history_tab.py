"""History tab: list of executions."""

import tkinter as tk
from tkinter import ttk, messagebox
from .tree_sort import enable_sorting

from .. import database as db


class HistoryTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="Historique des exécutions", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(toolbar, text="Rafraîchir", command=self.refresh).pack(side=tk.LEFT, padx=2)

        cols = ("id", "recovery_id", "date_execution", "lignes_exportees", "statut", "duree_ms", "csv_filename")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140, anchor=tk.W)
        self.tree.column("id", width=40)
        self.tree.tag_configure("odd", background="#f3f4f6")
        enable_sorting(self.tree, cols)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        conn = db.get_connection()
        try:
            for i, e in enumerate(db.list_executions(conn)):
                self.tree.insert("", tk.END, values=(
                    e["id"], e["recovery_id"], e["date_execution"], e["lignes_exportees"],
                    e["statut"], e["duree_ms"], e["csv_filename"],
                ), tags=("odd" if i % 2 else "",))
        finally:
            conn.close()
