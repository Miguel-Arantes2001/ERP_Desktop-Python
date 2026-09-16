from datetime import datetime, timedelta
from nt import access
from typing import Optional
from datetime import timezone
from jose import jwt, JWTError#type: ignore
from passlib.context import CryptContext # type: ignore
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer  
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]
from main import SECRET_KEY,ALGORITHM,ACCESS_TOKEN_EXPIRE_MINUTES,REFRESH_TOKEN_EXPIRE_DAYS,pwd_context,oauth2_scheme
import models
from database import get_db 


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str ) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict,expire_delta: Optional[timedelta] = None): 
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (expire_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)

    return access_token


def create_refresh_token(data: dict , expire_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expire_delta or timedelta(days = REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire , "type": "refresh"})
    refresh_token = jwt.encode(to_encode , SECRET_KEY , algorithm= ALGORITHM) 

    return refresh_token



def decode_refresh_token(token: str) -> dict:
    invalid_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid_exception

    if payload.get("type") != "refresh":
        raise invalid_exception

    return payload



PHOTO_TOKEN_EXPIRE_MINUTES = 5


def create_photo_token(product_id: int, store_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=PHOTO_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {
            "type": "photo_upload",
            "product_id": product_id,
            "store_id": store_id,
            "exp": expire,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_photo_token(token: str) -> dict:
    invalid_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Link expirado ou inválido. Gere um QR novo no computador.",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid_exception

    if payload.get("type") != "photo_upload":
        raise invalid_exception

    if payload.get("product_id") is None or payload.get("store_id") is None:
        raise invalid_exception

    return payload


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")

        if payload.get('type') != 'access':
            raise credentials_exception

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    if not user:
        raise credentials_exception

    return user
