from backend.models.models import DesignCreate, DesignBase
from bson import ObjectId
from backend.services.generation_service import generation_service
from backend.database.connection import get_database
from backend.utils.auth_utils import get_current_user_uid
from backend.utils.rate_limit import limiter
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request

router = APIRouter()

async def process_generation_job(job_id: str, prompt: str, uid: str):
    db = get_database()
    try:
        result = await generation_service.generate_layout(prompt)
        if not result["success"]:
            await db.jobs.update_one(
                {"_id": ObjectId(job_id)}, 
                {"$set": {"status": "failed", "error": result.get("error", "Unknown ML Error")}}
            )
            return
            
        design_doc = {
            "user_id": uid,
            "prompt": prompt,
            "layout_data": result["layout"],
            "spec_data": result["spec"],
            "model_url": result.get("model_url"),
            "stl_url": result.get("stl_url"),
            "score": result.get("score", 0),
            "stats": result.get("stats", {}),
            "created_at": datetime.utcnow(),
            "design_id": result.get("design_id"),
            "name": "Untitled Project",
            "description": "",
            "tags": [],
            "is_deleted": False,
            "parent_id": None
        }
        
        new_design = await db.designs.insert_one(design_doc)
        
        await db.jobs.update_one(
            {"_id": ObjectId(job_id)}, 
            {"$set": {
                "status": "completed", 
                "result": {**result, "db_id": str(new_design.inserted_id)}
            }}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "failed", "error": str(e)}})


@router.post("/generate", response_model=dict)
@limiter.limit("5/minute")
async def generate_layout(
    request: Request,
    design: DesignCreate, 
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_user_uid)
):
    """
    Queue a layout generation job.
    """
    db = get_database()

    job_doc = {
        "user_id": uid,
        "prompt": design.prompt,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    job = await db.jobs.insert_one(job_doc)
    job_id = str(job.inserted_id)

    background_tasks.add_task(process_generation_job, job_id, design.prompt, uid)
    
    return {"success": True, "job_id": job_id}

@router.get("/jobs/{job_id}", response_model=dict)
async def get_job_status(job_id: str, uid: str = Depends(get_current_user_uid)):
    db = get_database()
    job = await db.jobs.find_one({"_id": ObjectId(job_id), "user_id": uid})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job["_id"] = str(job["_id"])
    return job

@router.get("/designs", response_model=List[dict])
async def get_all_designs(limit: int = 10):
    """
    Get generic designs for the Explore page. Limited to 10 latest.
    """
    db = get_database()
    cursor = db.designs.find({"is_deleted": {"$ne": True}}).sort("created_at", -1).limit(limit)
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
        {"$match": {"user_id": uid, "is_deleted": {"$ne": True}}},
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

from pydantic import BaseModel
from typing import Optional

class DesignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_deleted: Optional[bool] = None

@router.put("/designs/{design_id}", response_model=dict)
async def update_design(
    design_id: str,
    update_data: DesignUpdate,
    uid: str = Depends(get_current_user_uid)
):
    db = get_database()
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if not update_dict:
        return {"success": True, "message": "No fields to update"}
        
    result = await db.designs.update_one(
        {"_id": ObjectId(design_id), "user_id": uid},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Design not found or unauthorized")
        
    return {"success": True, "message": "Design updated"}

@router.post("/designs/{design_id}/duplicate", response_model=dict)
async def duplicate_design(
    design_id: str,
    uid: str = Depends(get_current_user_uid)
):
    db = get_database()
    original = await db.designs.find_one({"_id": ObjectId(design_id), "user_id": uid})
    
    if not original:
        raise HTTPException(status_code=404, detail="Design not found or unauthorized")
        
    new_design = dict(original)
    del new_design["_id"]
    new_design["name"] = f"{original.get('name', 'Untitled Project')} (Copy)"
    new_design["created_at"] = datetime.utcnow()
    new_design["parent_id"] = str(original["_id"])
    
    res = await db.designs.insert_one(new_design)
    return {"success": True, "new_id": str(res.inserted_id)}

@router.get("/health")
def health_check():
    return {"status": "ok"}
