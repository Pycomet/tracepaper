import hashlib
import uuid
from typing import List, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel

from .database import create_db_and_tables, get_session, engine
from .models import (
    Source, SourceBase, SourceRead,
    ContentItem, ContentItemBase, ContentItemRead,
    Summary, SummaryRead
)
from .vector_db import VectorDB
from . import summarizer

vector_db_instance: Optional[VectorDB] = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Code to run on startup
    print("Application startup: Initializing resources...")
    create_db_and_tables()
    global vector_db_instance
    if vector_db_instance is None:
        vector_db_instance = VectorDB()
    print(f"Database and tables created. VectorDB initialized: {vector_db_instance.index_path}")
    
    try:
        summarizer.initialize_summarizer()
        print("Summarization pipeline initialized.")
    except Exception as e:
        print(f"ERROR: Summarization pipeline failed to initialize on startup: {e}")
        # Decide if this should prevent app startup or just log the error.
        # For now, it logs and the app will start, but summarization will fail.

    yield
    # Code to run on shutdown (if any)
    print("Application shutdown: Cleaning up resources...")
    # e.g., vector_db_instance.close() if it had a close method

app = FastAPI(
    title="Tracepaper API",
    description="Backend API for Tracepaper - your offline-first AI research companion",
    version="0.1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def calculate_hash(text_content: str) -> str:
    return hashlib.sha256(text_content.encode('utf-8')).hexdigest()

@app.get("/health", tags=["General"], summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "message": "Tracepaper API is running"}

@app.post("/ingest/text", response_model=ContentItemRead, tags=["Ingestion"], summary="Ingest raw text content")
async def ingest_text(
    text: str = Body(..., embed=True, description="The text content to ingest"),
    source_type: str = Body(default="manual_text", embed=True, description="Type of the source, e.g., 'clipboard', 'manual_text'"),
    source_title: Optional[str] = Body(default=None, embed=True, description="Optional title for the source of this text"),
    source_url: Optional[str] = Body(default=None, embed=True, description="Optional URL if this text is from a web source"),
    session: Session = Depends(get_session)
):
    content_hash = calculate_hash(text)
    existing_content_item = session.exec(
        select(ContentItem).where(ContentItem.content_hash == content_hash)
    ).first()

    if existing_content_item:
        print(f"Content with hash {content_hash} already exists (ID: {existing_content_item.id}). Returning existing.")
        return existing_content_item

    db_source = None
    if source_url:
        db_source = session.exec(select(Source).where(Source.url == source_url)).first()
    
    if not db_source:
        source_data = SourceBase(type=source_type, title=source_title, url=source_url)
        db_source = Source.model_validate(source_data)
        session.add(db_source)
        session.commit()
        session.refresh(db_source)
        print(f"Created new source: {db_source.id} ({db_source.type})")
    else:
        print(f"Using existing source: {db_source.id} for URL: {source_url}")

    content_item_data = ContentItemBase(text_content=text, content_hash=content_hash)
    db_content_item = ContentItem.model_validate(content_item_data, update={"source_id": db_source.id})
    
    session.add(db_content_item)
    session.commit()
    session.refresh(db_content_item)
    print(f"Created new content item: {db_content_item.id}")

    try:
        if vector_db_instance is None:
            raise HTTPException(status_code=500, detail="VectorDB not initialized")
        vector_db_instance.add_text_embedding(db_content_item.id, text)
        print(f"Added embedding for content item {db_content_item.id} to VectorDB.")
    except Exception as e:
        print(f"Error adding embedding to VectorDB for {db_content_item.id}: {e}")

    db_content_item.source = db_source
    return db_content_item

@app.post("/ingest/webpage", response_model=ContentItemRead, tags=["Ingestion"], summary="Ingest content from a webpage")
async def ingest_webpage(
    text: str = Body(..., embed=True, description="The main text content from the webpage"),
    source_url: str = Body(..., embed=True, description="The URL of the webpage"),
    source_title: Optional[str] = Body(default=None, embed=True, description="The title of the webpage"),
    session: Session = Depends(get_session)
):
    source_type = "webpage"
    content_hash = calculate_hash(text)

    existing_content_item = session.exec(
        select(ContentItem).where(ContentItem.content_hash == content_hash)
    ).first()

    if existing_content_item:
        print(f"Content with hash {content_hash} already exists (ID: {existing_content_item.id}). Verifying source link.")
        if existing_content_item.source and existing_content_item.source.url == source_url:
            print(f"Existing content item is already linked to this URL: {source_url}. Returning existing.")
            return existing_content_item
        else:
            print(f"Content hash matches, but source URL may differ or was not primary. Returning existing content item.")
            return existing_content_item

    db_source = session.exec(select(Source).where(Source.url == source_url)).first()
    
    if not db_source:
        source_data = SourceBase(type=source_type, title=source_title, url=source_url)
        db_source = Source.model_validate(source_data)
        session.add(db_source)
        session.commit()
        session.refresh(db_source)
        print(f"Created new source (webpage): {db_source.id} for URL: {source_url}")
    else:
        print(f"Using existing source (webpage): {db_source.id} for URL: {source_url}")
        if source_title and db_source.title != source_title:
            db_source.title = source_title
            session.add(db_source)
            session.commit()
            session.refresh(db_source)
            print(f"Updated title for existing source {db_source.id} to: {source_title}")

    content_item_data = ContentItemBase(text_content=text, content_hash=content_hash)
    db_content_item = ContentItem.model_validate(content_item_data, update={"source_id": db_source.id})
    
    session.add(db_content_item)
    session.commit()
    session.refresh(db_content_item)
    print(f"Created new content item for webpage: {db_content_item.id}")

    try:
        if vector_db_instance is None: 
            raise HTTPException(status_code=500, detail="VectorDB not initialized")
        vector_db_instance.add_text_embedding(db_content_item.id, text)
        print(f"Added webpage embedding for content item {db_content_item.id} to VectorDB.")
    except Exception as e:
        print(f"Error adding webpage embedding to VectorDB for {db_content_item.id}: {e}")

    db_content_item.source = db_source 
    return db_content_item

@app.get("/search", response_model=List[ContentItemRead], tags=["Search"], summary="Perform semantic search")
async def search_content(
    query: str,
    k: int = 5, 
    session: Session = Depends(get_session)
):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if vector_db_instance is None:
        raise HTTPException(status_code=500, detail="VectorDB not initialized")

    search_results_from_vector_db = vector_db_instance.search_similar(query, k=k)
    
    if not search_results_from_vector_db:
        return []

    content_item_ids = [result["content_item_id"] for result in search_results_from_vector_db]
    
    content_items_db = session.exec(
        select(ContentItem).where(ContentItem.id.in_(content_item_ids))
    ).all()

    id_to_item_map = {item.id: item for item in content_items_db}
    ordered_content_items = []
    for item_id in content_item_ids:
        if item_id in id_to_item_map:
            fetched_item = id_to_item_map[item_id]
            _ = fetched_item.source 
            ordered_content_items.append(fetched_item)
        else:
            print(f"Warning: ContentItem ID {item_id} from vector search not found in SQL database.")
    
    return ordered_content_items

# Define response model for ContentItem that includes the summary
class ContentItemReadWithSummary(ContentItemRead):
    ai_summary: Optional[SummaryRead] = None

@app.get("/content_items", response_model=List[ContentItemReadWithSummary], tags=["Content"], summary="List all content items with optional summaries")
async def list_content_items_with_summary(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    content_items_db = session.exec(select(ContentItem).offset(skip).limit(limit)).all()
    for item in content_items_db:
        _ = item.ai_summary 
        _ = item.source 
    return content_items_db

@app.get("/content_items/{item_id}", response_model=ContentItemReadWithSummary, tags=["Content"], summary="Get a specific content item with its summary")
async def get_content_item_with_summary(
    item_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    content_item = session.get(ContentItem, item_id)
    if not content_item:
        raise HTTPException(status_code=404, detail="ContentItem not found")
    _ = content_item.ai_summary 
    _ = content_item.source
    return content_item

class SummarizationRequest(SQLModel):
    max_length: Optional[int] = 150
    min_length: Optional[int] = 30

@app.post("/content_items/{item_id}/summarize", response_model=SummaryRead, tags=["AI Features"], summary="Generate or retrieve AI summary for a content item")
async def summarize_content_item(
    item_id: uuid.UUID,
    request_body: Optional[SummarizationRequest] = None, 
    session: Session = Depends(get_session)
):
    db_content_item = session.get(ContentItem, item_id)
    if not db_content_item:
        raise HTTPException(status_code=404, detail="ContentItem not found")

    existing_summary = session.exec(
        select(Summary).where(Summary.content_item_id == item_id)
    ).first()

    if existing_summary:
        print(f"Returning existing summary {existing_summary.id} for content item {item_id}")
        return existing_summary

    text_to_summarize = db_content_item.text_content
    if not text_to_summarize.strip():
        raise HTTPException(status_code=400, detail="ContentItem has no text to summarize")

    max_len = request_body.max_length if request_body and request_body.max_length is not None else 150
    min_len = request_body.min_length if request_body and request_body.min_length is not None else 30

    print(f"Generating new summary for content item {item_id}...")
    summary_text = summarizer.generate_summary(text_to_summarize, max_length=max_len, min_length=min_len)

    if summary_text.startswith("Error:"):
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {summary_text}")

    new_summary = Summary(
        summary_text=summary_text,
        model_used=summarizer.MODEL_NAME, 
        type="ai_generated_item_summary",
        content_item_id=db_content_item.id
    )
    session.add(new_summary)
    session.commit()
    session.refresh(new_summary)
    print(f"Created and stored new summary {new_summary.id} for content item {item_id}")

    return new_summary

# To run this app (from the `backend` directory):
# Ensure you are in the `backend` directory first, then:
# uvicorn app.main:app --reload 