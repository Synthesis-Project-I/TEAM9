import pandas as pd

from src.pipeline.scoring import rank_candidates


def test_rank_candidates_adds_score_and_sorts():
    candidates = pd.DataFrame({
        "NAME": ["A", "B"],
        "English_Spanish": [10, 20],
        "AVERAGE_QUALITY": [8, 7],
        "ON_TIME_SCORE": [1.0, 0.5],
        "SUB_Test": [2, 1],
    })
    task_reqs = {
        "language_pair": "English_Spanish",
        "max_hourly_rate": 30,
        "min_quality": 6,
        "wildcard": "quality",
        "task_type": "Translation",
        "required_subindustry": ["Test"],
    }

    ranked = rank_candidates(candidates, task_reqs)

    assert "SUITABILITY_SCORE" in ranked.columns
    assert ranked.iloc[0]["SUITABILITY_SCORE"] >= ranked.iloc[1]["SUITABILITY_SCORE"]
