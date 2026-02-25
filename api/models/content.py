from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional

class SearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = None  # From auth token in production
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
    
    # @computed_field
    # @property
    # def url(self) -> str:
    #     content_type = self.metadata.get('content_type', 'read')
    #     category = self.metadata.get('read_category') or self.metadata.get('app_type', 'content')
    #     return f"/read/{self.id}"
    
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
    slug: Optional[str] = None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    
    # Author
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    
    # Widgets
    widget_size: Optional[str] = 'medium'
    widget_vertical: bool = False
    
    # Scoring/ranking
    view_count: int = 0
    social_score: float = 0
    priority: int = 3
    price: int = 0
    
    # Series/sequences
    parent_id: Optional[int] = None
    sequence_order: Optional[int] = None
    
    # Computed fields
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