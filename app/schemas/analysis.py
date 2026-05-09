from pydantic import BaseModel, Field
from typing import Optional
import datetime

class DerivedSleepDataResponse(BaseModel):
    derived_id: str = Field(..., description="Unique ID for the analysis result")
    user_id: str = Field(..., description="The user's ID")
    raw_id: str = Field(..., description="The source raw data ID")
    date: datetime.date = Field(..., description="Analysis date", example="2024-04-23")
    
    # Derived Metrics
    sleep_eff: Optional[float] = Field(None, description="Calculated sleep efficiency (0-1)", example=0.88)
    interrupt_index: Optional[float] = Field(None, description="Calculated interruption index", example=0.25)
    consistency_7d: Optional[float] = Field(None, description="7-day sleep consistency score", example=0.92)
    caff_gap_hours: Optional[float] = Field(None, description="Hours between last caffeine and sleep", example=7.5)
    caff_impact: Optional[float] = Field(None, description="Calculated impact of caffeine on sleep", example=0.05)
    screen_impact: Optional[float] = Field(None, description="Calculated impact of screen time", example=0.1)
    act_gap_hours: Optional[float] = Field(None, description="Hours between last activity and sleep", example=3.0)
    
    # Scoring
    penalty: float = Field(..., description="Total penalties applied", example=5.0)
    base_score: Optional[float] = Field(None, description="Rule-based base score (0-100)", example=85.0)
    ml_score: Optional[float] = Field(None, description="Machine Learning predicted score (0-100)", example=82.5)
    final_score_raw: Optional[float] = Field(None, description="Final blended score before rounding", example=83.75)
    user_score: Optional[float] = Field(None, description="Actual user feedback score", example=85.0)
    user_class: Optional[str] = Field(None, description="Predicted or actual classification", example="Good")
    final_score: Optional[int] = Field(None, description="Final rounded sleep quality score", example=84)
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class UserFeedback(BaseModel):
    user_score: float = Field(..., description="Ground truth score provided by user (0-100)", ge=0, le=100, example=90.0)
    user_class: Optional[str] = Field(None, description="User's subjective classification", example="Excellent")


class Recommendation(BaseModel):
    category: str = Field(..., description="Area of improvement", example="Caffeine")
    message: str = Field(..., description="Actionable advice for the user")
    priority: str = Field(..., description="Urgency level: 'high', 'medium', or 'low'", example="medium")
