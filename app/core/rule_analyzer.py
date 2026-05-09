from typing import Any, Dict


def calculate_base_score(features: Dict[str, float]) -> float:
    """
    Step 10 weighted formula — returns 0-1.
    base = 0.25·norm(TST) + 0.20·sleep_eff + 0.15·consistency_7d
         + 0.15·(1-interrupt_index) + 0.15·(1-psych_load) + 0.10·bio_ready
    """
    tst_norm = min(1.0, features.get("tst", 0.0) / 8.0)   # ideal TST = 8h
    score = (
        0.25 * tst_norm +
        0.20 * features.get("sleep_eff", 0.0) +
        0.15 * features.get("consistency_7d", 1.0) +
        0.15 * (1.0 - min(1.0, features.get("interrupt_index", 0.0))) +
        0.15 * (1.0 - features.get("psych_load", 0.5)) +
        0.10 * features.get("bio_ready", 0.5)
    )
    return round(max(0.0, min(1.0, score)), 4)


def calculate_penalties(raw_data: Any, features: Dict[str, float]) -> float:
    """Step 8: deterministic rule penalties."""
    penalty = 0.0

    if features.get("caff_gap_hours", 24.0) < 4:
        penalty += 8.0

    if (raw_data.stress or 0) > 7:
        penalty += 6.0

    if features.get("sleep_eff", 1.0) < 0.75:
        penalty += 10.0

    if (raw_data.awakenings or 0) > 4:
        penalty += 6.0

    if (raw_data.alcohol_units or 0) > 2:
        penalty += 10.0

    return penalty
