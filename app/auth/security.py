from datetime import UTC, datetime, timedelta

import jwt
from app.config.settings import settings
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str)->str:
    return password_hash.hash(password)


def verify_password(password:str, hashed_password:str)->bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str)->str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "exp": expire
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return token
    
    






