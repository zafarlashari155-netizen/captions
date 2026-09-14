import datetime
from fastapi import Depends, HTTPException, Header
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.db_models import User

ALGORITHM = "HS256"


def verify_google_token(credential: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google Sign-In is not configured")
    try:
        payload = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid Google credential") from e
    if not payload.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google email is not verified")
    return {"google_sub": payload["sub"], "email": payload["email"], "name": payload.get("name", "")}


def create_session_token(user: User) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.jwt_expires_minutes)
    return jwt.encode({"user_id": user.id, "exp": expire}, settings.jwt_secret, algorithm=ALGORITHM)


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in required")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload.get("user_id"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Session expired, please sign in again")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user
