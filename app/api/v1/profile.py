from fastapi import APIRouter, Depends
from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.profile import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user=Depends(deps.get_current_user)):
    return vars(current_user)


@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    db=Depends(get_db),
    current_user=Depends(deps.get_current_user),
):
    update_data = {k: v for k, v in user_in.model_dump().items() if v is not None}
    if update_data:
        rows = exec(db.table("users").update(update_data).eq("user_id", current_user.user_id))
        if rows:
            return rows[0]
    return vars(current_user)
