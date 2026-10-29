from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.auth.dependencies import get_current_user
from app.database.connectdb import db
from app.models.category import CategoryCreate, CategoryResponse, CategoryUpdate

router=APIRouter(prefix="/categories",tags=["Categories"])



@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, user: Annotated[dict, Depends(get_current_user)]):
    try:

        category_document={
            "_id": uuid4(),
            **data.model_dump(),
            "user_id": user["_id"],
            "created_at": datetime.now(UTC)
        }

        await db.categories.insert_one(category_document)

        return CategoryResponse.model_validate(category_document)


    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )
        

@router.get("/", response_model=list[CategoryResponse])
async def get_categories(user: Annotated[dict, Depends(get_current_user)]):
    try:
        cursor = db.categories.find({
            "user_id": user["_id"]
        })
        
        categories = await cursor.to_list(length=None)
        
        return [CategoryResponse.model_validate(category) for category in categories]
    
    except HTTPException:
        raise

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: UUID, user: Annotated[dict, Depends(get_current_user)]):
    try:
        category = await db.categories.find_one({
            "_id": category_id,
            "user_id":user["_id"]
        })

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="category not found!"
            )
        
        return CategoryResponse.model_validate(category)
    
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )

    except HTTPException:
        raise
        
    
@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID, data: CategoryUpdate, user: Annotated[dict, Depends(get_current_user)]):
    
    try:
        category= await db.categories.find_one({
            "_id": category_id,
            "user_id":user["_id"]
        })

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="category not found!"
            )

        update_data=data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided."
            )
        
        await db.categories.update_one({
            "_id": category_id,
            "user_id": user["_id"]
        },{
            "$set": update_data
        })

        updated_category= await db.categories.find_one({
            "_id": category_id,
            "user_id": user["_id"]
        })

        return CategoryResponse.model_validate(updated_category)
    
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )

    except HTTPException:
        raise


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, user: Annotated[dict, Depends(get_current_user)]):
    try:
        result=await db.categories.delete_one({
            "_id": category_id,
            "user_id": user["_id"]
        })

        if result.deleted_count==0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="category not found!"
            )
        
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database error!"
        )

    except HTTPException:
        raise

        
