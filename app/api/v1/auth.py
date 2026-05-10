from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.auth import Token, UserCreate, PasswordResetRequest
from app.utils.security import create_access_token, verify_password, get_password_hash, generate_random_password
from app.services.email_service import send_email, render_template
from app.config import settings
from app.api import deps

router = APIRouter()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db=Depends(get_db)):
    existing = exec(db.table("users").select("user_id").eq("email", user_in.email))
    if existing:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")

    confirmation_token = str(uuid.uuid4())

    exec(db.table("users").insert({
        "user_id": str(uuid.uuid4()),
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "age": user_in.age,
        "gender": user_in.gender,
        "weight_kg": user_in.weight_kg,
        "height_cm": user_in.height_cm,
        "email_confirmed": False,
        "email_confirmation_token": confirmation_token,
    }))

    # Send confirmation email (fire-and-forget)
    display_name = user_in.full_name or user_in.email.split("@")[0]
    confirm_link = f"{settings.frontend_url}/api/v1/auth/confirm-email?token={confirmation_token}"
    try:
        html = render_template("confirmation.html", NAME=display_name, EMAIL=user_in.email, LINK=confirm_link)
        send_email(user_in.email, "Confirm your SmartSleep email", html)
    except Exception:
        pass

    return {"access_token": create_access_token(subject=user_in.email), "token_type": "bearer"}


@router.get("/confirm-email", response_class=HTMLResponse)
def confirm_email(token: str, db=Depends(get_db)):
    rows = exec(db.table("users").select("*").eq("email_confirmation_token", token))
    if not rows:
        return HTMLResponse(_confirmation_page(success=False, msg="Invalid or expired confirmation link."), status_code=400)

    user = rows[0]
    exec(
        db.table("users")
        .update({"email_confirmed": True, "email_confirmation_token": None})
        .eq("user_id", user["user_id"])
    )

    # Send welcome email
    display_name = user.get("full_name") or user["email"].split("@")[0]
    try:
        html = render_template("welcome.html", NAME=display_name, EMAIL=user["email"])
        send_email(user["email"], "Welcome to SmartSleep! 🌙", html)
    except Exception:
        pass

    return HTMLResponse(_confirmation_page(success=True, msg=f"Email confirmed! Welcome to SmartSleep, {display_name}."))


@router.post("/login", response_model=Token)
def login(db=Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    rows = exec(db.table("users").select("*").eq("email", form_data.username))
    user = rows[0] if rows else None
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Send login notification email (fire-and-forget)
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    display_name = user.get("full_name") or user["email"].split("@")[0]
    try:
        html = render_template("login_notification.html", NAME=display_name, EMAIL=user["email"], LOGIN_TIME=now)
        send_email(user["email"], "New sign-in to your SmartSleep account", html)
    except Exception:
        pass

    return {"access_token": create_access_token(subject=user["email"]), "token_type": "bearer"}


@router.post("/reset-password")
def reset_password(body: PasswordResetRequest, db=Depends(get_db)):
    rows = exec(db.table("users").select("*").eq("email", body.email))
    if not rows:
        # Return 200 even if not found to avoid email enumeration
        return {"message": "If an account with that email exists, a reset email has been sent."}

    user = rows[0]
    new_password = generate_random_password()
    exec(
        db.table("users")
        .update({"password_hash": get_password_hash(new_password)})
        .eq("user_id", user["user_id"])
    )

    display_name = user.get("full_name") or user["email"].split("@")[0]
    try:
        html = render_template("password_reset.html", NAME=display_name, EMAIL=user["email"], NEW_PASSWORD=new_password)
        send_email(user["email"], "Your SmartSleep password has been reset", html)
    except Exception:
        pass

    return {"message": "If an account with that email exists, a reset email has been sent."}


@router.post("/resend-confirmation")
def resend_confirmation(
    db=Depends(get_db),
    current_user=Depends(deps.get_current_user),
):
    """Re-send the email confirmation link. No-op if already confirmed."""
    if getattr(current_user, "email_confirmed", False):
        return {"message": "Email is already confirmed."}

    new_token = str(uuid.uuid4())
    exec(
        db.table("users")
        .update({"email_confirmation_token": new_token})
        .eq("user_id", current_user.user_id)
    )

    display_name = getattr(current_user, "full_name", None) or current_user.email.split("@")[0]
    confirm_link = f"{settings.frontend_url}/api/v1/auth/confirm-email?token={new_token}"
    try:
        html = render_template("confirmation.html", NAME=display_name, EMAIL=current_user.email, LINK=confirm_link)
        send_email(current_user.email, "Confirm your SmartSleep email", html)
    except Exception:
        pass

    return {"message": "Confirmation email sent. Please check your inbox."}


def _confirmation_page(success: bool, msg: str) -> str:
    icon = "✅" if success else "❌"
    color = "#16A34A" if success else "#EF4444"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Email Confirmation — SmartSleep</title></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;">
<div style="max-width:480px;width:100%;margin:40px auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
<div style="background:linear-gradient(135deg,#1B3A6B,#243B55);padding:32px;text-align:center;">
<div style="font-size:28px;font-weight:800;color:#fff;">🌙 SmartSleep</div></div>
<div style="padding:40px;text-align:center;">
<div style="font-size:56px;margin-bottom:16px;">{icon}</div>
<h1 style="font-size:22px;color:#1E293B;margin:0 0 12px;">{msg}</h1>
<p style="font-size:15px;color:#64748B;line-height:1.6;margin:0;">You can close this tab and return to the SmartSleep app.</p>
</div></div></body></html>"""
