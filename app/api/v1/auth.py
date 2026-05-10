from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import uuid
from app.database import get_db
from app.db.supabase_client import exec
from app.schemas.auth import Token, UserCreate
from app.utils.security import create_access_token, verify_password, get_password_hash

router = APIRouter()

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db=Depends(get_db)):
    existing = exec(db.table("users").select("user_id").eq("email", user_in.email))
    if existing:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")

    exec(db.table("users").insert({
        "user_id": str(uuid.uuid4()),
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "age": user_in.age,
        "gender": user_in.gender,
        "weight_kg": user_in.weight_kg,
        "height_cm": user_in.height_cm,
    }))

    return {"access_token": create_access_token(subject=user_in.email), "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(db=Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    rows = exec(db.table("users").select("*").eq("email", form_data.username))
    user = rows[0] if rows else None
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return {"access_token": create_access_token(subject=user["email"]), "token_type": "bearer"}
