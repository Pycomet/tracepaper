import pytest
from typing import Generator, Any
import os # Added
from unittest import mock # Added mock
from sentence_transformers import SentenceTransformer # Import SentenceTransformer

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from pytest import MonkeyPatch # Added
from pathlib import Path # Added

# Import your FastAPI app and database functions
# Adjust the import path based on your project structure
# Assuming 'app' is the directory containing 'main.py', 'models.py', etc.
from app.main import app  # Your FastAPI application instance
from app.database import get_session # Your dependency_overrides target
from app.models import Source, ContentItem # Import all your models
from app.vector_db import VectorDB # Added

# Define a test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite:///./test.db" # Or "sqlite:///:memory:"

# Create a test engine
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False # echo=False for cleaner test output
)

@pytest.fixture(scope="session") # Removed autouse=True for more control if needed
def db_setup_session_scoped():
    """Session-scoped fixture to create and drop database tables."""
    # print("Creating test database tables...")
    SQLModel.metadata.create_all(engine)
    yield
    # print("Dropping test database tables...")
    SQLModel.metadata.drop_all(engine)
    # Attempt to remove the test.db file after session
    if os.path.exists("test.db"): # Check if it was file-based
        try:
            os.remove("test.db")
        except OSError as e:
            print(f"Error removing test.db: {e}")

@pytest.fixture(scope="function")
def db_session(db_setup_session_scoped: None) -> Generator[Session, Any, None]: # Ensure session scope runs first
    """Function-scoped fixture for a clean database session per test."""
    with Session(engine) as session:
        yield session
        # Optional: Clean up data if you want pristine tables for each test function
        # This can be slow if you have many tests that don't interfere.
        # for table in reversed(SQLModel.metadata.sorted_tables):
        #     session.execute(table.delete())
        # session.commit()

@pytest.fixture(scope="function")
def isolated_vector_db(tmp_path: Path, monkeypatch: MonkeyPatch) -> None: # Changed return to None
    """
    Creates a VectorDB instance that uses temporary paths for its index files.
    It also patches app.main.vector_db_instance to use this isolated one during tests
    and mocks the SentenceTransformer model loading.
    """
    test_index_path = str(tmp_path / "test_vector_index.faiss")
    test_id_map_path = str(tmp_path / "test_vector_id_map.pkl")

    # Create a mock SentenceTransformer
    mock_sentence_transformer_instance = mock.MagicMock(spec=SentenceTransformer)
    # Mock its methods. Adjust dimension as needed, e.g., e5-small-v2 uses 384
    mock_sentence_transformer_instance.get_sentence_embedding_dimension.return_value = 384 
    # Mock encode to return a dummy embedding of the correct shape
    dummy_embedding = [[0.1] * 384] # Example: batch of 1, dimension 384
    mock_sentence_transformer_instance.encode.return_value = dummy_embedding

    class PatchedVectorDB(VectorDB):
        def __init__(self, model_name="intfloat/e5-small-v2"):
            self.model_name = model_name
            self.index_path = test_index_path # Use temp path directly
            self.id_to_content_map_path = test_id_map_path # Use temp path directly
            
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.id_to_content_map_path), exist_ok=True)

            # Use the mocked SentenceTransformer instance
            self.model = mock_sentence_transformer_instance
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            
            self.load_or_create_index() # This will now use the mocked model's dim

    monkeypatch.setattr("app.main.VectorDB", PatchedVectorDB)
    monkeypatch.setattr("app.main.vector_db_instance", None) # Ensure it's recreated by on_startup

    yield

@pytest.fixture(scope="session", autouse=True) # Autouse to apply to all tests in a session
def mock_summarizer_init_session_scoped():
    """
    Mocks app.summarizer.initialize_summarizer for the entire test session
    to prevent actual model downloads or directory creation during most tests.
    Tests specifically wanting to test the real initialization would need to manage this mock.
    """
    with mock.patch("app.summarizer.initialize_summarizer") as mocked_init:
        mocked_init.return_value = None # Or any other simple return that signifies success without action
        print("INFO: app.summarizer.initialize_summarizer is mocked for the test session.")
        yield

@pytest.fixture(scope="function")
def client(
    db_session: Session, 
    isolated_vector_db: None, # Ensure this fixture runs to patch VectorDB
    monkeypatch: MonkeyPatch # Keep monkeypatch if used for other things, like app.main.vector_db_instance
) -> Generator[TestClient, Any, None]:
    """
    Pytest fixture to create a TestClient for your FastAPI app.
    This client will use the test database session.
    """
    def get_session_override() -> Generator[Session, Any, None]:
        yield db_session

    original_get_session_dependency = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = get_session_override
    
    monkeypatch.setattr("app.main.vector_db_instance", None)
    
    with TestClient(app) as c:
        yield c
    
    if original_get_session_dependency is not None:
        app.dependency_overrides[get_session] = original_get_session_dependency
    else:
        del app.dependency_overrides[get_session]
    
    monkeypatch.setattr("app.main.vector_db_instance", None) 