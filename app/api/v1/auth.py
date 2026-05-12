# ─────────────────────────────────────────────────────────────────────────────
# auth.py  –  Authentication API endpoints (signup, login, email confirmation,
#              password reset, resend confirmation).
#
# All routes in this file are prefixed with /api/v1/auth (set in main.py).
# Unprotected routes (no login required): signup, confirm-email, login, reset-password
# Protected routes (JWT required):        resend-confirmation
# ─────────────────────────────────────────────────────────────────────────────

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

# APIRouter groups all routes in this file under the /api/v1/auth prefix.
router = APIRouter()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db=Depends(get_db)):
    """Register a new user account.

    Steps performed:
    1. Check that the email isn't already registered.
    2. Generate a unique email confirmation token.
    3. Store the hashed password and user details in the database.
    4. Send a confirmation email (fire-and-forget — failure is silent).
    5. Return a JWT access token so the user is immediately logged in.

    Args:
        user_in: Registration form data (email, password, name, demographics).
        db:      Supabase database client (injected by FastAPI).

    Returns:
        Token: {"access_token": "...", "token_type": "bearer"}

    Raises:
        HTTPException 400: If the email is already in use.
    """
    # Check if the email is already taken
    existing = exec(db.table("users").select("user_id").eq("email", user_in.email))
    if existing:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")

    # uuid4() generates a random, universally unique ID string like:
    # "550e8400-e29b-41d4-a716-446655440000"
    confirmation_token = str(uuid.uuid4())

    # Insert the new user row. Note: we store the HASHED password, never plain text.
    exec(db.table("users").insert({
        "user_id": str(uuid.uuid4()),
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "age": user_in.age,
        "gender": user_in.gender,
        "weight_kg": user_in.weight_kg,
        "height_cm": user_in.height_cm,
        "email_confirmed": False,               # User hasn't confirmed email yet
        "email_confirmation_token": confirmation_token,
    }))

    # Build the confirmation link and send the email.
    # "Fire-and-forget" means we try it but don't fail the signup if email sending fails.
    display_name = user_in.full_name or user_in.email.split("@")[0]
    confirm_link = f"{settings.frontend_url}/api/v1/auth/confirm-email?token={confirmation_token}"
    try:
        html = render_template("confirmation.html", NAME=display_name, EMAIL=user_in.email, LINK=confirm_link)
        send_email(user_in.email, "Confirm your SmartSleep email", html)
    except Exception:
        pass  # Email failure should NOT block signup

    # Return a JWT so the user is immediately usable (even before email confirmation).
    return {"access_token": create_access_token(subject=user_in.email), "token_type": "bearer"}


@router.get("/confirm-email", response_class=HTMLResponse)
def confirm_email(token: str, db=Depends(get_db)):
    """Confirm a user's email address via the link sent to their inbox.

    The user clicks the link in their confirmation email. The link contains
    a one-time token. This route verifies the token, marks the email as
    confirmed, and shows an HTML confirmation page.

    Args:
        token: The UUID token from the confirmation link query parameter.
        db:    Supabase database client (injected by FastAPI).

    Returns:
        HTMLResponse: A styled success or failure page shown in the browser.
    """
    # Look up the user who has this confirmation token
    rows = exec(db.table("users").select("*").eq("email_confirmation_token", token))
    if not rows:
        # Invalid/expired token — show error page
        return HTMLResponse(_confirmation_page(success=False, msg="Invalid or expired confirmation link."), status_code=400)

    user = rows[0]
    # Mark the email as confirmed and clear the one-time token
    exec(
        db.table("users")
        .update({"email_confirmed": True, "email_confirmation_token": None})
        .eq("user_id", user["user_id"])
    )

    # Send a welcome email now that they've confirmed
    display_name = user.get("full_name") or user["email"].split("@")[0]
    try:
        html = render_template("welcome.html", NAME=display_name, EMAIL=user["email"])
        send_email(user["email"], "Welcome to SmartSleep! 🌙", html)
    except Exception:
        pass

    return HTMLResponse(_confirmation_page(success=True, msg=f"Email confirmed! Welcome to SmartSleep, {display_name}."))


@router.post("/login", response_model=Token)
def login(db=Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate a user and return a JWT access token.

    OAuth2PasswordRequestForm expects the request body to be form-encoded
    (not JSON) with fields `username` and `password`. Our "username" is
    actually an email address.

    Args:
        db:        Supabase database client (injected by FastAPI).
        form_data: Login credentials from the HTML form body.

    Returns:
        Token: {"access_token": "...", "token_type": "bearer"}

    Raises:
        HTTPException 401: If the email doesn't exist or password is wrong.
    """
    # Find the user by email (form_data.username holds the email)
    rows = exec(db.table("users").select("*").eq("email", form_data.username))
    user = rows[0] if rows else None

    # Verify the user exists AND the password matches the stored hash
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Send a login notification email (fire-and-forget)
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    display_name = user.get("full_name") or user["email"].split("@")[0]
    try:
        html = render_template("login_notification.html", NAME=display_name, EMAIL=user["email"], LOGIN_TIME=now)
        send_email(user["email"], "New sign-in to your SmartSleep account", html)
    except Exception:
        pass

    # Issue a new JWT for this session
    return {"access_token": create_access_token(subject=user["email"]), "token_type": "bearer"}


@router.post("/reset-password")
def reset_password(body: PasswordResetRequest, db=Depends(get_db)):
    """Reset a user's password and email them a new random one.

    Security note: We return the same success message whether the email
    exists or not. This prevents "email enumeration" — an attack where
    someone tests many emails to find which ones have accounts.

    Args:
        body: The request body containing just an email address.
        db:   Supabase database client (injected by FastAPI).

    Returns:
        dict: A generic success message (same message whether email found or not).
    """
    rows = exec(db.table("users").select("*").eq("email", body.email))
    if not rows:
        # Return 200 even if not found to avoid email enumeration
        return {"message": "If an account with that email exists, a reset email has been sent."}

    user = rows[0]
    # Generate a new random password and store its hash
    new_password = generate_random_password()
    exec(
        db.table("users")
        .update({"password_hash": get_password_hash(new_password)})
        .eq("user_id", user["user_id"])
    )

    # Email the user their new temporary password
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
    """Re-send the email confirmation link to the logged-in user.

    This is a no-op if the user's email is already confirmed.
    Generates a new one-time token to replace any previous one.

    Args:
        db:           Supabase database client (injected by FastAPI).
        current_user: The authenticated user (from JWT, injected by FastAPI).

    Returns:
        dict: A message confirming the email was sent (or already confirmed).
    """
    # If already confirmed, nothing to do
    if getattr(current_user, "email_confirmed", False):
        return {"message": "Email is already confirmed."}

    # Generate a fresh confirmation token
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
    """Build a simple HTML page to show the user after clicking a confirmation link.

    Args:
        success: True to show a green success icon, False for a red error icon.
        msg:     The main message displayed on the page.

    Returns:
        An HTML string that the browser will render.
    """
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
