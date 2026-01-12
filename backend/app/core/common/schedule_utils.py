#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities for scheduled tasks
"""

from typing import Optional, Union
from datetime import datetime


def calculate_next_run(cron_expr: str, return_datetime: bool = False) -> Optional[Union[str, datetime]]:
    """
    Calculate next run time from cron expression

    Args:
        cron_expr: Cron expression string
        return_datetime: If True, return datetime object; if False, return ISO string

    Returns:
        Next run time as datetime object or ISO string, or None if invalid
    """
    if not cron_expr:
        return None
    try:
        from cronsim import CronSim

        base = datetime.now()
        it = CronSim(cron_expr, base)
        next_run = next(it)
        return next_run if return_datetime else next_run.isoformat()
    except Exception:
        return None
