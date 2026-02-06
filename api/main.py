from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from config import settings
from services.search import semantic_search
from services.database import get_db_connection

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.5

class SearchResponse(BaseModel):
    results: list
    count: int
    query: str

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "service": "FastAPI Search API"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/company_search", response_model=SearchResponse)
async def search_company_content(request: SearchRequest):
    """
    Semantic search across company content blocks.
    
    - **query**: Search query text
    - **limit**: Maximum number of results (default: 10)
    - **threshold**: Minimum similarity score 0-1 (default: 0.5)
    """
    try:
        results = semantic_search(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold
        )
        
        return SearchResponse(
            results=results,
            count=len(results),
            query=request.query
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR: {error_detail}")  # This will show in docker logs
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Company Search API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }