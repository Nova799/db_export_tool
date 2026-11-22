"""Scheduling helpers for recovery frequencies."""

from datetime import datetime, timedelta


def compute_next_execution(frequency, from_date=None):
    """Compute the next execution datetime for a given frequency.

    frequency: 'manual' | 'weekly' | 'monthly' | 'quarterly'
    Returns ISO string or None for manual.
    """
    base = from_date or datetime.now()
    freq = (frequency or "manual").lower()
    if freq == "manual":
        return None
    if freq == "weekly":
        return (base + timedelta(days=7)).isoformat()
    if freq == "monthly":
        # same day next month
        year = base.year + (1 if base.month == 12 else 0)
        month = 1 if base.month == 12 else base.month + 1
        day = min(base.day, 28)
        return base.replace(year=year, month=month, day=day).isoformat()
    if freq == "quarterly":
        month = base.month + 3
        year = base.year
        while month > 12:
            month -= 12
            year += 1
        day = min(base.day, 28)
        return base.replace(year=year, month=month, day=day).isoformat()
    return None
