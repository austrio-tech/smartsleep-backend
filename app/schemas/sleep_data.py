from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time, datetime

class RawSleepDataBase(BaseModel):
    record_date: date = Field(..., description="The date of the sleep record (YYYY-MM-DD)", example="2024-04-23")
    
    # Sleep timing
    sleep_time: Optional[time] = Field(None, description="Time the user went to bed", example="22:30:00")
    wake_time: Optional[time] = Field(None, description="Time the user woke up", example="07:00:00")
    awakenings: Optional[int] = Field(None, description="Number of times the user woke up during sleep", ge=0, example=2)
    sleep_latency_minutes: Optional[int] = Field(None, description="Minutes it took to fall asleep", ge=0, example=15)
    naps: Optional[int] = Field(None, description="Number of naps during the day", ge=0, example=0)
    
    # Bio-metrics
    hr_rest: Optional[int] = Field(None, description="Resting heart rate (BPM)", ge=30, le=200, example=60)
    hrv: Optional[int] = Field(None, description="Heart Rate Variability (ms)", ge=1, example=50)
    body_temp: Optional[float] = Field(None, description="Body temperature in Celsius", example=36.6)
    resp_rate: Optional[int] = Field(None, description="Respiratory rate (breaths per minute)", ge=8, example=14)
    
    # Lifestyle
    caffeine_time: Optional[time] = Field(None, description="Time of last caffeine intake", example="15:00:00")
    caffeine_mg: Optional[int] = Field(None, description="Amount of caffeine in mg", ge=0, example=100)
    alcohol_units: Optional[int] = Field(None, description="Alcohol units consumed", ge=0, example=0)
    water_liters: Optional[float] = Field(None, description="Water intake in liters", ge=0, example=2.0)
    steps: Optional[int] = Field(None, description="Total daily steps", ge=0, example=10000)
    activity_intensity: Optional[str] = Field(None, description="Daily activity level (Low, Medium, High)", example="Medium")
    screen_minutes_before_bed: Optional[int] = Field(None, description="Screen time in minutes before bed", ge=0, example=30)
    
    # Subjective
    stress: Optional[int] = Field(None, description="Subjective stress level (1-10)", ge=1, le=10, example=3)
    mood: Optional[int] = Field(None, description="Subjective mood level (1-10)", ge=1, le=10, example=7)
    
    # Environment
    room_temp: Optional[float] = Field(None, description="Room temperature in Celsius", example=20.5)
    noise_db: Optional[int] = Field(None, description="Average noise level in dB", ge=0, example=30)
    light_lux: Optional[int] = Field(None, description="Average light level in lux", ge=0, example=5)

class RawSleepDataCreate(RawSleepDataBase):
    pass

class RawSleepDataResponse(RawSleepDataBase):
    raw_id: str = Field(..., description="Unique ID for the raw data record")
    user_id: str = Field(..., description="The owner's user ID")
    created_at: datetime

    class Config:
        from_attributes = True
