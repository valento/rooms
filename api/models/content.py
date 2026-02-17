from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional

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

class ContentDetail(BaseModel):
    id: int
    title: str
    deck: Optional[str] = None
    body: str
    author_name: Optional[str] = None  # From JOIN
    created_at: datetime
    updated_at: datetime
    metadata: dict
    slug: Optional[str] = None
    author_id: Optional[int] = None
    author_username: Optional[str] = None
    
    # data_schema: Optional[dict] = None
    # ui_schema: Optional[dict] = None
    
    @computed_field
    @property
    def content_type(self) -> str:
        return self.metadata.get('content_type', 'unknown')
    
    @computed_field
    @property
    def category(self) -> str:
        return self.metadata.get('read_category') or self.metadata.get('app_type', 'unknown')
    
    @computed_field
    @property
    def tags(self) -> list[str]:
        return self.metadata.get('tags', [])