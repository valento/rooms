from fastapi import APIRouter, HTTPException
from services.database import execute_query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/apps", tags=["apps"])

class AppInfo(BaseModel):
    id: int
    # content_id: int
    package_name: str
    component_name: str
    route_path: str
    config: dict = {}
    created_at: datetime
    # From content_blocks join
    title: str
    deck: Optional[str] = None
    content_slug: str

class AppRegistryItem(BaseModel):
    id: int
    package_name: str
    component_name: str
    route_path: str



@router.get("/registry", response_model=list[AppRegistryItem])
async def list_app_registry():
    """Flat list of registered apps for dropdowns."""
    result = execute_query("""
        SELECT id, package_name, component_name, route_path
        FROM company.apps_registry
        ORDER BY component_name
    """)
    return result if result else []


@router.get("/{identifier}")
async def get_app_info(identifier: str):
    """Get app registry info by slug or content_id."""
    if identifier.isdigit():
        sql = """
            SELECT ar.id, ar.package_name, ar.component_name, 
                   ar.route_path, ar.config, ar.created_at,
                   cb.title, cb.deck, cb.slug AS content_slug
            FROM company.apps_registry ar
            JOIN company.content_blocks cb ON cb.app_id = ar.id
            WHERE ar.id = %s
        """
        result = execute_query(sql, (int(identifier),))
    else:
        sql = """
            SELECT ar.id, ar.package_name, ar.component_name, 
                   ar.route_path, ar.config, ar.created_at,
                   cb.title, cb.deck, cb.slug AS content_slug
            FROM company.apps_registry ar
            JOIN company.content_blocks cb ON ar.id = cb.app_id
            WHERE cb.slug = %s
        """
        result = execute_query(sql, (identifier,))
    
    if not result:
        raise HTTPException(status_code=404, detail="App not found")
    
    return AppInfo(**result[0])


@router.get("/")
async def list_apps():
    """List all registered apps."""
    sql = """
        SELECT ar.id, ar.package_name, ar.component_name, 
               ar.route_path, ar.config, ar.created_at,
               cb.title, cb.deck, cb.slug AS content_slug
        FROM company.apps_registry ar
        LEFT JOIN company.content_blocks cb ON cb.app_id = ar.id
        ORDER BY cb.title
    """
    result = execute_query(sql)
    return {"app": [AppInfo(**row) for row in result], "count": len(result)}