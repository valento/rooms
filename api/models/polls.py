from pydantic import BaseModel, computed_field, model_validator
from datetime import datetime
from typing import Optional

class PollOptionResult(BaseModel):
    id: int
    text: str
    sequence_order: int
    vote_count: int = 0
    _percentage: int

    @computed_field
    @property
    def percentage(self) -> float:
        # Calculated after we know total — handled in PollDetail
        return self._percentage

class PollDetail(BaseModel):
    id: int
    content_id: Optional[int] = None
    question: str
    poll_type: str
    status: str
    closes_at: Optional[datetime] = None
    created_at: datetime
    options: list[PollOptionResult] = []
    total_votes: int = 0
    user_voted: bool = False                # did the requesting user already vote?
    user_option_id: Optional[int] = None    # which option they picked
    category_id: Optional[int] = None
    category_slug: Optional[str] = None

    @computed_field
    @property
    def is_closed(self) -> bool:
        from datetime import timezone
        if self.status == 'closed':
            return True
        if self.closes_at and datetime.now(timezone.utc) > self.closes_at:
            return True
        return False
    
    @model_validator(mode='after')
    def calculate_percentages(self) -> 'PollDetail':
        total_votes = sum(opt.vote_count for opt in self.options)
        
        for opt in self.options:
            if total_votes > 0:
                # Set the private attribute directly
                opt._percentage = round((opt.vote_count / total_votes) * 100, 2)
            else:
                opt._percentage = 0.0
        return self

class PollOptionCreate(BaseModel):
    text: str
    sequence_order: int = 0

class PollCreate(BaseModel):
    # content_block fields
    title: str
    slug: Optional[str] = None
    deck: Optional[str] = None
    body: Optional[str] = None
    app_id: int
    widget_size: Optional[str] = 'medium'
    status: Optional[str] = 'draft'
    # Category fields
    category_id: Optional[int] = None
    # poll fields
    question: str
    poll_type: str = 'single'
    closes_at: Optional[datetime] = None
    options: list[PollOptionCreate] = []

class VoteRequest(BaseModel):
    option_id: Optional[int] = None   # None for rating type
    rating_value: Optional[int] = None  # None for binary/single

class PollCreated(BaseModel):
    success: bool
    poll_id: int
    slug: str