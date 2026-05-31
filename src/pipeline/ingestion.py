import pandas as pd


def build_task_input(company_name, task_date, task_deadline, task_start_time, task_end_time, task_length_hours, language_pair, task_type="Translation", followed_by=None):
    """Validate and parse the incoming task."""
    pd.to_datetime(task_date)
    pd.to_datetime(task_deadline)
    return {
        "company_name": company_name,
        "task_date": task_date,
        "task_deadline": task_deadline,
        "task_start_time": task_start_time,
        "task_end_time": task_end_time,
        "task_length_hours": float(task_length_hours),
        "language_pair": language_pair,
        "task_type": task_type,
        "followed_by": followed_by,
    }
