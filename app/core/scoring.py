def blend_scores(base_score: float, ml_score: float, learning_factor: float) -> float:
    """
    Step 9: Score Blending
    final_score = (1 - alpha) * base_score + alpha * ml_score
    """
    return (1 - learning_factor) * base_score + learning_factor * ml_score
