from pydantic import BaseModel, Field
from typing import Optional
import datetime


class DerivedSleepDataResponse(BaseModel):
    derived_id: str
    user_id:    str
    raw_id:     str
    date:       datetime.date

    # Step 2 — Core sleep metrics
    tib:             Optional[float] = Field(None, description="Time in Bed (hours)")
    tst:             Optional[float] = Field(None, description="Total Sleep Time (hours)")
    sleep_eff:       Optional[float] = Field(None, description="Sleep Efficiency (0-1)")
    interrupt_index: Optional[float] = Field(None, description="Interruption Index")
    consistency_7d:  Optional[float] = Field(None, description="7-day sleep schedule consistency (0-1)")

    # Step 3 — Lifestyle
    caff_gap_hours: Optional[float] = Field(None, description="Hours between last caffeine and sleep")
    caff_impact:    Optional[float] = Field(None, description="Caffeine impact factor (0.1 / 0.5 / 1.0)")
    screen_impact:  Optional[float] = Field(None, description="Screen exposure impact")
    act_gap_hours:  Optional[float] = Field(None, description="Activity intensity impact")

    # Steps 4-6 — Bio / Psych / Env
    bio_ready:  Optional[float] = Field(None, description="Biological Readiness Score (0-1)")
    psych_load: Optional[float] = Field(None, description="Psychological Load (0-1)")
    env_score:  Optional[float] = Field(None, description="Environmental Quality Score (0-1)")

    # Scoring
    penalty:         float
    base_score:      Optional[float] = Field(None, description="Rule-based base score (0-1)")
    ml_score:        Optional[float] = Field(None, description="ML predicted score (0-100)")
    final_score_raw: Optional[float] = Field(None, description="Final blended score before clamping")
    final_score:     Optional[int]   = Field(None, description="Final sleep quality score (0-100)")
    user_score:      Optional[float] = Field(None, description="User's own rating (0-100)")
    user_class:      Optional[str]   = Field(None, description="Excellent / Good / Fair / Poor")

    created_at: datetime.datetime

    class Config:
        from_attributes = True


class UserFeedback(BaseModel):
    user_score: float = Field(..., ge=0, le=100, description="User's own sleep rating (0-100)")
    user_class: Optional[str] = Field(None, description="Excellent / Good / Fair / Poor")


class Recommendation(BaseModel):
    category: str = Field(..., description="Area of improvement")
    message:  str = Field(..., description="Actionable advice")
    priority: str = Field(..., description="high / medium / low")
