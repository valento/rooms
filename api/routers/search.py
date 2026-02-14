from fastapi import APIRouter, HTTPException
from models.content import SearchRequest, SearchResponse
from services.search import semantic_search

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
async def search_content(request: SearchRequest):
    """
    Semantic search across company content blocks.
    
    - **query**: Search query text
    - **limit**: Maximum number of results (default: 10)
    - **threshold**: Minimum similarity score 0-1 (default: 0.3)
    """
    try:
        results = semantic_search(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold
        )
        
        # Handle None or empty results
        if results is None:
            results = []
        
        return SearchResponse(
            results=results,
            count=len(results),
            query=request.query
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")