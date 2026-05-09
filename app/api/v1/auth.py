from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import uuid
from app.database import get_db
from app.schemas.auth import Token, UserCreate
from app.utils.security import create_access_token, verify_password, get_password_hash

router = APIRouter()

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db=Depends(get_db)):
    existing = db.table("users").select("user_id").eq("email", user_in.email).maybe_single().execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system")

    db.table("users").insert({
        "user_id": str(uuid.uuid4()),
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "age": user_in.age,
        "gender": user_in.gender,
        "weight_kg": user_in.weight_kg,
        "height_cm": user_in.height_cm,
    }).execute()

    return {"access_token": create_access_token(subject=user_in.email), "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(db=Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    result = db.table("users").select("*").eq("email", form_data.username).maybe_single().execute()
    user = result.data
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return {"access_token": create_access_token(subject=user["email"]), "token_type": "bearer"}
