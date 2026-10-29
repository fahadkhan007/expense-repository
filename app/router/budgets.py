from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.auth.dependencies import get_current_user
from app.database.connectdb import db
from app.models.budget import BudgetCreate, BudgetResponse, BudgetUpdate

router=APIRouter(prefix="/budgets", tags=["Budgets"])

@router.post("/",status_code=status.HTTP_201_CREATED, response_model=BudgetResponse)
async def create_budget(data: BudgetCreate, user: Annotated[str, Depends(get_current_user)]):
    try:
        budget_document={
            "_id": uuid4(),
            **data.model_dump(),
            "user_id": user["_id"]
        }

        await db.budgets.insert_one(budget_document)

        return BudgetResponse.model_validate(budget_document)
    except HTTPException:
        raise
        
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )



@router.get("/", status_code=status.HTTP_200_OK, response_model=list[BudgetResponse])
async def get_budgets(user: Annotated[str, Depends(get_current_user)]):
    try:
        budget_documents=await db.budgets.find({
            "user_id": user["_id"]
        }).to_list(length=None)

        if not budget_documents:
            return []

        return[
            BudgetResponse.model_validate(doc)
            for doc in budget_documents
        ]

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )
    
    except HTTPException:
        raise


    

@router.get("/{budget_id}", status_code=status.HTTP_200_OK, response_model=BudgetResponse)
async def get_budget(budget_id: UUID, user: Annotated[str, Depends(get_current_user)]):
    try:
        budget = await db.budgets.find_one({
            "_id": budget_id,
            "user_id": user["_id"]
        })

        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found!"
            )

        return BudgetResponse.model_validate(budget)
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )
    
    except HTTPException:
        raise



        
@router.patch("/{budget_id}", status_code=status.HTTP_200_OK, response_model=BudgetResponse)
async def update_budget(budget_id: UUID, data: BudgetUpdate, user: Annotated[str, Depends(get_current_user)]):
    try:
        budget = await db.budgets.find_one({
            "_id": budget_id,
            "user_id": user["_id"]
        })

        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found!"
            )

        update_data=data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided."
            )

        await db.budgets.update_one({
            "_id": budget_id,
            "user_id": user["_id"]
        },{
            "$set": update_data
        })

        updated_budget = await db.budgets.find_one({
            "_id": budget_id,
            "user_id": user["_id"]
        })

        return BudgetResponse.model_validate(updated_budget)
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error!"
        )
    
    except HTTPException:
        raise



@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: UUID, user: Annotated[str, Depends(get_current_user)]):
    try:
        result = await db.budgets.delete_one({
            "_id": budget_id,
            "user_id": user["_id"]
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found!"
            )

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error!"
        )
    
    except HTTPException:
        raise