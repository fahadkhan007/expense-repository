from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import PyMongoError  # type: ignore

from app.auth.dependencies import get_current_user
from app.database.connectdb import db
from app.models.transactions import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransactionCreate, user: Annotated[dict, Depends(get_current_user)]):
    try:
        category = await db.categories.find_one({
            "_id": data.category_id,
            "user_id": user["_id"]
        })
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="category not found!"
            )
        
        if category.get("type") is not None and category["type"]!=data.type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="category type does not match transaction type!"
            )
            
        transaction_document = {
            "_id": uuid4(),
            **data.model_dump(),
            "user_id": user["_id"],
            "created_at": datetime.now(UTC)
        }
        
        await db.transactions.insert_one(transaction_document)
        
        return TransactionResponse.model_validate(transaction_document)
    except HTTPException:
        raise
    
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )
    


@router.get("/", response_model=list[TransactionResponse])
async def get_transactions(user: Annotated[dict, Depends(get_current_user)], page: int = Query(default=1, ge=1)):  # noqa: B008
    page_size = 20
    skip = (page-1)*page_size
    try:
        cursor =(
                db.transactions.find({
                "user_id": user["_id"]})
                .sort("created_at", -1)
                .skip(skip)
                .limit(page_size)
            ) 
        
        transactions=await cursor.to_list(length=page_size)
        
        return [TransactionResponse.model_validate(transaction) for transaction in transactions]
    
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )
        
        
        
@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
):
    try:
        transaction = await db.transactions.find_one({
            "_id": transaction_id,
            "user_id": user["id"],
        })

        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        return TransactionResponse.model_validate(transaction)

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error.",
        )

        
        
        
        
