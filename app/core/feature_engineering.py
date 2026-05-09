from datetime import datetime, time, date, timedelta
from typing import Any


def _to_time(val) -> time:
    if val is None:
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2].split(".")[0]) if len(parts) > 2 else 0)
    return val


def calculate_duration_hours(start: time, end: time) -> float:
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return (end_dt - start_dt).total_seconds() / 3600


def compute_sleep_efficiency(raw_data: Any) -> float:
    sleep_time = _to_time(raw_data.sleep_time)
    wake_time = _to_time(raw_data.wake_time)
    if not sleep_time or not wake_time:
        return 0.0

    total_time_in_bed = calculate_duration_hours(sleep_time, wake_time)
    if total_time_in_bed <= 0:
        return 0.0

    latency_hours = (raw_data.sleep_latency_minutes or 0) / 60
    awakening_penalty = (raw_data.awakenings or 0) * 5 / 60
    tst = total_time_in_bed - latency_hours - awakening_penalty
    return max(0.0, min(1.0, tst / total_time_in_bed))


def compute_caffeine_gap(raw_data: Any) -> float:
    caffeine_time = _to_time(raw_data.caffeine_time)
    sleep_time = _to_time(raw_data.sleep_time)
    if not caffeine_time or not sleep_time:
        return 24.0
    return calculate_duration_hours(caffeine_time, sleep_time)


def compute_features(raw_data: Any) -> dict:
    return {
        "sleep_eff": compute_sleep_efficiency(raw_data),
        "interrupt_index": (raw_data.awakenings or 0) / 8.0,
        "caff_gap_hours": compute_caffeine_gap(raw_data),
        "screen_impact": (raw_data.screen_minutes_before_bed or 0) / 60.0,
    }
