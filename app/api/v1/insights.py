# ─────────────────────────────────────────────────────────────────────────────
# insights.py  –  Sleep recommendations API endpoint.
#
# This router provides personalised, actionable advice based on the user's
# most recent sleep analysis record. Each recommendation has:
#   - category: what area of sleep it targets (e.g., "Caffeine", "Sleep Duration")
#   - message:  the human-readable advice
#   - priority: "high", "medium", or "low" — so the app can highlight urgent ones
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.analysis import Recommendation

router = APIRouter()


def _build_recommendations(r: dict) -> List[Recommendation]:
    """Generate a list of personalised sleep recommendations from derived metrics.

    This function implements a rule-based recommendation engine. It checks
    each sleep metric against evidence-based thresholds and returns actionable
    advice for any metric that is outside the healthy range.

    Args:
        r: A row from the derived_sleep_data table containing computed sleep
           metrics (sleep_eff, tst, caff_impact, etc.).

    Returns:
        List[Recommendation]: A list of recommendation objects. If all metrics
        look healthy, a single positive "keep it up" message is returned.
    """
    recs = []  # We'll build up this list as we check each metric

    # ── Sleep efficiency ──────────────────────────────────────────────────────
    # Sleep efficiency = Total Sleep Time / Time in Bed.
    # Below 75% means you're spending more than 25% of your bed time awake.
    if (r.get("sleep_eff") or 1) < 0.75:
        recs.append(Recommendation(category="Sleep Efficiency", priority="high",
            message="Sleep efficiency below 75%. Go to bed only when sleepy and rise at the same time daily."))

    # ── Sleep continuity (awakenings) ─────────────────────────────────────────
    # interrupt_index > 0.3 means frequent mid-sleep awakenings.
    if (r.get("interrupt_index") or 0) > 0.3:
        recs.append(Recommendation(category="Sleep Continuity", priority="high",
            message="Frequent awakenings detected. Consider white noise, earplugs, or a sleep apnea evaluation."))

    # ── Caffeine timing ────────────────────────────────────────────────────────
    # caff_impact >= 0.5 means caffeine was consumed close to bedtime.
    # Caffeine's half-life is ~5-7 hours, so it should be cut off at least 6 hours before bed.
    if (r.get("caff_impact") or 0) >= 0.5:
        gap = r.get("caff_gap_hours") or 0
        recs.append(Recommendation(category="Caffeine", priority="high" if gap < 4 else "medium",
            message=f"Caffeine was consumed {gap:.1f}h before bed. Aim for at least 6 hours gap."))

    # ── Screen time ────────────────────────────────────────────────────────────
    # Blue light from screens suppresses melatonin (the sleep hormone).
    if (r.get("screen_impact") or 0) > 0.25:
        recs.append(Recommendation(category="Screen Time", priority="medium",
            message="High screen exposure before bed. Stop screens 30-60 minutes before sleep."))

    # ── Sleep schedule consistency ─────────────────────────────────────────────
    # Irregular sleep times disrupt the circadian rhythm (your internal body clock).
    if (r.get("consistency_7d") or 1) < 0.75:
        recs.append(Recommendation(category="Sleep Schedule", priority="medium",
            message="Inconsistent sleep timing this week. A fixed sleep/wake schedule strengthens your circadian rhythm."))

    # ── Psychological load (stress + mood) ────────────────────────────────────
    if (r.get("psych_load") or 0) > 0.6:
        recs.append(Recommendation(category="Stress & Mood", priority="medium",
            message="High psychological load detected. Try a 10-minute wind-down routine: journaling, breathing, or light reading."))

    # ── Biological readiness (biometrics) ─────────────────────────────────────
    # bio_ready is a z-score comparison against the user's personal baseline.
    # Low bio_ready means HR, HRV, or temperature are unusual for this person.
    if (r.get("bio_ready") or 1) < 0.4:
        recs.append(Recommendation(category="Biological Readiness", priority="medium",
            message="Your biometrics (HR, HRV, temperature) are outside your personal norm. Prioritise recovery today."))

    # ── Sleep environment ──────────────────────────────────────────────────────
    # The ideal sleep environment: ~18-20°C, quiet (<40dB), dark (<5 lux).
    if (r.get("env_score") or 1) < 0.5:
        recs.append(Recommendation(category="Sleep Environment", priority="low",
            message="Room conditions (temperature, noise, light) are suboptimal. Aim for 18-20°C, quiet, and darkness."))

    # ── Sleep duration ─────────────────────────────────────────────────────────
    # Adults need 7-9 hours of actual sleep (TST = Total Sleep Time in hours).
    if (r.get("tst") or 8) < 6:
        recs.append(Recommendation(category="Sleep Duration", priority="high",
            message=f"You only got {r.get('tst', 0):.1f}h of sleep. Adults need 7-9 hours for full cognitive recovery."))

    # ── Fallback: everything is healthy ───────────────────────────────────────
    if not recs:
        recs.append(Recommendation(category="General", priority="low",
            message="All metrics look healthy. Keep maintaining your current routine."))

    return recs


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(db=Depends(get_db), current_user=Depends(deps.get_current_user)):
    """Return personalised sleep improvement recommendations for the current user.

    Fetches the user's most recent sleep analysis record and passes its
    metrics to the rule-based recommendation engine.

    Args:
        db:           Supabase database client (injected by FastAPI).
        current_user: The authenticated user (from JWT).

    Returns:
        List[Recommendation]: Ordered list of sleep improvement recommendations.

    Raises:
        HTTPException 404: If the user has not submitted any sleep records yet.
    """
    # Fetch the single most recent derived_sleep_data row for this user
    rows = exec(
        db.table("derived_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("date", desc=True)  # Most recent first
        .limit(1)                  # We only need the latest record
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No analysis data found. Submit a sleep record first.")

    # Pass the row's metrics to the recommendation engine
    return _build_recommendations(rows[0])
