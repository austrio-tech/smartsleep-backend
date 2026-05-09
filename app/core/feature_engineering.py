from datetime import datetime, time, date, timedelta
from typing import Optional
import math
from app.models.raw_sleep_data import RawSleepData

def calculate_duration_hours(start: time, end: time) -> float:
    # Handles wrap around midnight
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    duration = end_dt - start_dt
    return duration.total_seconds() / 3600

def compute_sleep_efficiency(raw_data: RawSleepData) -> float:
    if not raw_data.sleep_time or not raw_data.wake_time:
        return 0.0
    
    total_time_in_bed = calculate_duration_hours(raw_data.sleep_time, raw_data.wake_time)
    if total_time_in_bed <= 0:
        return 0.0
    
    # TST = Time in Bed - Latency - Awakenings (simplified)
    latency_hours = (raw_data.sleep_latency_minutes or 0) / 60
    # Assuming each awakening costs 5 mins on average if not specified
    awakening_penalty = (raw_data.awakenings or 0) * 5 / 60
    
    tst = total_time_in_bed - latency_hours - awakening_penalty
    return max(0.0, min(1.0, tst / total_time_in_bed))

def compute_caffeine_gap(raw_data: RawSleepData) -> float:
    if not raw_data.caffeine_time or not raw_data.sleep_time:
        return 24.0 # Default if no caffeine
    
    # Gap between last caffeine and sleep
    gap = calculate_duration_hours(raw_data.caffeine_time, raw_data.sleep_time)
    # If caffeine was after sleep (likely previous day), it should be a large gap or handled differently
    # But usually caffeine_time is on the same record_date as pre-sleep input
    return gap

def compute_features(raw_data: RawSleepData):
    features = {
        "sleep_eff": compute_sleep_efficiency(raw_data),
        "interrupt_index": (raw_data.awakenings or 0) / 8.0, # Normalized by 8 hours
        "caff_gap_hours": compute_caffeine_gap(raw_data),
        "screen_impact": (raw_data.screen_minutes_before_bed or 0) / 60.0,
    }
    return features
