from fastapi import APIRouter, HTTPException
from models.content import ContentDetail
from services.database import execute_query
from schemas.content_schemas import get_schemas

router = APIRouter(prefix="/content", tags=["content"])

@router.get("/{content_id}", response_model=ContentDetail)
async def get_content(content_id: int):
    """
    Get a single content block by ID.
    
    - **content_id**: The ID of the content to retrieve
    """
    try:
        sql = """
            SELECT 
                id,
                title,
                body,
                metadata,
                created_at,
                updated_at
            FROM company.content_blocks
            WHERE id = %s
        """
        
        result = execute_query(sql, (content_id,))
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
        
        content = result[0]
        # content_type = content['metadata'.get('content_type', 'read')]
        data_schema, ui_schema = get_schemas(content_type='read')

        content['data_schema'] = data_schema
        content['ui_schema'] = ui_schema
        return ContentDetail(**result[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch content: {str(e)}")

@router.get("/", response_model=list[ContentDetail])
async def list_content(
    content_type: str = None,
    category: str = None,
    limit: int = 10
):
    """
    List content blocks with optional filtering.
    
    - **content_type**: Filter by content_type (app/read)
    - **category**: Filter by category
    - **limit**: Maximum number of results
    """
    try:
        conditions = []
        params = []
        
        if content_type:
            conditions.append("metadata->>'content_type' = %s")
            params.append(content_type)
        
        if category:
            conditions.append("(metadata->>'read_category' = %s OR metadata->>'app_type' = %s)")
            params.extend([category, category])
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        sql = f"""
            SELECT 
                id,
                title,
                body,
                metadata,
                created_at,
                updated_at
            FROM company.content_blocks
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        params.append(limit)
        results = execute_query(sql, tuple(params))
        
        return results if results else []
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list content: {str(e)}")