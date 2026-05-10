from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.api import deps
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.profile import UserResponse, UserUpdate
from app.services.email_service import send_email, render_template

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
    if not update_data:
        return vars(current_user)

    rows = exec(db.table("users").update(update_data).eq("user_id", current_user.user_id))

    # Send profile update alert email (fire-and-forget)
    display_name = getattr(current_user, "full_name", None) or current_user.email.split("@")[0]
    field_lines = "<br/>".join(
        f"&#8226; &nbsp;<strong>{k.replace('_', ' ').title()}</strong>"
        for k in update_data
    )
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    try:
        html = render_template(
            "profile_update.html",
            NAME=display_name,
            EMAIL=current_user.email,
            UPDATE_TIME=now,
            UPDATED_FIELDS=field_lines,
        )
        send_email(current_user.email, "Your SmartSleep profile was updated", html)
    except Exception:
        pass

    return rows[0] if rows else vars(current_user)
