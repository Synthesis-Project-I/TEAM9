import pandas as pd

from src.pipeline.filtering import TaskAssignmentCSP


def test_get_eligible_translators_filters_language_budget_quality_and_schedule():
    translators = pd.DataFrame({
        "NAME": ["Alice", "Bob"],
        "START": ["08:00:00", "08:00:00"],
        "END": ["17:00:00", "17:00:00"],
        "MON": [1, 1],
        "TUES": [1, 1],
        "WED": [1, 1],
        "THURS": [1, 1],
        "FRI": [1, 1],
        "SAT": [0, 0],
        "SUN": [0, 0],
        "English_Spanish": [10, 50],
        "AVERAGE_QUALITY": [8, 4],
        "ON_TIME_SCORE": [1.0, 1.0],
        "Translation_experience": [5, 5],
        "SUB_Test": [3, 3],
    })
    reqs = {
        "language_pair": "English_Spanish",
        "task_date": "2024-01-01",
        "task_length_hours": 2,
        "window_days": 1,
        "max_hourly_rate": 20,
        "min_quality": 7,
        "min_on_time_score": 0,
        "task_type": "Translation",
        "required_subindustry": ["Test"],
        "min_subindustry_experience": 1,
    }

    result = TaskAssignmentCSP(translators).get_eligible_translators(reqs)

    assert result["NAME"].tolist() == ["Alice"]
