from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_google_token, create_session_token
from app.database import get_db
from app.models.db_models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str  # the ID token Google's Sign-In button returns


class SessionResponse(BaseModel):
    access_token: str
    email: str
    name: str
    is_subscribed: bool


@router.post("/google", response_model=SessionResponse)
def login_with_google(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    google_user = verify_google_token(body.credential)

    user = db.query(User).filter(User.google_sub == google_user["google_sub"]).first()
    if not user:
        user = User(
            google_sub=google_user["google_sub"],
            email=google_user["email"],
            name=google_user["name"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_session_token(user)
    return SessionResponse(
        access_token=token,
        email=user.email,
        name=user.name or "",
        is_subscribed=user.is_subscribed,
    )
