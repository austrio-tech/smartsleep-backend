from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.database import get_db
from app.models.user import User
from app.models.derived_sleep_data import DerivedSleepData
from app.schemas.analysis import Recommendation

router = APIRouter()


def _build_recommendations(record: DerivedSleepData) -> List[Recommendation]:
    recs = []

    if record.sleep_eff is not None and record.sleep_eff < 0.80:
        recs.append(Recommendation(
            category="Sleep Efficiency",
            message="Your sleep efficiency is below 80%. Try going to bed only when sleepy and getting up at the same time each day.",
            priority="high"
        ))

    if record.interrupt_index is not None and record.interrupt_index > 0.30:
        recs.append(Recommendation(
            category="Sleep Continuity",
            message="You had frequent awakenings. Consider earplugs, a white-noise machine, or checking for sleep apnea.",
            priority="high"
        ))

    if record.caff_impact is not None and record.caff_impact > 0.10:
        recs.append(Recommendation(
            category="Caffeine",
            message="Caffeine is affecting your sleep. Avoid caffeine at least 6 hours before bed.",
            priority="medium"
        ))

    if record.screen_impact is not None and record.screen_impact > 0.10:
        recs.append(Recommendation(
            category="Screen Time",
            message="Screen exposure before bed is impacting sleep quality. Stop screens at least 30 minutes before sleep.",
            priority="medium"
        ))

    if record.consistency_7d is not None and record.consistency_7d < 0.75:
        recs.append(Recommendation(
            category="Sleep Schedule",
            message="Your sleep schedule is inconsistent. Maintaining a regular sleep and wake time strengthens your circadian rhythm.",
            priority="medium"
        ))

    if record.caff_gap_hours is not None and record.caff_gap_hours < 6.0:
        recs.append(Recommendation(
            category="Caffeine Timing",
            message=f"Your last caffeine was only {record.caff_gap_hours:.1f}h before sleep. Aim for at least 6 hours gap.",
            priority="medium"
        ))

    if not recs:
        recs.append(Recommendation(
            category="General",
            message="Great job! Your sleep metrics look healthy. Keep maintaining your current routine.",
            priority="low"
        ))

    return recs


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Return personalised sleep improvement recommendations based on the latest analysis."""
    record = (
        db.query(DerivedSleepData)
        .filter(DerivedSleepData.user_id == current_user.user_id)
        .order_by(DerivedSleepData.date.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No analysis data found. Submit a sleep record first.")

    return _build_recommendations(record)
