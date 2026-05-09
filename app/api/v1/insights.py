from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.analysis import Recommendation

router = APIRouter()


def _build_recommendations(r: dict) -> List[Recommendation]:
    recs = []

    if (r.get("sleep_eff") or 1) < 0.75:
        recs.append(Recommendation(category="Sleep Efficiency", priority="high",
            message="Sleep efficiency below 75%. Go to bed only when sleepy and rise at the same time daily."))

    if (r.get("interrupt_index") or 0) > 0.3:
        recs.append(Recommendation(category="Sleep Continuity", priority="high",
            message="Frequent awakenings detected. Consider white noise, earplugs, or a sleep apnea evaluation."))

    if (r.get("caff_impact") or 0) >= 0.5:
        gap = r.get("caff_gap_hours") or 0
        recs.append(Recommendation(category="Caffeine", priority="high" if gap < 4 else "medium",
            message=f"Caffeine was consumed {gap:.1f}h before bed. Aim for at least 6 hours gap."))

    if (r.get("screen_impact") or 0) > 0.25:
        recs.append(Recommendation(category="Screen Time", priority="medium",
            message="High screen exposure before bed. Stop screens 30-60 minutes before sleep."))

    if (r.get("consistency_7d") or 1) < 0.75:
        recs.append(Recommendation(category="Sleep Schedule", priority="medium",
            message="Inconsistent sleep timing this week. A fixed sleep/wake schedule strengthens your circadian rhythm."))

    if (r.get("psych_load") or 0) > 0.6:
        recs.append(Recommendation(category="Stress & Mood", priority="medium",
            message="High psychological load detected. Try a 10-minute wind-down routine: journaling, breathing, or light reading."))

    if (r.get("bio_ready") or 1) < 0.4:
        recs.append(Recommendation(category="Biological Readiness", priority="medium",
            message="Your biometrics (HR, HRV, temperature) are outside your personal norm. Prioritise recovery today."))

    if (r.get("env_score") or 1) < 0.5:
        recs.append(Recommendation(category="Sleep Environment", priority="low",
            message="Room conditions (temperature, noise, light) are suboptimal. Aim for 18-20°C, quiet, and darkness."))

    if (r.get("tst") or 8) < 6:
        recs.append(Recommendation(category="Sleep Duration", priority="high",
            message=f"You only got {r.get('tst', 0):.1f}h of sleep. Adults need 7-9 hours for full cognitive recovery."))

    if not recs:
        recs.append(Recommendation(category="General", priority="low",
            message="All metrics look healthy. Keep maintaining your current routine."))

    return recs


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(db=Depends(get_db), current_user=Depends(deps.get_current_user)):
    rows = exec(
        db.table("derived_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("date", desc=True)
        .limit(1)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No analysis data found. Submit a sleep record first.")
    return _build_recommendations(rows[0])
