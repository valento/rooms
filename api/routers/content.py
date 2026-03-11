import json as json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.content import ContentDetail, CreateContentRequest, BrickFeedResponse, UpdateContentRequest
from models.auth import CurrentUser
from services.database import execute_query
from services.auth import verify_token
from services.embeddings import regenerate_embedding
from services.permissions import Permissions
from services.utils import generate_unique_slug
from services.feed import build_center_feed
from routers.auth import get_current_user



router = APIRouter(prefix="/content", tags=["content"])


@router.get("/feed", response_model=BrickFeedResponse)
async def get_brick_feed(limit: int = 50):
    """
    Get brick-grouped content feed.
    
    - Center: 'read' content, ranked
    - Left/Right: 'app' content, promoted (priority=5) featured
    - Items grouped by widget_size
    """
    try:
        # Fetch ranked content
        sql = """
            WITH stats AS (
                SELECT 
                    MAX(view_count) as max_views,
                    MAX(social_score) as max_social
                FROM company.content_blocks
            )
            SELECT 
                c.id, c.title, c.deck, c.slug, c.category_id, c.body, c.metadata,
                c.created_at, c.updated_at, c.author_id,
                c.priority, c.view_count, c.social_score,
                c.widget_size, c.widget_vertical,
                cat.slug AS category_slug,
                u.full_name as author_name,
                u.username as author_username,
                -- Recency score
                CASE 
                    WHEN AGE(NOW(), c.created_at) < INTERVAL '7 days' THEN 1.0
                    WHEN AGE(NOW(), c.created_at) < INTERVAL '14 days' THEN 0.8
                    WHEN AGE(NOW(), c.created_at) < INTERVAL '30 days' THEN 0.5
                    ELSE 0.2
                END as recency_score,
                -- Composite ranking score
                (
                    (c.priority::float / 5.0) * 0.3 +
                    (CASE WHEN s.max_views > 0 THEN c.view_count::float / s.max_views ELSE 0 END) * 0.2 +
                    (CASE 
                        WHEN AGE(NOW(), c.created_at) < INTERVAL '7 days' THEN 1.0
                        WHEN AGE(NOW(), c.created_at) < INTERVAL '14 days' THEN 0.8
                        WHEN AGE(NOW(), c.created_at) < INTERVAL '30 days' THEN 0.5
                        ELSE 0.2
                    END) * 0.3 +
                    (CASE WHEN s.max_social > 0 THEN c.social_score::float / s.max_social ELSE 0 END) * 0.2
                ) as final_score
            FROM company.content_blocks c
            LEFT JOIN company.users u ON c.author_id = u.id
            LEFT JOIN company.categories cat ON c.category_id = cat.id
            CROSS JOIN stats s
            WHERE c.metadata->>'status' = 'published'
            ORDER BY final_score DESC
            LIMIT %s
        """
        
        results = execute_query(sql, (limit,))
        if not results:
            return BrickFeedResponse(center=[], left=[], right=[])

        content_items = [ContentDetail(**item) for item in results]

        reads = [c for c in content_items if c.content_type == 'read']
        apps  = [c for c in content_items if c.content_type == 'app']

        return BrickFeedResponse(
            center=build_center_feed(reads),
            left=[],    # apps — TBD
            right=[]
        )
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch feed: {str(e)}")

# Get a sequence of parent
@router.get("/{identifier}/parts")
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
@router.get("/{identifier}")
async def get_content_by_id(identifier: str):
    """Get content block by id or by slug, with series navigation."""
    
    if identifier.isdigit():
        where_clause = "cb.id = %s"
        param = int(identifier)
    else:
        where_clause = "cb.slug = %s"
        param = identifier
    
    sql = f"""
        WITH siblings AS (
            SELECT 
                id,
                LAG(slug) OVER (ORDER BY sequence_order) AS prev_slug,
                LEAD(slug) OVER (ORDER BY sequence_order) AS next_slug
            FROM company.content_blocks
            WHERE parent_id = (
                SELECT parent_id FROM company.content_blocks WHERE {where_clause.replace('cb.', '')}
            )
            AND parent_id IS NOT NULL
        )
        SELECT 
            cb.id, cb.title, cb.body, cb.deck, cb.slug, cb.metadata,
            cb.author_id, cb.view_count, cb.widget_size, cb.widget_vertical,
            cb.social_score, cb.priority, cb.price,
            cb.parent_id, cb.sequence_order,
            cb.category_id,
            cat.slug AS category_slug,
            cb.created_at, cb.updated_at,
            u.full_name AS author_name,
            u.username AS author_username,
            s.prev_slug,
            s.next_slug
        FROM company.content_blocks cb
        LEFT JOIN company.users u ON cb.author_id = u.id
        LEFT JOIN company.categories cat ON cb.category_id = cat.id
        LEFT JOIN siblings s ON cb.id = s.id
        WHERE {where_clause}
    """
    
    result = execute_query(sql, (param, param))
    
    if not result:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return ContentDetail(**result[0])

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
def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> int:

    """Extract user_id from JWT token."""
    token = credentials.credentials

    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user from database with role
    sql = "SELECT id, email, role FROM company.users WHERE id = %s"
    result = execute_query(sql, (int(user_id),))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    return (CurrentUser(**result[0]).id)

# Create content or sequel of content
@router.post("/", response_model=ContentDetail)
async def create_content(
        request: CreateContentRequest,
        current_user_id: int = Depends(get_current_user_id)
    ):

    """Create a new content block."""
    slug = request.slug if request.slug else generate_unique_slug(request.title)

    # Auto-calculate sequence_order if parent_id provided but no order
    sequence_order = request.sequence_order
    if request.parent_id and sequence_order is None:
        sql = """
            SELECT COALESCE(MAX(sequence_order), 0) + 1 as next_order 
            FROM company.content_blocks 
            WHERE parent_id = %s
        """
        result = execute_query(sql, (request.parent_id,))
        
        # Safe access with dict key
        if result and len(result) > 0:
            sequence_order = result[0]['next_order']  # Use column alias
        else:
            sequence_order = 1  # First child

    try:
        sql = """
            INSERT INTO company.content_blocks 
            (title, body, deck, metadata, slug, author_id, parent_id, sequence_order, widget_size, widget_vertical, category_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
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
                request.widget_vertical,
                request.category_id
            )
        )
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=500, detail="Failed to create content")
        
        content_id = result[0]['id']
        try:
            regenerate_embedding(content_id)
        except Exception as e:
            print(f"Warning: Embedding update failed: {e}")

        try:
            # Fetch full detail with category JOIN
            fetch_sql = """
                SELECT cb.*, 
                    cat.slug AS category_slug,
                    u.full_name AS author_name,
                    u.username AS author_username
                FROM company.content_blocks cb
                LEFT JOIN company.categories cat ON cb.category_id = cat.id
                LEFT JOIN company.users u ON cb.author_id = u.id
                WHERE cb.id = %s
            """
            full_result = execute_query(fetch_sql, (content_id,))
        except Exception as e:
            print("Warning: Error fetching the last created item")
        
        return ContentDetail(**full_result[0])
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create content: {str(e)}")
    

@router.post("/{content_id}/view")
async def track_view(
    content_id: int,
    current_user_id: int = Depends(get_current_user_id)
):
    """Track unique view from logged-in user."""
    try:
        # Just insert - trigger handles view_count update!
        sql = """
            INSERT INTO company.content_views (content_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT (content_id, user_id) DO NOTHING
        """
        execute_query(sql, (content_id, current_user_id))
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"View tracking error: {e}")
        return {"status": "error"}


@router.put("/{content_id}", response_model=ContentDetail)
async def update_content(
        content_id: int,
        request: UpdateContentRequest,
        current_user: CurrentUser = Depends(get_current_user)
    ):
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
        # Get Content and check Permissions: editors can edit any, authors only their own
        # Fetch content directly (don't call the GET route)
        sql = """
            SELECT id, author_id
            FROM company.content_blocks
            WHERE id = %s
        """
        result = execute_query(sql, (content_id,))
        # DEBUG logging
        print(f"DEBUG UPDATE: user_id={current_user.id}, user_role={current_user.role}")
        print(f"DEBUG UPDATE: content_author_id={result[0]['author_id']}")
        print(f"DEBUG UPDATE: can_edit={Permissions.can_edit_content(current_user.id, current_user.role, result[0]['author_id'])}")        
        
        if not Permissions.can_edit_content(
            user_id=current_user.id,
            user_role=current_user.role,
            content_author_id=result[0]['author_id']
        ):
            raise HTTPException(status_code=403, detail="Cannot edit this content")
        
        # Update content
        sql = """
            UPDATE company.content_blocks 
            SET 
                title = %s,
                deck = %s,
                slug = %s,
                category_id = %s,
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
                request.category_id,
                request.body,
                json.dumps(request.metadata),
                request.author_id,
                content_id
            )
        )
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
        
        # Join author info
        author_sql = """
            SELECT 
                c.*,
                cat.slug AS category_slug,
                u.full_name as author_name,
                u.username as author_username
            FROM company.content_blocks c
            LEFT JOIN company.categories cat ON c.category_id = cat.id
            LEFT JOIN company.users u ON c.author_id = u.id
            WHERE c.id = %s
        """
        
        final_result = execute_query(author_sql, (content_id,))
        
        try:
            regenerate_embedding(content_id)
        except Exception as e:
            print(f"Warning: Embedding update failed: {e}")
        
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


# ================= Helpers ==================================================

