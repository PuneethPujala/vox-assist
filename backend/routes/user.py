from fastapi import APIRouter, Depends, HTTPException, Body
from backend.models.models import UserCreate, UserBase
from backend.utils.auth_utils import verify_token, get_current_user_uid
from backend.database.connection import get_database
from typing import Dict, Any

router = APIRouter()

@router.post("/user/profile", response_model=dict)
async def update_profile(
    user_data: UserCreate, 
    uid: str = Depends(get_current_user_uid)
):
    """
    Update or create user profile in MongoDB.
    """
    db = get_database()
    
    if user_data.firebase_uid != uid:
        raise HTTPException(status_code=403, detail="UID mismatch")

    user_dict = user_data.model_dump()
    
    # Upsert user
    result = await db.users.update_one(
        {"firebase_uid": uid},
        {"$set": user_dict},
        upsert=True
    )
    
    return {"success": True, "message": "Profile updated"}

@router.get("/user/me")
async def get_my_profile(uid: str = Depends(get_current_user_uid)):
    db = get_database()
    user = await db.users.find_one({"firebase_uid": uid})
    if not user:
        return {"exists": False}
    
    # Convert ObjectId to str
    user["_id"] = str(user["_id"])
    return {"exists": True, "data": user}
