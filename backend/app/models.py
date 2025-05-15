import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel # type: ignore

# Helper for timezone-aware default datetimes
def datetime_now_utc():
    return datetime.now(timezone.utc)

class SourceBase(SQLModel):
    type: str  # e.g., "pdf", "webpage", "youtube", "clipboard"
    url: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = Field(default=None)
    original_path: Optional[str] = Field(default=None) # For local files like PDFs


class Source(SourceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime_now_utc, index=True)
    updated_at: datetime = Field(default_factory=datetime_now_utc, index=True) # Consider onupdate

    content_items: List["ContentItem"] = Relationship(back_populates="source")


class SourceRead(SourceBase):
    id: uuid.UUID
    created_at: datetime


class ContentItemBase(SQLModel):
    text_content: str # The main textual content
    content_hash: str = Field(index=True) # To avoid duplicates
    metadata_json: Optional[str] = Field(default=None) # Store other metadata as JSON string
    processed_at: Optional[datetime] = Field(default=None, index=True)


class ContentItem(ContentItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    source_id: uuid.UUID = Field(foreign_key="source.id", index=True)
    created_at: datetime = Field(default_factory=datetime_now_utc, index=True)
    
    # Path to stored embedding vector (if stored separately, otherwise could be in vector DB directly)
    # embedding_path: Optional[str] = None 
    
    source: Optional[Source] = Relationship(back_populates="content_items")
    ai_summary: Optional["Summary"] = Relationship(
        sa_relationship_kwargs={"uselist": False}, # Ensures one-to-one
        back_populates="content_item_summarized"
    )
    # Potential future relationship:
    # summaries: List["SummaryAssociation"] = Relationship(back_populates="content_item")


class ContentItemRead(ContentItemBase):
    id: uuid.UUID
    source_id: uuid.UUID
    created_at: datetime
    source: Optional[SourceRead] = None


class SummaryBase(SQLModel):
    summary_text: str
    model_used: Optional[str] = Field(default=None) # e.g., "flan-t5-base"
    type: str = Field(default="manual", index=True) # e.g., "daily", "topic_cluster", "manual_selection"


class Summary(SummaryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime_now_utc, index=True)
    content_item_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contentitem.id", index=True, unique=True)
    # unique=True enforces one-to-one from the Summary side for this specific summary type

    content_item_summarized: Optional["ContentItem"] = Relationship(back_populates="ai_summary")
    
    # Many-to-many relationship with ContentItem if a summary can span multiple items
    # For MVP, a summary might be tied to one primary item or a query context
    # If related to many content items:
    # content_items: List["ContentItem"] = Relationship(back_populates="summaries", link_model=SummaryContentLink)

class SummaryRead(SummaryBase):
    id: uuid.UUID
    created_at: datetime

# Placeholder for a potential future SearchQuery log, if needed.
# class SearchQuery(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     query_text: str
#     results_json: Optional[str] = None # JSON string of result IDs and scores
#     timestamp: datetime = Field(default_factory=datetime_now_utc, index=True)

# Note: For many-to-many relationships like Summary-ContentItem, a link table would be needed.
# Example Link Table for Summary and ContentItem (if a summary can be composed of multiple items):
# class SummaryContentLink(SQLModel, table=True):
#    summary_id: uuid.UUID = Field(default=None, foreign_key="summary.id", primary_key=True)
#    content_item_id: uuid.UUID = Field(default=None, foreign_key="contentitem.id", primary_key=True) 