from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.api import deps
from app.database import get_db
from app.schemas.analysis import Recommendation

router = APIRouter()


def _build_recommendations(record: dict) -> List[Recommendation]:
    recs = []

    sleep_eff = record.get("sleep_eff")
    interrupt_index = record.get("interrupt_index")
    caff_impact = record.get("caff_impact")
    screen_impact = record.get("screen_impact")
    consistency_7d = record.get("consistency_7d")
    caff_gap_hours = record.get("caff_gap_hours")

    if sleep_eff is not None and sleep_eff < 0.80:
        recs.append(Recommendation(
            category="Sleep Efficiency",
            message="Your sleep efficiency is below 80%. Try going to bed only when sleepy and getting up at the same time each day.",
            priority="high",
        ))

    if interrupt_index is not None and interrupt_index > 0.30:
        recs.append(Recommendation(
            category="Sleep Continuity",
            message="You had frequent awakenings. Consider earplugs, a white-noise machine, or checking for sleep apnea.",
            priority="high",
        ))

    if caff_impact is not None and caff_impact > 0.10:
        recs.append(Recommendation(
            category="Caffeine",
            message="Caffeine is affecting your sleep. Avoid caffeine at least 6 hours before bed.",
            priority="medium",
        ))

    if screen_impact is not None and screen_impact > 0.10:
        recs.append(Recommendation(
            category="Screen Time",
            message="Screen exposure before bed is impacting sleep quality. Stop screens at least 30 minutes before sleep.",
            priority="medium",
        ))

    if consistency_7d is not None and consistency_7d < 0.75:
        recs.append(Recommendation(
            category="Sleep Schedule",
            message="Your sleep schedule is inconsistent. Maintaining a regular sleep and wake time strengthens your circadian rhythm.",
            priority="medium",
        ))

    if caff_gap_hours is not None and caff_gap_hours < 6.0:
        recs.append(Recommendation(
            category="Caffeine Timing",
            message=f"Your last caffeine was only {caff_gap_hours:.1f}h before sleep. Aim for at least 6 hours gap.",
            priority="medium",
        ))

    if not recs:
        recs.append(Recommendation(
            category="General",
            message="Great job! Your sleep metrics look healthy. Keep maintaining your current routine.",
            priority="low",
        ))

    return recs


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(db=Depends(get_db), current_user=Depends(deps.get_current_user)):
    result = (
        db.table("derived_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No analysis data found. Submit a sleep record first.")
    return _build_recommendations(result.data[0])
