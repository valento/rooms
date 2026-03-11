from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.database import execute_query

router = APIRouter(prefix="/categories", tags=["categories"])

class Category(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None

@router.get("/", response_model=list[Category])
async def list_categories():
    sql = "SELECT id, name, slug, parent_id FROM company.categories ORDER BY name"
    result = execute_query(sql)
    return result if result else []