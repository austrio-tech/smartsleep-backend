from datetime import datetime, time, date, timedelta
from typing import Any, Optional, List
import statistics


def _to_time(val):
    if val is None:
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2].split(".")[0]) if len(parts) > 2 else 0)
    return val


def _duration_hours(start: time, end: time) -> float:
    s = datetime.combine(date.today(), start)
    e = datetime.combine(date.today(), end)
    if e < s:
        e += timedelta(days=1)
    return (e - s).total_seconds() / 3600


# ── Step 2: Core sleep metrics ────────────────────────────────────────────────

def _tib_tst(raw_data: Any):
    st = _to_time(raw_data.sleep_time)
    wt = _to_time(raw_data.wake_time)
    if not st or not wt:
        return 0.0, 0.0
    tib = _duration_hours(st, wt)
    if tib <= 0:
        return 0.0, 0.0
    latency_h = (raw_data.sleep_latency_minutes or 0) / 60
    awakening_h = (raw_data.awakenings or 0) * 5 / 60   # ~5 min per awakening
    tst = max(0.0, tib - latency_h - awakening_h)
    return round(tib, 4), round(tst, 4)


# ── Step 3: Lifestyle features ────────────────────────────────────────────────

def _caff_gap(raw_data: Any) -> float:
    ct = _to_time(raw_data.caffeine_time)
    st = _to_time(raw_data.sleep_time)
    if not ct or not st:
        return 24.0
    return round(_duration_hours(ct, st), 4)


def _caff_impact(gap_hours: float) -> float:
    """Step 3 formula: 1.0 if gap<4h, 0.5 if 4-6h, 0.1 otherwise."""
    if gap_hours < 4:
        return 1.0
    if gap_hours < 6:
        return 0.5
    return 0.1


def _screen_impact(raw_data: Any) -> float:
    """screen_minutes / 120  (Step 3)."""
    return round((raw_data.screen_minutes_before_bed or 0) / 120.0, 4)


def _act_impact(raw_data: Any) -> float:
    """Encode activity_intensity as numeric impact (proxy for act_gap)."""
    intensity = (raw_data.activity_intensity or "").strip().lower()
    if intensity == "high":
        return 1.0
    if intensity == "medium":
        return 0.5
    return 0.0


# ── Step 4: Biological Readiness ──────────────────────────────────────────────

def _bio_ready(raw_data: Any, user_stat: Optional[dict]) -> float:
    if not user_stat or (user_stat.get("sample_count") or 0) < 2:
        return 0.5  # neutral until baseline exists

    z_sum = 0.0
    n = 0

    if raw_data.hr_rest and (user_stat.get("std_hr_rest") or 0) > 0:
        z_sum += abs((raw_data.hr_rest - user_stat["mean_hr_rest"]) / user_stat["std_hr_rest"])
        n += 1

    if raw_data.hrv and (user_stat.get("std_hrv") or 0) > 0:
        # High HRV is good → deviation from personal mean is still a sign of irregularity
        z_sum += abs((raw_data.hrv - user_stat["mean_hrv"]) / user_stat["std_hrv"])
        n += 1

    if raw_data.body_temp and (user_stat.get("std_body_temp") or 0) > 0:
        z_sum += abs((raw_data.body_temp - user_stat["mean_body_temp"]) / user_stat["std_body_temp"])
        n += 1

    if n == 0:
        return 0.5

    avg_z = z_sum / n
    return round(max(0.0, min(1.0, 1 - avg_z / 3)), 4)


# ── Step 5: Psychological Load ────────────────────────────────────────────────

def _psych_load(raw_data: Any) -> float:
    stress_factor = (raw_data.stress or 5) / 10
    mood_factor = 1 - (raw_data.mood or 5) / 10
    return round((stress_factor + mood_factor) / 2, 4)


# ── Step 6: Environmental Score ───────────────────────────────────────────────

def _env_score(raw_data: Any) -> float:
    temp_score  = max(0.0, 1 - abs((raw_data.room_temp  or 22)  - 22) / 10)
    noise_score = max(0.0, 1 - (raw_data.noise_db or 0) / 80)
    light_score = max(0.0, 1 - (raw_data.light_lux or 0) / 300)
    return round((temp_score + noise_score + light_score) / 3, 4)


# ── Step 2 continued: Consistency 7d ─────────────────────────────────────────

def _consistency_7d(last_7_sleep_times: Optional[List[str]]) -> float:
    """1 - std_dev(sleep_times_last_7d) / 24  (Step 2)."""
    if not last_7_sleep_times or len(last_7_sleep_times) < 2:
        return 1.0

    def to_h(t_str):
        t = _to_time(t_str)
        return (t.hour + t.minute / 60) if t else None

    hours = [h for h in (to_h(t) for t in last_7_sleep_times) if h is not None]
    if len(hours) < 2:
        return 1.0
    return round(max(0.0, min(1.0, 1 - statistics.stdev(hours) / 24)), 4)


# ── Step 7: Full feature computation ─────────────────────────────────────────

def compute_features(
    raw_data: Any,
    user_stat: Optional[dict] = None,
    last_7_sleep_times: Optional[List[str]] = None,
) -> dict:
    tib, tst = _tib_tst(raw_data)
    sleep_eff = round(tst / tib, 4) if tib > 0 else 0.0
    interrupt_index = round((raw_data.awakenings or 0) / tst, 4) if tst > 0 else 0.0
    caff_gap = _caff_gap(raw_data)

    return {
        "tib":            tib,
        "tst":            tst,
        "sleep_eff":      sleep_eff,
        "interrupt_index": interrupt_index,
        "consistency_7d": _consistency_7d(last_7_sleep_times),
        "caff_gap_hours": caff_gap,
        "caff_impact":    _caff_impact(caff_gap),
        "screen_impact":  _screen_impact(raw_data),
        "act_gap_hours":  _act_impact(raw_data),   # stores act_impact (no timestamp available)
        "bio_ready":      _bio_ready(raw_data, user_stat),
        "psych_load":     _psych_load(raw_data),
        "env_score":      _env_score(raw_data),
    }


def feature_vector(features: dict) -> list:
    """Step 7: ordered 10-element vector X for ML."""
    return [
        features["tst"],
        features["sleep_eff"],
        features["interrupt_index"],
        features["consistency_7d"],
        features["caff_impact"],
        features["screen_impact"],
        features["act_gap_hours"],
        features["bio_ready"],
        features["psych_load"],
        features["env_score"],
    ]
