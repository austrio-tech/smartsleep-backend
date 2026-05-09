from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.database import get_db
from app.models.user import User
from app.models.raw_sleep_data import RawSleepData
from app.models.derived_sleep_data import DerivedSleepData
from app.schemas.sleep_data import RawSleepDataCreate, RawSleepDataResponse
from app.schemas.analysis import DerivedSleepDataResponse
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
    
    This endpoint accepts pre-sleep and post-sleep metrics. 
    Upon ingestion, it automatically triggers the analysis pipeline to calculate 
    derived metrics and a sleep quality score.
    """
    db_raw = RawSleepData(
        **data_in.model_dump(),
        user_id=current_user.user_id
    )
    db.add(db_raw)
    db.commit()
    db.refresh(db_raw)
    
    # Trigger analysis
    process_daily_sleep(db, db_raw.raw_id, current_user)
    
    return db_raw

@router.get("/history", response_model=List[DerivedSleepDataResponse])
def get_sleep_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retrieve historical sleep analysis results for the current user.
    
    Returns a list of analysis records including scores, derived metrics, and dates.
    """
    history = db.query(DerivedSleepData).filter(
        DerivedSleepData.user_id == current_user.user_id
    ).order_by(DerivedSleepData.date.desc()).all()
    return history
