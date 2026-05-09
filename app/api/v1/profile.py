from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.database import get_db
from app.models.user import User
from app.schemas.profile import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(deps.get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if user_in.age is not None:
        current_user.age = user_in.age
    if user_in.gender is not None:
        current_user.gender = user_in.gender
    if user_in.weight_kg is not None:
        current_user.weight_kg = user_in.weight_kg
    if user_in.height_cm is not None:
        current_user.height_cm = user_in.height_cm
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
