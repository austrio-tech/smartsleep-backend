def blend_scores(base_score: float, ml_score: float, learning_factor: float) -> float:
    """
    Step 16: progressive personalization.
    base_score : 0-1  (from rule-based weighted formula)
    ml_score   : 0-100 (SGDRegressor trained on user_score)
    learning_factor: min(1, n/60)

    Returns raw score 0-100 before penalty subtraction.
    """
    return (1 - learning_factor) * base_score * 100 + learning_factor * ml_score
