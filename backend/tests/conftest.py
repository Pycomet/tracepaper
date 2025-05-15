import pytest
from typing import Generator, Any
import os # Added
from unittest import mock # Added mock

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
def isolated_vector_db(tmp_path: Path, monkeypatch: MonkeyPatch) -> VectorDB:
    """
    Creates a VectorDB instance that uses temporary paths for its index files.
    It also patches app.main.vector_db_instance to use this isolated one during tests.
    """
    test_index_path = str(tmp_path / "test_vector_index.faiss")
    test_id_map_path = str(tmp_path / "test_vector_id_map.pkl")
    
    # This fixture creates an instance, but the app needs its own.
    # We will patch the VectorDB class used by app.main
    # or directly set app.main.vector_db_instance.

    # Since vector_db_instance is created in on_startup, we can patch 
    # the VectorDB class that on_startup will use.
    
    class PatchedVectorDB(VectorDB):
        def __init__(self, model_name="intfloat/e5-small-v2"):
            # Force usage of temp paths for any instance created via this patched class
            super().__init__(
                model_name=model_name, 
                index_file_path=test_index_path, 
                id_map_file_path=test_id_map_path
            )
    
    monkeypatch.setattr("app.main.VectorDB", PatchedVectorDB)
    
    # After tests, app.main.vector_db_instance might hold reference to PatchedVectorDB.
    # We need to ensure it's reset if app instance persists across test client contexts.
    # For TestClient, a new app instance is usually used or configured per client context.
    # However, our global `app.main.vector_db_instance` variable needs to be cleared too.
    monkeypatch.setattr("app.main.vector_db_instance", None) # Ensure it's recreated by on_startup

    # The fixture doesn't need to return the instance itself if it's just patching.
    # But for clarity or direct use in tests, it could.
    # For now, its job is to set up the patch.
    yield # Indicates the patch is active during the test

    # Teardown: monkeypatch automatically undoes its changes.
    # The tmp_path directory is also automatically cleaned up by pytest.

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

    # Correctly override the dependency
    original_get_session_dependency = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = get_session_override
    
    # Reset the global vector_db_instance in app.main before TestClient starts the app,
    # so that on_startup instantiates it using the (potentially) patched VectorDB class.
    monkeypatch.setattr("app.main.vector_db_instance", None)
    
    with TestClient(app) as c:
        yield c
    
    # Clean up dependency override
    if original_get_session_dependency is not None:
        app.dependency_overrides[get_session] = original_get_session_dependency
    else:
        del app.dependency_overrides[get_session]
    
    # Clean up vector_db_instance for the next test that might use the client fixture
    monkeypatch.setattr("app.main.vector_db_instance", None) # Ensure clean state for next test 