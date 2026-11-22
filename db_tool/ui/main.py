"""Main Tkinter application window — modern look via sv_ttk."""

import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import threading

from ..services.scheduler_service import SchedulerService
from ..database import get_setting, set_setting, get_connection

from .connections_tab import ConnectionsTab
from .sharepoint_tab import SharePointTab
from .recoveries_tab import RecoveriesTab
from .execution_tab import ExecutionTab
from .history_tab import HistoryTab
from .settings_tab import SettingsTab
from .tooltip import ToolTip


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DB Export Tool")
        self.geometry("1180x760")
        self.minsize(900, 600)

        # App logo / icon
        import os
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo.png")
        if os.path.exists(logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=logo_path)
                # subsample to a reasonable icon size
                self._logo_small = self._logo_img.subsample(8, 8)
                self.iconphoto(True, self._logo_img)
            except Exception:
                self._logo_img = None
                self._logo_small = None
        else:
            self._logo_img = None
            self._logo_small = None

        self._theme = get_setting(self._conn(), "ui_theme", "light")
        sv_ttk.set_theme(self._theme)

        self.scheduler = SchedulerService(self)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        conn = self._conn()
        try:
            enabled = get_setting(conn, "schedule_enabled", "0") == "1"
            hour = int(get_setting(conn, "schedule_hour", "8") or 8)
        finally:
            conn.close()
        self.hour_var.set(str(hour))
        if enabled:
            self.scheduler.start(hour=hour)
            self.set_schedule_status(True, hour)
        else:
            self.set_schedule_status(False, hour)

    def _conn(self):
        return get_connection()

    def _build(self):
        # Keyboard shortcuts
        self.bind("<Control-q>", lambda e: self._on_close())
        self.bind("<F5>", lambda e: self._shortcut_refresh())

        # Header
        header = ttk.Frame(self, padding=(16, 10))
        header.pack(fill=tk.X)
        if getattr(self, "_logo_small", None) is not None:
            ttk.Label(header, image=self._logo_small).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(header, text="DB Export Tool", font=("Helvetica", 18, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text="Export de bases de données vers SharePoint", foreground="#6b7280").pack(side=tk.LEFT, padx=(12, 0))
        btn_theme = ttk.Button(header, text="Thème clair/sombre", command=self.toggle_theme)
        btn_theme.pack(side=tk.RIGHT)
        ToolTip(btn_theme, "Basculer entre le thème clair et sombre")

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        tabs = [
            ("🔌 Connexions", ConnectionsTab),
            ("📁 SharePoint", SharePointTab),
            ("📋 Récupérations", RecoveriesTab),
            ("▶ Exécution", ExecutionTab),
            ("📜 Historique", HistoryTab),
            ("⚙ Paramètres", SettingsTab),
        ]
        for name, cls in tabs:
            frame = cls(self.notebook)
            self.notebook.add(frame, text=name)

        # Status bar
        bar = ttk.Frame(self, relief=tk.SUNKEN, padding=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Planification : inactive")
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=6)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        self.progress.pack(side=tk.LEFT, padx=6)
        self.progress.pack_forget()
        ttk.Label(bar, text="Heure :").pack(side=tk.RIGHT, padx=(0, 4))
        self.hour_var = tk.StringVar(value="8")
        ttk.Spinbox(bar, from_=0, to=23, width=4, textvariable=self.hour_var).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bar, text="Activer/Désactiver planification", command=self.toggle_schedule).pack(side=tk.RIGHT, padx=6)

    # ---------- progress helpers ----------
    def start_progress(self, text=None):
        if text:
            self.status_var.set(text)
        self.progress.pack(side=tk.LEFT, padx=6)
        self.progress.start(10)

    def stop_progress(self, text=None):
        self.progress.stop()
        self.progress.pack_forget()
        if text:
            self.status_var.set(text)

    def run_in_background(self, fn, on_done=None):
        """Run fn() in a worker thread; call on_done(result) on the UI thread."""
        def worker():
            try:
                result = fn()
            except Exception as e:
                result = {"_exception": str(e)}
            if on_done is not None:
                self.after(0, lambda r=result: on_done(r))
        threading.Thread(target=worker, daemon=True).start()

    def set_schedule_status(self, enabled, hour):
        self.status_var.set(f"Planification : {'active ✅' if enabled else 'inactive'} (heure {hour}h)")

    def toggle_schedule(self):
        try:
            hour = int(self.hour_var.get())
        except ValueError:
            hour = 8
        conn = self._conn()
        enabled_now = get_setting(conn, "schedule_enabled", "0") == "1"
        conn.close()
        self.scheduler.set_enabled(not enabled_now, hour=hour)
        self.set_schedule_status(not enabled_now, hour)

    def toggle_theme(self):
        new = "dark" if self._theme == "light" else "light"
        self._theme = new
        sv_ttk.set_theme(new)
        conn = self._conn()
        try:
            set_setting(conn, "ui_theme", new)
        finally:
            conn.close()

    def _shortcut_new_conn(self):
        # switch to connections tab and trigger add
        self.notebook.select(0)
        tab = self.notebook.nametowidget(self.notebook.tabs()[0])
        if hasattr(tab, "add"):
            tab.add()

    def _shortcut_refresh(self):
        for i in range(len(self.notebook.tabs())):
            tab = self.notebook.nametowidget(self.notebook.tabs()[i])
            if hasattr(tab, "refresh"):
                try:
                    tab.refresh()
                except Exception:
                    pass
            if hasattr(tab, "refresh_list"):
                try:
                    tab.refresh_list()
                except Exception:
                    pass

    def _about(self):
        from tkinter import messagebox
        messagebox.showinfo("À propos", "DB Export Tool\nVersion 1.0.0\n\nExport de bases de données vers SharePoint.\n\nConnexions : PostgreSQL, MySQL, SQL Server.\nPlanification : APScheduler.\nUI : Tkinter + sv_ttk.")

    def _on_close(self):
        try:
            self.scheduler.stop()
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
