import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.database.connectdb import db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme))->dict:
    creds_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id=payload.get("sub")
        
        if not isinstance(user_id, str) or not user_id:
            raise creds_exception
        
    except PyJWTError:
        raise creds_exception
    
    
    try:
        user_document = await db.users.find_one({"_id": user_id})
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal server error"
        )
    
    if user_document is None:
        raise creds_exception
    
    return {
        **user_document,
        "id": user_document["_id"]
    }
        
        