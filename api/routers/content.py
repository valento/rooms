import json as json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.content import ContentDetail
from services.database import execute_query
from services.utils import generate_unique_slug
from services.auth import verify_token
from pydantic import BaseModel
from typing import Optional

class CreateContentRequest(BaseModel):
    title: str
    deck: Optional[str] = None
    slug: Optional[str] = None
    body: str
    metadata: dict
    widget_size: Optional[str] = 'medium'
    widget_vertical: Optional[bool] = False
    parent_id: Optional[int] = None
    sequence_order: Optional[int] = None

router = APIRouter(prefix="/content", tags=["content"])

# Get a sequence of parent
@router.get("/{content_id}/parts")
async def get_series_parts(identifier: str):
    """Get all parts of a content series."""
    # Get parent ID
    if identifier.isdigit():
        parent_id = int(identifier)
    else:
        sql = "SELECT id FROM company.content_blocks WHERE slug = %s"
        result = execute_query(sql, (identifier,))
        if not result:
            raise HTTPException(status_code=404, detail="Series not found")
        parent_id = result[0]['id']
    
    sql = """
        SELECT id, title, deck, slug, sequence_order, created_at
        FROM company.content_blocks 
        WHERE parent_id = %s 
        ORDER BY sequence_order
    """
    parts = execute_query(sql, (parent_id,))
    
    return {"parent_id": parent_id, "parts": parts, "count": len(parts)}

# Get by content_id
@router.get("/{content_id}", response_model=ContentDetail)
async def get_content(content_id: int):
    """
    Get a single content block by ID.
    
    - **content_id**: The ID of the content to retrieve
    """
    try:
        sql = """
            SELECT 
                c.id,
                c.title,
                c.deck,
                c.body,
                u.full_name as author_name,
                c.created_at,
                c.updated_at,
                c.slug,
                c.metadata,
                c.author_id,
                u.username as author_username
            FROM company.content_blocks c
            LEFT JOIN company.users u ON c.author_id = u.id
            WHERE c.id = %s
        """
        
        result = execute_query(sql, (content_id,))
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
        
        content = result[0]
        # content_type = content['metadata'.get('content_type', 'read')]
        # data_schema, ui_schema = get_schemas(content_type='read')

        # content['data_schema'] = data_schema
        # content['ui_schema'] = ui_schema
        return ContentDetail(**result[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch content: {str(e)}")

# Get all content
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


security = HTTPBearer()
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Extract user_id from JWT token."""
    token = credentials.credentials
    print(f"=== Token received: {token}")  # Add this
    payload = verify_token(token)
    print(f"=== User received: {payload}")  # Add this
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    print(f"DEBUG: User ID from token: {user_id}")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return int(user_id)

# Create content or sequel of content
@router.post("/", response_model=ContentDetail)
async def create_content(request: CreateContentRequest,
                         current_user_id: int = Depends(get_current_user_id)
                        ):
    """Create a new content block."""
    slug = request.slug if request.slug else generate_unique_slug(request.title)

    # Auto-calculate sequence_order if parent_id provided but no order
    sequence_order = request.sequence_order
    if request.parent_id and sequence_order is None:
        sql = "SELECT COALESCE(MAX(sequence_order), 0) + 1 FROM company.content_blocks WHERE parent_id = %s"
        result = execute_query(sql, (request.parent_id,))
        sequence_order = result[0][0]

    try:
        sql = """
            INSERT INTO company.content_blocks 
            (title, body, deck, metadata, slug, author_id, parent_id, sequence_order, widget_size, widget_vertical)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, body, deck, slug, metadata, author_id, 
                    parent_id, sequence_order, created_at, updated_at
        """
        
        result = execute_query(
            sql, 
            (   
                request.title,
                request.body,
                request.deck,
                json.dumps(request.metadata),
                slug,
                current_user_id,
                request.parent_id,
                sequence_order,
                request.widget_size,
                request.widget_vertical
            )
        )
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=500, detail="Failed to create content")
        
        # TODO: Generate embedding for new content
        
        return ContentDetail(**result[0])
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create content: {str(e)}")
    
# Create content
class UpdateContentRequest(BaseModel):
    title: str
    deck: Optional[str] = None
    slug: Optional[str] = None
    body: str
    metadata: dict
    author_id: Optional[int] = None

@router.put("/{content_id}", response_model=ContentDetail)
async def update_content(content_id: int, request: UpdateContentRequest):
    """
    Update an existing content block.
    
    - **content_id**: The ID of the content to update
    - **title**: Updated title
    - **deck**: Updated subtitle/deck
    - **slug**: Updated URL slug
    - **body**: Updated body content
    - **metadata**: Updated metadata
    - **author_id**: Author ID (optional)
    """
    slug = generate_unique_slug(request.title)
    try:
        # Update content
        sql = """
            UPDATE company.content_blocks 
            SET 
                title = %s,
                deck = %s,
                slug = %s,
                body = %s,
                metadata = %s,
                author_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, title, deck, slug, body, metadata, author_id, created_at, updated_at
        """
        
        result = execute_query(
            sql,
            (
                request.title,
                request.deck,
                slug,
                request.body,
                json.dumps(request.metadata),
                request.author_id,
                content_id
            )
        )
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
        
        content = result[0]
        
        # Join author info
        author_sql = """
            SELECT 
                c.*,
                u.full_name as author_name,
                u.username as author_username
            FROM company.content_blocks c
            LEFT JOIN company.users u ON c.author_id = u.id
            WHERE c.id = %s
        """
        
        final_result = execute_query(author_sql, (content_id,))
        
        # TODO: Regenerate embedding for updated content
        
        return ContentDetail(**final_result[0])
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}")
    
# Get by slug
@router.get("/read/{identifier}")
async def get_content(identifier: str):
    """Get content by ID or slug."""
    print(f"=== get_content called with: {identifier}")
    if identifier.isdigit():
        sql = """
            SELECT id, title, body, deck, slug, metadata, author_id, 
                   view_count, social_score, priority, created_at, updated_at
            FROM company.content_blocks 
            WHERE id = %s
        """
        result = execute_query(sql, (int(identifier),))
    else:
        sql = """
            SELECT id, title, body, deck, slug, metadata, author_id,
                   view_count, social_score, priority, created_at, updated_at
            FROM company.content_blocks 
            WHERE slug = %s
        """
        result = execute_query(sql, (identifier,))
    
    if not result:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return result[0]