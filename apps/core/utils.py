"""
Utils for the application
"""
from datetime import datetime, timedelta


def get_week_range(date=None):
    """Get the start and end date of the week."""
    if date is None:
        date = datetime.now().date()
    
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_month_range(date=None):
    """Get the start and end date of the month."""
    if date is None:
        date = datetime.now().date()
    
    if date.month == 12:
        end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
    
    start = date.replace(day=1)
    return start, end
