from typing import Tuple

def update_stats(mean: float, std: float, count: int, new_val: float) -> Tuple[float, float, int]:
    """
    Welford's algorithm for computing running mean and standard deviation.
    """
    count += 1
    delta = new_val - mean
    mean += delta / count
    delta2 = new_val - mean
    # M2 is used to track sum of squares of differences from the mean
    # M2 = std^2 * (count - 1)
    m2 = (std ** 2) * (count - 1) if count > 1 else 0
    m2 += delta * delta2
    
    new_std = (m2 / (count - 1)) ** 0.5 if count > 1 else 0
    return mean, new_std, count
