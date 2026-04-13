from pydantic import BaseModel, Field, computed_field
from datetime import datetime
from typing import Optional, List

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

class ContentLinks(BaseModel):
    self_link: str = Field(alias="self")
    parent: Optional[str] = None
    parts: Optional[str] = None
    prev: Optional[str] = None
    next: Optional[str] = None
    author: Optional[str] = None
    class Config:
        populate_by_name = True
        
class ContentDetail(BaseModel):
    id: int
    title: str
    deck: Optional[str] = None
    body: str
    slug: Optional[str] = None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    category_id: Optional[int] = None
    category_slug: Optional[str] = None
    
    # Author
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    
    # Widgets
    widget_size: Optional[str] = 'medium'
    widget_vertical: bool = False

    # App registry (for content_type: "play")
    app_id: Optional[int] = None
    package_name: Optional[str] = None
    component_name: Optional[str] = None
    route_path: Optional[str] = None
    app_config: Optional[dict] = None

    
    # Scoring/ranking
    view_count: int = 0
    social_score: float = 0
    priority: int = 3
    price: int = 0
    
    # Series/sequences
    parent_id: Optional[int] = None
    sequence_order: Optional[int] = None
    prev_slug: Optional[str] = None
    next_slug: Optional[str] = None
    
    # Computed fields
    @computed_field
    @property
    def content_type(self) -> str:
        return self.metadata.get('content_type', 'read')
    
    @computed_field
    @property
    def category(self) -> str:
        return self.metadata.get('read_category') or self.metadata.get('app_type', 'unknown')
    
    @computed_field
    @property
    def tags(self) -> list[str]:
        return self.metadata.get('tags', [])
    
    @computed_field
    @property
    def _links(self) -> dict:
        links = {"self": f"/content/{self.slug or self.id}"}
        
        if self.parent_id is None:
            links["parts"] = f"/content/{self.slug or self.id}/parts"
        else:
            links["parent"] = f"/content/{self.parent_id}"
        
        if self.prev_slug:
            links["prev"] = f"/content/{self.prev_slug}"
        
        if self.next_slug:
            links["next"] = f"/content/{self.next_slug}"
        
        if self.author_id:
            links["author"] = f"/users/{self.author_id}"
        
        return links
    
class CreateContentRequest(BaseModel):
    title: str
    deck: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] = None
    body: str
    metadata: dict
    widget_size: Optional[str] = 'medium'
    widget_vertical: Optional[bool] = False
    parent_id: Optional[int] = None
    sequence_order: Optional[int] = None

class UpdateContentRequest(BaseModel):
    title: str
    deck: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] = None
    body: str
    metadata: dict
    author_id: Optional[int] = None

class BrickItem(BaseModel):
    brick_type: str  # 'xlarge', 'large', 'medium', 'small', 'promoted'
    items: List[ContentDetail]

class BrickFeedResponse(BaseModel):
    center: List[BrickItem]
    left: List[BrickItem]
    right: List[BrickItem]