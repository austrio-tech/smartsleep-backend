from typing import Dict

def calculate_base_score(features: Dict[str, float]) -> float:
    """
    Step 8: Rule-based base scoring (0-100)
    """
    # Weights for different factors
    weights = {
        "sleep_eff": 0.5,
        "interrupt_index": -0.2,
        "caff_gap": -0.15,
        "screen_impact": -0.15
    }
    
    score = 80.0 # Starting base
    
    # Efficiency component
    score += (features["sleep_eff"] - 0.85) * 100 * weights["sleep_eff"]
    
    # Interruptions
    score += features["interrupt_index"] * 100 * weights["interrupt_index"]
    
    # Caffeine Gap (penalty if < 6 hours)
    if features["caff_gap_hours"] < 6:
        gap_penalty = (6 - features["caff_gap_hours"]) * 5
        score += gap_penalty * weights["caff_gap"]
        
    # Screen impact
    score += features["screen_impact"] * 100 * weights["screen_impact"]
    
    return max(0.0, min(100.0, score))

def calculate_penalties(raw_data) -> float:
    penalty = 0.0
    if raw_data.alcohol_units and raw_data.alcohol_units > 2:
        penalty += 10.0
    if raw_data.stress and raw_data.stress > 7:
        penalty += 5.0
    return penalty
