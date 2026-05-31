import pandas as pd

from src.pipeline.output import format_recommendations


def test_format_recommendations_keeps_existing_columns():
    candidates = pd.DataFrame({
        "SUITABILITY_SCORE": [90],
        "NAME": ["Alice"],
        "English_Spanish": [10],
        "AVERAGE_QUALITY": [8],
        "ON_TIME_SCORE": [1.0],
    })
    reqs = {"required_subindustry": ["Missing"]}

    result = format_recommendations(candidates, reqs, "English_Spanish")

    assert result.columns.tolist() == ["SUITABILITY_SCORE", "NAME", "English_Spanish", "AVERAGE_QUALITY", "ON_TIME_SCORE"]
