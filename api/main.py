from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, computed_field
from typing import Optional
from config import settings
from services.search import semantic_search
from services.database import get_db_connection
from datetime import datetime

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
    threshold: Optional[float] = 0.3

class SearchResultItem(BaseModel):
    id: int
    title: str
    body: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
    semantic_similarity: float
    priority: int
    final_score: float

    @computed_field
    @property
    def snippet(self) -> str:
        return self.body[:150] + "..." if len(self.body) > 150 else self.body
    
    @computed_field
    @property
    def url(self) -> str:
        # Get content_type from metadata for URL generation
        content_type = self.metadata.get('content_type', 'read')
        category = self.metadata.get('read_category') or self.metadata.get('app_type', 'content')
        return f"/{content_type}/{category}/{self.id}"
    
    @computed_field
    @property
    def content_type(self) -> str:
        return self.metadata.get('content_type', 'unknown')
    
class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    count: int
    query: str
    
class Config:
    fields = {"body": {"execute": True}}

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

        # if results is None:
        #     results = []
        
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