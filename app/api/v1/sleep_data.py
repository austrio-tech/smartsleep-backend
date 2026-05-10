from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from datetime import datetime

from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.sleep_data import RawSleepDataCreate, RawSleepDataResponse
from app.schemas.analysis import DerivedSleepDataResponse, UserFeedback
from app.services.sleep_analysis_service import process_daily_sleep, trigger_training

router = APIRouter()

# Pre-sleep fields captured in the evening before bed
_PRE_FIELDS = [
    "record_date", "caffeine_time", "caffeine_mg", "alcohol_units",
    "water_liters", "steps", "activity_intensity", "screen_minutes_before_bed", "stress",
]

# Post-sleep fields captured in the morning after waking
_POST_FIELDS = [
    "sleep_time", "wake_time", "awakenings", "sleep_latency_minutes",
    "naps", "hr_rest", "hrv", "body_temp", "resp_rate",
    "mood", "room_temp", "noise_db", "light_lux",
]


def _serialize(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _create_derived_stub(db, raw_id: str, user_id: str, record_date: str) -> None:
    """Insert a minimal derived row so the Flutter stage flips to waitingForPostSleep."""
    exec(
        db.table("derived_sleep_data").insert({
            "derived_id": str(uuid.uuid4()),
            "user_id": user_id,
            "raw_id": raw_id,
            "date": record_date,
        })
    )


@router.post("/ingest", response_model=RawSleepDataResponse)
def ingest_sleep_data(
    data_in: RawSleepDataCreate,
    db=Depends(get_db),
    current_user=Depends(deps.get_current_user),
):
    phase = data_in.phase
    record_date_str = data_in.record_date.isoformat()
    now = datetime.utcnow().isoformat()

    existing = exec(
        db.table("raw_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .eq("record_date", record_date_str)
    )
    existing_row = existing[0] if existing else None

    if phase == "pre":
        # Block if there is already an un-completed pre-sleep record (any date)
        pending = exec(
            db.table("raw_sleep_data")
            .select("raw_id")
            .eq("user_id", current_user.user_id)
            .not_.is_("pre_sleep_submitted_at", "null")
            .is_("post_sleep_submitted_at", "null")
        )
        if pending:
            raise HTTPException(
                status_code=400,
                detail="Complete your morning check-in before starting a new evening log.",
            )
        if existing_row and existing_row.get("pre_sleep_submitted_at"):
            raise HTTPException(
                status_code=400,
                detail="Evening habits already logged for today.",
            )

        raw_id = str(uuid.uuid4())
        raw_data = {
            "raw_id": raw_id,
            "user_id": current_user.user_id,
            "pre_sleep_submitted_at": now,
        }
        for k in _PRE_FIELDS:
            v = getattr(data_in, k, None)
            raw_data[k] = _serialize(v)

        rows = exec(db.table("raw_sleep_data").insert(raw_data))
        _create_derived_stub(db, raw_id, current_user.user_id, record_date_str)
        return rows[0] if rows else raw_data

    else:  # phase == "post"
        if not existing_row:
            raise HTTPException(
                status_code=400,
                detail="No evening log found for this date. Log your evening habits first.",
            )
        if not existing_row.get("pre_sleep_submitted_at"):
            raise HTTPException(
                status_code=400,
                detail="Evening habits must be logged before the morning check-in.",
            )
        if existing_row.get("post_sleep_submitted_at"):
            raise HTTPException(
                status_code=400,
                detail="Morning check-in already submitted for this date.",
            )

        raw_id = existing_row["raw_id"]
        update_data: dict = {"post_sleep_submitted_at": now}
        for k in _POST_FIELDS:
            v = getattr(data_in, k, None)
            if v is not None:
                update_data[k] = _serialize(v)

        exec(db.table("raw_sleep_data").update(update_data).eq("raw_id", raw_id))
        process_daily_sleep(db, raw_id, current_user)

        rows = exec(db.table("raw_sleep_data").select("*").eq("raw_id", raw_id))
        return rows[0] if rows else existing_row


@router.get("/history", response_model=List[DerivedSleepDataResponse])
def get_sleep_history(db=Depends(get_db), current_user=Depends(deps.get_current_user)):
    return exec(
        db.table("derived_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("date", desc=True)
    )


@router.get("/analysis/latest", response_model=DerivedSleepDataResponse)
def get_latest_analysis(db=Depends(get_db), current_user=Depends(deps.get_current_user)):
    rows = exec(
        db.table("derived_sleep_data")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("date", desc=True)
        .limit(1)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No analysis records found.")
    return rows[0]


@router.post("/analysis/feedback", response_model=DerivedSleepDataResponse)
def submit_feedback(
    feedback: UserFeedback,
    db=Depends(get_db),
    current_user=Depends(deps.get_current_user),
):
    latest = exec(
        db.table("derived_sleep_data")
        .select("derived_id")
        .eq("user_id", current_user.user_id)
        .not_.is_("tst", "null")  # only records that have full analysis
        .is_("user_score", "null")  # not yet rated
        .order("date", desc=True)
        .limit(1)
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No completed analysis awaiting feedback.")

    derived_id = latest[0]["derived_id"]

    rows = exec(
        db.table("derived_sleep_data")
        .update({"user_score": feedback.user_score, "user_class": feedback.user_class})
        .eq("derived_id", derived_id)
    )

    trigger_training(db, derived_id, current_user.user_id, feedback.user_score, feedback.user_class)

    return rows[0] if rows else latest[0]
