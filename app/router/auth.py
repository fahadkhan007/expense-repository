from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.database.connectdb import db
from app.models.auth import AuthResponse
from app.models.users import UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    try:  
        existing_user = await db.users.find_one({
            "email": user.email
        })
    
        if(existing_user):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user already exists!"
            )
            
        hashed_password = await run_in_threadpool(hash_password, user.password)
    
        user_document = {
            "_id": str(uuid4()),
            **user.model_dump(exclude={"password"}),
            "password_hash": hashed_password,
            "created_at": datetime.now(UTC)
        }
        
        await db.users.insert_one(user_document)
        
        access_token = await run_in_threadpool(create_access_token, user_document["_id"])
        
        user_data={
            **user_document,
            "id": user_document["_id"]
        }
        
        return AuthResponse(
            user=UserResponse.model_validate(user_data),
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user already exists!"
        )
        
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while registering the user."
        )
        
        
        
@router.post("/login", response_model= AuthResponse)
async def login_user(user: UserLogin):
    try:
        user_document = await db.users.find_one({
            "email": user.email
        })
        
        if not user_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found!"
            )
        
        isValidPassword = await run_in_threadpool(verify_password, user.password, user_document["password_hash"])
        
        if not isValidPassword:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials!"
            )
            
        access_token = await run_in_threadpool(create_access_token, user_document["_id"])
        
        user_data={
            **user_document,
            "id": user_document["_id"]
        }
        
        return AuthResponse(
            user=UserResponse.model_validate(user_data),
            access_token=access_token,
            token_type="bearer"
        )
        
    
    except HTTPException:
        raise
    
    
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occured during login."
        )
        
  

@router.post("/token")
async def issue_token(form: OAuth2PasswordRequestForm = Depends()):
    # Scalar sends the email in the standard OAuth2 "username" field.
    user_document = await db.users.find_one({"email": form.username})

    if not user_document:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    is_valid = await run_in_threadpool(
        verify_password,
        form.password,
        user_document["password_hash"],
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    access_token = await run_in_threadpool(
        create_access_token,
        user_document["_id"],
    )
    return {"access_token": access_token, "token_type": "bearer"} 


      
@router.get("/me", response_model=UserResponse)
async def get_user(user: UserResponse = Depends(get_current_user)):
    return user
        
        
        
                
        
    