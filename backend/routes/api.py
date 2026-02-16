from fastapi import APIRouter, HTTPException, Depends
from backend.models.models import DesignCreate
from backend.services.generation_service import generation_service
from backend.database.connection import get_database
from backend.utils.auth_utils import get_current_user_uid
from datetime import datetime
from typing import List

router = APIRouter()

@router.post("/generate", response_model=dict)
async def generate_layout(
    design: DesignCreate, 
    uid: str = Depends(get_current_user_uid)
):
    """
    Generate a layout from a text prompt and save it.
    Requires Authentication.
    """
    # 1. Generate
    result = await generation_service.generate_layout(design.prompt)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # 2. Save to DB
    db = get_database()
    design_doc = {
        "user_id": uid,
        "prompt": design.prompt,
        "layout_data": result["layout"],
        "spec_data": result["spec"],
        "model_url": result.get("model_url"),
        "score": result.get("score", 0),
        "stats": result.get("stats", {}),
        "created_at": datetime.utcnow(),
        "design_id": result.get("design_id")
    }
    
    new_design = await db.designs.insert_one(design_doc)
    
    return {**result, "db_id": str(new_design.inserted_id)}

@router.get("/designs", response_model=List[dict])
async def get_all_designs(limit: int = 10):
    """
    Get generic designs for the Explore page. Limited to 10 latest.
    """
    db = get_database()
    cursor = db.designs.find().sort("created_at", -1).limit(limit)
    designs = await cursor.to_list(length=limit)
    
    # Convert ObjectId
    for d in designs:
        d["_id"] = str(d["_id"])
        
    return designs

@router.get("/my-designs", response_model=List[dict])
async def get_my_designs(uid: str = Depends(get_current_user_uid)):
    """
    Get designs for the current user.
    Returns UNIQUE prompts only (latest version), limited to 30.
    """
    db = get_database()
    
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$prompt",
            "doc": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"created_at": -1}},
        {"$limit": 30}
    ]
    
    cursor = db.designs.aggregate(pipeline)
    designs = await cursor.to_list(length=30)
    
    for d in designs:
        d["_id"] = str(d["_id"])
        
    return designs

@router.get("/health")
def health_check():
    return {"status": "ok"}
