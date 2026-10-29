from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import PyMongoError  # type: ignore

from app.auth.dependencies import get_current_user
from app.database.connectdb import db
from app.models.transactions import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

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
            "user_id": user["_id"],
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


@router.patch("/{transaction_id}", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
async def update_transaction(
    transaction_id: UUID,
    data: TransactionUpdate,
    user: Annotated[dict, Depends(get_current_user)]):

    try:
        transaction = await db.transactions.find_one({
            "_id": transaction_id,
            "user_id": user["_id"],
        })

        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        if data.category_id is not None:
            category=await db.categories.find_one({
                "_id":data.category_id,
                "user_id":user["_id"]
            })

            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="category not found!"
                )
            
            # Use the new type if provided, otherwise fall back to the existing transaction type
            effective_type = data.type if data.type is not None else transaction["type"]
            if category["type"] is not None and category["type"] != effective_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="category type does not match transaction type!"
                )
        
        update_data=data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided.",
            )
        
        await db.transactions.update_one({
            "_id": transaction_id,
            "user_id": user["_id"],
        },{
            "$set": update_data
        })
        
        updated_transaction = await db.transactions.find_one({
            "_id": transaction_id,
            "user_id": user["_id"],
        })

        return TransactionResponse.model_validate(updated_transaction)

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error.",
        )
    
    except HTTPException:
        raise
    


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: UUID, user: Annotated[dict, Depends(get_current_user)]):
    try:
        result = await db.transactions.delete_one({
            "_id": transaction_id,
            "user_id": user["_id"],
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
    except HTTPException:
        raise

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error.",
        )

