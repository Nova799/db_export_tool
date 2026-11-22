"""Background scheduling service for recoveries (APScheduler)."""

import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from .. import database as dbmod
from ..database import get_connection as get_db, list_recoveries, get_recovery, update_recovery_execution
from ..services.executor import run_recovery
def _get_setting(conn, key, default=None):
    from ..database import get_setting as gs
    return gs(conn, key, default)


class SchedulerService:
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.enabled = False
        self.hour = 8
        self._lock = threading.Lock()

    # ---------- lifecycle ----------

    def start(self, hour=None):
        with self._lock:
            if self.enabled:
                return
            conn = get_db()
            try:
                if hour is None:
                    hour = int(_get_setting(conn, "schedule_hour", "8") or 8)
                enabled_flag = _get_setting(conn, "schedule_enabled", "0")
            finally:
                conn.close()
            self.hour = hour
            if not self.scheduler.running:
                self.scheduler.start()
            self.enabled = True
            self._schedule_all()
            # catch-up missed runs in background
            threading.Thread(target=self._catchup, daemon=True).start()
            self._notify_ui()

    def stop(self):
        with self._lock:
            if not self.enabled:
                return
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            self.scheduler = BackgroundScheduler()
            self.enabled = False
            self._notify_ui()

    def set_enabled(self, enabled, hour=None):
        conn = get_db()
        try:
            from ..database import set_setting
            set_setting(conn, "schedule_enabled", "1" if enabled else "0")
            if hour is not None:
                set_setting(conn, "schedule_hour", str(hour))
        finally:
            conn.close()
        if enabled:
            self.start(hour=hour)
        else:
            self.stop()

    # ---------- scheduling ----------

    def _trigger(self, frequency, hour):
        if frequency == "weekly":
            return CronTrigger(day_of_week="mon", hour=hour, minute=0)
        if frequency == "monthly":
            return CronTrigger(day=1, hour=hour, minute=0)
        if frequency == "quarterly":
            return CronTrigger(month="1,4,7,10", day=1, hour=hour, minute=0)
        return None

    def _schedule_all(self):
        conn = get_db()
        try:
            recs = list_recoveries(conn)
        finally:
            conn.close()
        for r in recs:
            if r.get("frequency") and r["frequency"] != "manual":
                self.schedule_recovery(r["id"], r["frequency"])

    def schedule_recovery(self, recovery_id, frequency):
        if not self.enabled:
            return
        trigger = self._trigger(frequency, self.hour)
        if trigger is None:
            return
        try:
            self.scheduler.add_job(
                self._run_job,
                trigger,
                id=f"recovery_{recovery_id}",
                args=[recovery_id],
                replace_existing=True,
                misfire_grace_time=3600,
                coalesce=True,
                max_instances=1,
            )
        except Exception as e:
            print("schedule error:", e)
        # update next_execution in DB
        self._update_next(recovery_id, frequency)

    def unschedule_recovery(self, recovery_id):
        try:
            self.scheduler.remove_job(f"recovery_{recovery_id}")
        except JobLookupError:
            pass

    def run_now(self, recovery_id):
        threading.Thread(target=self._run_job, args=(recovery_id,), daemon=True).start()

    # ---------- job execution ----------

    def _run_job(self, recovery_id):
        try:
            res = run_recovery(recovery_id)
        except Exception as e:
            res = {"status": "error", "error": str(e)}
        # update DB
        conn = get_db()
        rec_name = str(recovery_id)
        try:
            rec = get_recovery(conn, recovery_id)
            if rec:
                rec_name = rec.get("name") or rec_name
            freq = rec.get("frequency") if rec else "manual"
            trigger = self._trigger(freq, self.hour) if freq else None
            next_iso = None
            if trigger is not None:
                nxt = trigger.get_next_fire_time(None, datetime.now())
                if nxt:
                    next_iso = nxt.isoformat()
            status = res.get("status", "error")
            from ..database import update_recovery_execution
            update_recovery_execution(conn, recovery_id, status, next_iso)
        finally:
            conn.close()
        # notification
        try:
            from .notifications import notify_run_result
            details = ""
            if res.get("error"):
                details = res["error"]
            elif res.get("sp_error"):
                details = res["sp_error"]
            elif res.get("csv_path"):
                details = f"Lignes : {res.get('rows',0)}\nCSV : {res['csv_path']}"
            notify_run_result(rec_name, status, details)
        except Exception as e:
            print("notify error:", e)
        self._notify_ui()

    def _update_next(self, recovery_id, frequency):
        conn = get_db()
        try:
            trigger = self._trigger(frequency, self.hour)
            next_iso = None
            if trigger is not None:
                nxt = trigger.get_next_fire_time(None, datetime.now())
                if nxt:
                    next_iso = nxt.isoformat()
            from ..database import update_recovery_execution
            # only set next_execution, keep status
            rec = get_recovery(conn, recovery_id)
            if rec:
                conn.execute(
                    "UPDATE recoveries SET next_execution=? WHERE id=?",
                    (next_iso, recovery_id),
                )
                conn.commit()
        finally:
            conn.close()

    # ---------- catch-up ----------

    def _catchup(self):
        conn = get_db()
        try:
            recs = list_recoveries(conn)
        finally:
            conn.close()
        now = datetime.now()
        for r in recs:
            if r.get("frequency") == "manual":
                continue
            ne = r.get("next_execution")
            if ne:
                try:
                    dt = datetime.fromisoformat(ne)
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                except Exception:
                    dt = None
                if dt and dt < now:
                    # missed run: execute once
                    self._run_job(r["id"])
            else:
                # no next_execution set: schedule will handle; but run once if never executed
                if not r.get("last_execution"):
                    self._run_job(r["id"])

    # ---------- ui ----------

    def _notify_ui(self):
        if self.app is not None and hasattr(self.app, "after"):
            try:
                self.app.after(0, self._refresh_status)
            except Exception:
                pass

    def _refresh_status(self):
        if hasattr(self.app, "set_schedule_status"):
            self.app.set_schedule_status(self.enabled, self.hour)
