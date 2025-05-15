from fastapi.testclient import TestClient
from sqlmodel import Session, select
import uuid
import hashlib # Added for calculate_hash
from unittest import mock # Added for mocking

from app.models import ContentItem, Source, Summary # Added Summary
from app.main import calculate_hash # Import from main to avoid duplication if it changes

# Helper function (copied from main.py for test usage)
def calculate_hash(text_content: str) -> str:
    return hashlib.sha256(text_content.encode('utf-8')).hexdigest()

# Helper to create a content item for tests
def create_content_item_in_db(session: Session, text: str, source_type: str = "test", source_title: str = "Test Source") -> ContentItem:
    source = Source(type=source_type, title=source_title, url=f"http://test.com/{uuid.uuid4()}")
    session.add(source)
    session.commit()
    session.refresh(source)

    content_hash = calculate_hash(text)
    item = ContentItem(text_content=text, content_hash=content_hash, source_id=source.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

# Note: The `client` fixture is defined in conftest.py and automatically available.
# The `db_session` fixture is also from conftest.py.

def test_health_check(client: TestClient):
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Tracepaper API is running"}

def test_ingest_text_simple(client: TestClient, db_session: Session): # db_session is injected by pytest
    """Test the /ingest/text endpoint with new unique content."""
    test_text = f"This is a unique test document {uuid.uuid4()}"
    payload = {
        "text": test_text,
        "source_type": "test_suite",
        "source_title": "Test Document Title",
        "source_url": f"http://test.com/{uuid.uuid4()}"
    }
    response = client.post("/ingest/text", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["text_content"] == test_text
    assert data["source"]["type"] == "test_suite"
    assert data["source"]["title"] == "Test Document Title"
    assert data["source"]["url"] == payload["source_url"]
    
    # Verify in DB
    content_item_id = uuid.UUID(data["id"])
    db_item = db_session.get(ContentItem, content_item_id)
    assert db_item is not None
    assert db_item.text_content == test_text
    assert db_item.source.type == "test_suite"

def test_ingest_text_duplicate_content(client: TestClient, db_session: Session):
    """Test ingesting the exact same text content twice. Should return the original item."""
    unique_text = f"A piece of content for testing duplication {uuid.uuid4()}"
    payload1 = {
        "text": unique_text,
        "source_type": "first_ingestion",
        "source_title": "Original Title",
        "source_url": f"http://duplicate.test/{uuid.uuid4()}"
    }

    response1 = client.post("/ingest/text", json=payload1)
    assert response1.status_code == 200, response1.text
    data1 = response1.json()
    original_content_item_id = data1["id"]
    original_source_id = data1["source"]["id"]

    # Ingest the same text again, potentially with different source details
    payload2 = {
        "text": unique_text, # Same text content
        "source_type": "second_ingestion",
        "source_title": "Newer Title for Same Content",
        # For MVP, if content_hash matches, we return the existing item. 
        # The source of the *returned* item will be the *original* source.
        # If we wanted to link to a new source or update, the endpoint logic would need to change.
        "source_url": f"http://duplicate.test/new-attempt/{uuid.uuid4()}" 
    }
    response2 = client.post("/ingest/text", json=payload2)
    assert response2.status_code == 200, response2.text
    data2 = response2.json()

    assert data2["id"] == original_content_item_id # Should be the same content item ID
    # According to current logic in main.py, it returns the *existing* item, 
    # including its original source details if content_hash matches.
    assert data2["source"]["id"] == original_source_id
    assert data2["source"]["type"] == "first_ingestion" # Not "second_ingestion"

    # Verify only one ContentItem with this text exists
    items_in_db = db_session.exec(select(ContentItem).where(ContentItem.text_content == unique_text)).all()
    assert len(items_in_db) == 1

def test_ingest_text_same_url_different_content(client: TestClient, db_session: Session):
    """Test ingesting different content items that claim to be from the same source URL."""
    shared_url = f"http://shared.url/{uuid.uuid4()}"
    
    payload1 = {
        "text": f"First content for shared URL {uuid.uuid4()}",
        "source_type": "webpage",
        "source_title": "Page V1",
        "source_url": shared_url
    }
    response1 = client.post("/ingest/text", json=payload1)
    assert response1.status_code == 200
    data1 = response1.json()
    source_id1 = data1["source"]["id"]

    payload2 = {
        "text": f"Second, different content for shared URL {uuid.uuid4()}",
        "source_type": "webpage", # Could be same or different, URL is key here
        "source_title": "Page V2",
        "source_url": shared_url # Same URL
    }
    response2 = client.post("/ingest/text", json=payload2)
    assert response2.status_code == 200
    data2 = response2.json()
    source_id2 = data2["source"]["id"]

    # The current logic in main.py for /ingest/text:
    # If source_url is provided, it tries to find an existing Source with that URL.
    # If found, it uses that existing Source for the new ContentItem.
    assert source_id1 == source_id2 # Both content items should point to the same Source ID

    # Verify two distinct content items exist, linked to the same source
    source_in_db = db_session.get(Source, uuid.UUID(source_id1))
    assert source_in_db is not None
    assert len(source_in_db.content_items) == 2

def test_search_content_no_results(client: TestClient):
    """Test /search endpoint when no results are expected."""
    # Assuming a clean vector DB for this test or a very specific query
    # Note: VectorDB is global in main.py. For true isolation, it would need to be managed by fixtures.
    # For now, this test might be affected by previous tests if they added to the global vector_db_instance.
    # To make this more robust, we might need to clear the vector_db_instance or use a test-specific one.
    # This is a known limitation of the current test setup for vector_db.
    query = "zzxxccvvhjkhkjhasdflkjh"
    response = client.get(f"/search?query={query}")
    assert response.status_code == 200
    assert response.json() == []

def test_search_content_simple(client: TestClient, db_session: Session):
    """Test /search endpoint with an ingested item."""
    search_term = f"searchable_unique_term_{uuid.uuid4()}"
    text_to_ingest = f"This document contains a {search_term} for testing search functionality."
    
    ingest_payload = {
        "text": text_to_ingest,
        "source_type": "search_test",
        "source_title": "Searchable Doc"
    }
    ingest_response = client.post("/ingest/text", json=ingest_payload)
    assert ingest_response.status_code == 200
    ingested_data = ingest_response.json()
    ingested_item_id = ingested_data["id"]

    # It might take a moment for the embedding to be processed by the global vector_db_instance
    # In a real-world scenario with background processing, you might need to wait or mock.
    # Since our current vector_db.add_text_embedding is synchronous, it should be available.
    
    search_response = client.get(f"/search?query={search_term}&k=1")
    assert search_response.status_code == 200
    search_results = search_response.json()
    
    assert len(search_results) >= 1
    # The first result should be our ingested item
    # Note: score comparison can be tricky. Here we just check if the ID matches.
    found = any(item["id"] == ingested_item_id for item in search_results)
    assert found, f"Ingested item {ingested_item_id} not found in search results for query '{search_term}'"

def test_ingest_markdown_file_content(client: TestClient, db_session: Session):
    """Test ingesting content as if it came from a Markdown file."""
    markdown_content = f"# Markdown Title\n\nThis is some **bold** and *italic* text from a file. Unique: {uuid.uuid4()}"
    file_path = f"/watched_area/notes/test_doc_{uuid.uuid4()}.md"
    file_name = "test_doc.md"

    payload = {
        "text": markdown_content,
        "source_type": "markdown",
        "source_title": file_name, # Typically filename
        "source_url": file_path    # Full path to the file
    }
    response = client.post("/ingest/text", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["text_content"] == markdown_content
    assert data["source"]["type"] == "markdown"
    assert data["source"]["title"] == file_name
    assert data["source"]["url"] == file_path # This will also be used for original_path implicitly by current model
    
    # Verify in DB
    content_item_id = uuid.UUID(data["id"])
    db_item = db_session.get(ContentItem, content_item_id)
    assert db_item is not None
    assert db_item.text_content == markdown_content
    assert db_item.source.type == "markdown"
    assert db_item.source.url == file_path
    # Assuming the Source model's `url` is used for file path here. If `original_path` were distinct, test that.

def test_ingest_text_file_content(client: TestClient, db_session: Session):
    """Test ingesting content as if it came from a plain text file."""
    text_content = f"Plain text file content.\nWith multiple lines. Unique: {uuid.uuid4()}"
    file_path = f"/watched_area/text_files/sample_{uuid.uuid4()}.txt"
    file_name = "sample.txt"

    payload = {
        "text": text_content,
        "source_type": "textfile",
        "source_title": file_name,
        "source_url": file_path
    }
    response = client.post("/ingest/text", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["text_content"] == text_content
    assert data["source"]["type"] == "textfile"
    assert data["source"]["title"] == file_name
    assert data["source"]["url"] == file_path
    
    content_item_id = uuid.UUID(data["id"])
    db_item = db_session.get(ContentItem, content_item_id)
    assert db_item is not None
    assert db_item.source.type == "textfile"

def test_ingest_pdf_text_content(client: TestClient, db_session: Session):
    """Test ingesting pre-extracted text as if it came from a PDF file."""
    pdf_extracted_text = f"This is text extracted from a PDF document. Page 1 content. Page 2 content. Unique: {uuid.uuid4()}"
    file_path = f"/watched_area/pdfs/report_{uuid.uuid4()}.pdf"
    file_name = "report.pdf"

    payload = {
        "text": pdf_extracted_text,
        "source_type": "pdf", # Critical: This identifies the source as a PDF
        "source_title": file_name,
        "source_url": file_path # The original path to the PDF file
    }
    response = client.post("/ingest/text", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["text_content"] == pdf_extracted_text
    assert data["source"]["type"] == "pdf"
    assert data["source"]["title"] == file_name
    assert data["source"]["url"] == file_path
    
    # Verify in DB
    content_item_id = uuid.UUID(data["id"])
    db_item = db_session.get(ContentItem, content_item_id)
    assert db_item is not None
    assert db_item.text_content == pdf_extracted_text
    assert db_item.source.type == "pdf"
    assert db_item.source.url == file_path

def test_ingest_webpage_content_new(client: TestClient, db_session: Session):
    """Test the /ingest/webpage endpoint with new unique content."""
    page_text = f"Main content of a sample webpage. Unique ID: {uuid.uuid4()}"
    page_url = f"http://example.com/article/{uuid.uuid4()}"
    page_title = "Sample Article Title"

    payload = {
        "text": page_text,
        "source_url": page_url,
        "source_title": page_title
    }
    response = client.post("/ingest/webpage", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["text_content"] == page_text
    assert data["source"]["type"] == "webpage"
    assert data["source"]["title"] == page_title
    assert data["source"]["url"] == page_url
    
    content_item_id = uuid.UUID(data["id"])
    db_item = db_session.get(ContentItem, content_item_id)
    assert db_item is not None
    assert db_item.text_content == page_text
    assert db_item.source.type == "webpage"
    assert db_item.source.title == page_title
    assert db_item.source.url == page_url

def test_ingest_webpage_existing_url_update_title(client: TestClient, db_session: Session):
    """Test ingesting to an existing URL, ensuring title update and new content item."""
    page_url = f"http://example.com/article/persistent/{uuid.uuid4()}"
    
    # First ingestion
    payload1 = {
        "text": f"Initial content. {uuid.uuid4()}",
        "source_url": page_url,
        "source_title": "Original Title"
    }
    response1 = client.post("/ingest/webpage", json=payload1)
    assert response1.status_code == 200
    data1 = response1.json()
    source_id1 = data1["source"]["id"]
    content_item_id1 = data1["id"]

    db_source1 = db_session.get(Source, uuid.UUID(source_id1))
    assert db_source1.title == "Original Title"

    # Second ingestion to the same URL with different text and title
    payload2 = {
        "text": f"Updated content. {uuid.uuid4()}",
        "source_url": page_url,
        "source_title": "Updated Title"
    }
    response2 = client.post("/ingest/webpage", json=payload2)
    assert response2.status_code == 200
    data2 = response2.json()
    source_id2 = data2["source"]["id"]
    content_item_id2 = data2["id"]

    assert source_id1 == source_id2 # Source should be reused
    assert content_item_id1 != content_item_id2 # Content item should be new

    db_source2 = db_session.get(Source, uuid.UUID(source_id2))
    assert db_source2.title == "Updated Title" # Title should be updated
    assert len(db_source2.content_items) == 2

def test_ingest_webpage_duplicate_content_hash(client: TestClient, db_session: Session):
    """Test ingesting webpage content that has an identical text (content_hash) to an existing one."""
    shared_text = f"This exact text will be shared. {uuid.uuid4()}"
    url1 = f"http://example.com/page1/{uuid.uuid4()}"
    url2 = f"http://example.com/page2/{uuid.uuid4()}"

    # Ensure no source for url2 exists before we start
    pre_check_source_url2 = db_session.exec(select(Source).where(Source.url == url2)).first()
    assert pre_check_source_url2 is None, f"Source for url2 unexpectedly existed before test logic: {pre_check_source_url2}"

    # Ingest first instance
    payload1 = {"text": shared_text, "source_url": url1, "source_title": "Page 1"}
    response1 = client.post("/ingest/webpage", json=payload1)
    assert response1.status_code == 200
    data1 = response1.json()
    original_content_item_id = data1["id"]

    # Ingest second instance with same text but different URL/title
    payload2 = {"text": shared_text, "source_url": url2, "source_title": "Page 2"}
    response2 = client.post("/ingest/webpage", json=payload2)
    assert response2.status_code == 200 # Should succeed
    data2 = response2.json()

    assert data2["id"] == original_content_item_id
    assert data2["source"]["url"] == url1

    items_in_db = db_session.exec(select(ContentItem).where(ContentItem.content_hash == calculate_hash(shared_text))).all()
    assert len(items_in_db) == 1
    
    source1_db = db_session.exec(select(Source).where(Source.url == url1)).first()
    assert source1_db is not None

    source2_check = db_session.exec(select(Source).where(Source.url == url2)).first()
    assert source2_check is None

# --- Tests for Summarization ---

MOCKED_MODEL_NAME = "mocked-flan-t5-base"

@mock.patch("app.summarizer.generate_summary")
@mock.patch("app.summarizer.MODEL_NAME", MOCKED_MODEL_NAME)
def test_summarize_content_item_new(mock_generate_summary, client: TestClient, db_session: Session):
    """Test successfully generating a new summary for a content item."""
    mock_generate_summary.return_value = "This is a mock summary."
    
    item_text = f"Some long text to summarize {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)

    response = client.post(f"/content_items/{db_item.id}/summarize")
    assert response.status_code == 200, response.text
    summary_data = response.json()

    assert summary_data["summary_text"] == "This is a mock summary."
    assert summary_data["model_used"] == MOCKED_MODEL_NAME
    assert summary_data["type"] == "ai_generated_item_summary"
    
    mock_generate_summary.assert_called_once_with(item_text, max_length=150, min_length=30)

    # Verify in DB
    db_summary = db_session.get(Summary, uuid.UUID(summary_data["id"]))
    assert db_summary is not None
    assert db_summary.content_item_id == db_item.id
    assert db_item.ai_summary is not None # Relationship should be populated
    assert db_item.ai_summary.id == db_summary.id


@mock.patch("app.summarizer.generate_summary")
@mock.patch("app.summarizer.MODEL_NAME", MOCKED_MODEL_NAME)
def test_summarize_content_item_existing(mock_generate_summary, client: TestClient, db_session: Session):
    """Test retrieving an existing summary if called again."""
    mock_generate_summary.return_value = "First mock summary."
    item_text = f"Text for existing summary test {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)

    # First call - generates summary
    response1 = client.post(f"/content_items/{db_item.id}/summarize")
    assert response1.status_code == 200, response1.text
    summary_data1 = response1.json()
    original_summary_id = summary_data1["id"]
    mock_generate_summary.assert_called_once()

    # Second call - should retrieve existing
    mock_generate_summary.reset_mock() # Reset mock before second call
    response2 = client.post(f"/content_items/{db_item.id}/summarize")
    assert response2.status_code == 200, response2.text
    summary_data2 = response2.json()

    assert summary_data2["id"] == original_summary_id
    assert summary_data2["summary_text"] == "First mock summary."
    mock_generate_summary.assert_not_called() # Should not generate again

    # Verify only one summary in DB for this item
    summaries_for_item = db_session.exec(select(Summary).where(Summary.content_item_id == db_item.id)).all()
    assert len(summaries_for_item) == 1


def test_summarize_content_item_not_found(client: TestClient):
    """Test summarizing a non-existent ContentItem."""
    fake_item_id = uuid.uuid4()
    response = client.post(f"/content_items/{fake_item_id}/summarize")
    assert response.status_code == 404
    assert response.json()["detail"] == "ContentItem not found"


def test_summarize_content_item_no_text(client: TestClient, db_session: Session):
    """Test summarizing a ContentItem with empty text."""
    db_item = create_content_item_in_db(db_session, text="   ") # Empty or whitespace text
    response = client.post(f"/content_items/{db_item.id}/summarize")
    assert response.status_code == 400
    assert response.json()["detail"] == "ContentItem has no text to summarize"


@mock.patch("app.summarizer.generate_summary")
def test_summarize_content_item_summarizer_error(mock_generate_summary, client: TestClient, db_session: Session):
    """Test error handling when summarizer.generate_summary returns an error string."""
    mock_generate_summary.return_value = "Error: Model failed spectacularly."
    item_text = f"Text for summarizer error test {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)

    response = client.post(f"/content_items/{db_item.id}/summarize")
    assert response.status_code == 500, response.text
    assert "Failed to generate summary: Error: Model failed spectacularly." in response.json()["detail"]

@mock.patch("app.summarizer.initialize_summarizer", side_effect=Exception("Pipeline init failed"))
def test_summarize_content_item_init_error_on_demand(mock_init_summarizer, client: TestClient, db_session: Session, monkeypatch):
    """Test error if summarizer pipeline is None and fails to initialize on demand."""
    # Ensure pipeline is None for this specific test if generate_summary tries to init
    monkeypatch.setattr("app.summarizer.summarizer_pipeline", None)
    
    item_text = f"Text for init error test {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)

    response = client.post(f"/content_items/{db_item.id}/summarize")
    # If initialize_summarizer (called by generate_summary) raises an Exception, 
    # generate_summary should return "Error: Summarization service not available."
    # and the endpoint should raise a 500.
    assert response.status_code == 500, response.text
    assert "Failed to generate summary: Error: Summarization service not available." in response.json()["detail"]
    mock_init_summarizer.assert_called_once()


def test_get_content_item_with_summary(client: TestClient, db_session: Session):
    """Test GET /content_items/{item_id} includes the AI summary."""
    item_text = f"Text for get_item_with_summary test {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)
    
    # Manually create a summary for this item
    summary_text = "This is the AI summary for the item."
    db_summary = Summary(
        summary_text=summary_text,
        model_used=MOCKED_MODEL_NAME,
        type="ai_generated_item_summary",
        content_item_id=db_item.id
    )
    db_session.add(db_summary)
    db_session.commit()
    db_session.refresh(db_summary)
    db_session.refresh(db_item) # Refresh item to load relationship

    response = client.get(f"/content_items/{db_item.id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == str(db_item.id)
    assert "ai_summary" in data
    assert data["ai_summary"] is not None
    assert data["ai_summary"]["summary_text"] == summary_text
    assert data["ai_summary"]["model_used"] == MOCKED_MODEL_NAME


def test_get_content_item_without_summary(client: TestClient, db_session: Session):
    """Test GET /content_items/{item_id} when no AI summary exists."""
    item_text = f"Text for get_item_without_summary test {uuid.uuid4()}."
    db_item = create_content_item_in_db(db_session, text=item_text)

    response = client.get(f"/content_items/{db_item.id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == str(db_item.id)
    assert "ai_summary" in data
    assert data["ai_summary"] is None


def test_list_content_items_with_and_without_summary(client: TestClient, db_session: Session):
    """Test GET /content_items includes summaries correctly."""
    item1_text = f"Item 1 with summary {uuid.uuid4()}"
    db_item1 = create_content_item_in_db(db_session, text=item1_text)
    summary1_text = "Summary for item 1."
    db_summary1 = Summary(summary_text=summary1_text, model_used="test_model", type="ai_generated_item_summary", content_item_id=db_item1.id)
    db_session.add(db_summary1)

    item2_text = f"Item 2 no summary {uuid.uuid4()}"
    db_item2 = create_content_item_in_db(db_session, text=item2_text)
    
    db_session.commit()
    db_session.refresh(db_item1)
    db_session.refresh(db_item2)
    db_session.refresh(db_summary1)


    response = client.get("/content_items")
    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data) >= 2 # Could be more if other tests added items

    found_item1 = False
    found_item2 = False
    for item_data in data:
        if item_data["id"] == str(db_item1.id):
            found_item1 = True
            assert "ai_summary" in item_data
            assert item_data["ai_summary"] is not None
            assert item_data["ai_summary"]["summary_text"] == summary1_text
        elif item_data["id"] == str(db_item2.id):
            found_item2 = True
            assert "ai_summary" in item_data
            assert item_data["ai_summary"] is None
            
    assert found_item1, "Item 1 with summary not found in list"
    assert found_item2, "Item 2 without summary not found in list"


# --- End of Summarization Tests ---

# TODO:
# - Test for /content_items and /content_items/{item_id}
# - More detailed tests for search ranking/scoring if necessary (might be hard with L2 distance)
# - Tests for error conditions (e.g., invalid UUID for item_id)
# - Tests for vector_db directly (mocking sentence transformer or using a tiny test model)
# - The vector_db_instance in main.py is global. This means its state persists across tests.
#   For fully isolated search tests, this vector_db_instance would ideally be reset or use a 
#   test-specific, temporary index path configured via the test client or fixtures.
#   The current conftest.py does NOT manage the FAISS index file on disk for the global vector_db_instance.
#   The test_vector_db.py itself manages its own files if run directly. 