from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.sleep_data import RawSleepDataCreate, RawSleepDataResponse
from app.schemas.analysis import DerivedSleepDataResponse, UserFeedback
from app.services.sleep_analysis_service import process_daily_sleep

router = APIRouter()

@router.post("/ingest", response_model=RawSleepDataResponse)
def ingest_sleep_data(
    data_in: RawSleepDataCreate,
    db=Depends(get_db),
    current_user=Depends(deps.get_current_user),
):
    raw_id = str(uuid.uuid4())
    raw_data = {"raw_id": raw_id, "user_id": current_user.user_id}
    for k, v in data_in.model_dump().items():
        raw_data[k] = v.isoformat() if hasattr(v, "isoformat") else v

    rows = exec(db.table("raw_sleep_data").insert(raw_data))
    process_daily_sleep(db, raw_id, current_user)
    return rows[0] if rows else raw_data


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
        .order("date", desc=True)
        .limit(1)
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No analysis records found.")

    rows = exec(
        db.table("derived_sleep_data")
        .update({"user_score": feedback.user_score, "user_class": feedback.user_class})
        .eq("derived_id", latest[0]["derived_id"])
    )
    return rows[0]
