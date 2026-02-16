from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

class DesignBase(BaseModel):
    user_id: str
    prompt: str
    layout_data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    model_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class DesignCreate(BaseModel):
    prompt: str

class DesignResponse(DesignBase):
    id: str = Field(alias="_id")

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserCreate(UserBase):
    firebase_uid: str
