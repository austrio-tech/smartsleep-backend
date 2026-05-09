from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.database import get_db
from app.models.user import User
from app.models.raw_sleep_data import RawSleepData
from app.models.derived_sleep_data import DerivedSleepData
from app.schemas.sleep_data import RawSleepDataCreate, RawSleepDataResponse
from app.schemas.analysis import DerivedSleepDataResponse, UserFeedback
from app.services.sleep_analysis_service import process_daily_sleep

router = APIRouter()

@router.post("/ingest", response_model=RawSleepDataResponse)
def ingest_sleep_data(
    data_in: RawSleepDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Ingest raw sleep and lifestyle data.

    Upon ingestion, automatically triggers the analysis pipeline to calculate
    derived metrics and a sleep quality score.
    """
    db_raw = RawSleepData(
        **data_in.model_dump(),
        user_id=current_user.user_id
    )
    db.add(db_raw)
    db.commit()
    db.refresh(db_raw)

    process_daily_sleep(db, db_raw.raw_id, current_user)

    return db_raw


@router.get("/history", response_model=List[DerivedSleepDataResponse])
def get_sleep_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Retrieve all analysed sleep records for the current user, newest first."""
    return (
        db.query(DerivedSleepData)
        .filter(DerivedSleepData.user_id == current_user.user_id)
        .order_by(DerivedSleepData.date.desc())
        .all()
    )


@router.get("/analysis/latest", response_model=DerivedSleepDataResponse)
def get_latest_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Return the most recent sleep analysis result for the current user."""
    record = (
        db.query(DerivedSleepData)
        .filter(DerivedSleepData.user_id == current_user.user_id)
        .order_by(DerivedSleepData.date.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No analysis records found.")
    return record


@router.post("/analysis/feedback", response_model=DerivedSleepDataResponse)
def submit_feedback(
    feedback: UserFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Submit subjective feedback on the most recent sleep analysis.

    Updates user_score and user_class on the latest derived record.
    """
    record = (
        db.query(DerivedSleepData)
        .filter(DerivedSleepData.user_id == current_user.user_id)
        .order_by(DerivedSleepData.date.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No analysis records found.")

    record.user_score = feedback.user_score
    record.user_class = feedback.user_class
    db.commit()
    db.refresh(record)
    return record
