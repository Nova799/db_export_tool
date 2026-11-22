"""Variable substitution for SQL queries (dates, periods, custom values)."""

import re
import calendar
from datetime import datetime, date, timedelta

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)(?::([^}]+))?\s*\}\}")


def _iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def _escape_sql(value):
    """Escape single quotes for safe SQL string literal injection."""
    return str(value).replace("'", "''")


def period_bounds(frequency, ref_date=None):
    """Return (start_date, end_date) for the period preceding ref_date, based on frequency."""
    ref = ref_date or date.today()
    freq = (frequency or "manual").lower()
    if freq == "weekly":
        # previous week Monday..Sunday
        monday = ref - timedelta(days=ref.weekday())
        start = monday - timedelta(days=7)
        end = monday - timedelta(days=1)
        return start, end
    if freq == "monthly":
        # previous month
        first_this = ref.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        end = last_prev
        return start, end
    if freq == "quarterly":
        # previous quarter
        q = (ref.month - 1) // 3
        # first month of current quarter
        first_month = q * 3 + 1
        first_this_q = date(ref.year, first_month, 1)
        last_prev_q = first_this_q - timedelta(days=1)
        # first month of previous quarter
        pq = (last_prev_q.month - 1) // 3
        first_prev_q = date(last_prev_q.year, pq * 3 + 1, 1)
        return first_prev_q, last_prev_q
    # manual / default: today only
    return ref, ref


def auto_variables(frequency=None, ref_date=None, recovery_name=None, connection_name=None):
    """Build the dict of auto-calculated variables (name -> str value)."""
    ref = ref_date or date.today()
    now = datetime.now()
    start, end = period_bounds(frequency, ref)
    vars_ = {
        "today": _iso(ref),
        "yesterday": _iso(ref - timedelta(days=1)),
        "tomorrow": _iso(ref + timedelta(days=1)),
        "now": now.isoformat(timespec="seconds"),
        "timestamp": now.strftime("%Y%m%d_%H%M%S"),
        "week_start": _iso(ref - timedelta(days=ref.weekday())),
        "week_end": _iso(ref + timedelta(days=6 - ref.weekday())),
        "month_start": _iso(ref.replace(day=1)),
        "month_end": _iso(date(ref.year, ref.month, calendar.monthrange(ref.year, ref.month)[1])),
        "year_start": _iso(date(ref.year, 1, 1)),
        "year_end": _iso(date(ref.year, 12, 31)),
        "period_start": _iso(start),
        "period_end": _iso(end),
        "period_label": f"{start.isoformat()}_{end.isoformat()}",
    }
    if recovery_name is not None:
        vars_["recovery_name"] = recovery_name
    if connection_name is not None:
        vars_["connection_name"] = connection_name
    return vars_


def extract_variables(sql):
    """Return list of (name, format_or_None) found in sql, in order, unique."""
    seen = set()
    out = []
    for m in PLACEHOLDER_RE.finditer(sql or ""):
        name = m.group(1)
        fmt = m.group(2)
        key = (name, fmt)
        if key not in seen:
            seen.add(key)
            out.append((name, fmt))
    return out


def _format_date_value(raw_value, fmt):
    """Try to parse raw_value as date and format; fallback to raw."""
    if not fmt:
        return raw_value
    # try parse ISO date/datetime
    for parser in (lambda s: date.fromisoformat(s), lambda s: datetime.fromisoformat(s).date()):
        try:
            d = parser(raw_value)
            return d.strftime(fmt)
        except Exception:
            continue
    try:
        dt = datetime.strptime(raw_value, "%Y-%m-%d")
        return dt.strftime(fmt)
    except Exception:
        return raw_value


def resolve_variables(sql, context_vars, overrides=None, custom_vars=None):
    """Resolve {{var}} placeholders in sql.

    context_vars: dict of auto variables.
    overrides: dict of user overrides (name -> value) for this run.
    custom_vars: list of dicts {name, var_type, value, format} from DB.
    Returns resolved sql string.
    """
    overrides = overrides or {}
    custom_map = {}
    for cv in (custom_vars or []):
        custom_map[cv["name"]] = cv

    def replacer(m):
        name = m.group(1)
        fmt = m.group(2)
        # overrides first
        if name in overrides:
            val = overrides[name]
            return _escape_sql(_format_date_value(val, fmt) if fmt else val)
        # custom vars
        if name in custom_map:
            cv = custom_map[name]
            vtype = cv.get("var_type", "text")
            val = cv.get("value", "")
            if vtype == "date":
                effective_fmt = fmt or cv.get("format") or None
                val = _format_date_value(val, effective_fmt) if effective_fmt else val
            return _escape_sql(val)
        # auto vars
        if name in context_vars:
            val = context_vars[name]
            if fmt:
                val = _format_date_value(val, fmt)
            return _escape_sql(val)
        # unknown: leave placeholder
        return m.group(0)

    return PLACEHOLDER_RE.sub(replacer, sql or "")
