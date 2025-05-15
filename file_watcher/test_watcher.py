import pytest
import os
import time
from unittest.mock import MagicMock, mock_open, patch

from . import watcher

@pytest.fixture
def mock_event_handler(mocker):
    handler = watcher.WatcherEventHandler()
    mocker.patch.object(handler, 'process_file') # Mock process_file to inspect calls
    return handler

@pytest.fixture
def mock_file_stat(mocker):
    stat_result = mocker.MagicMock()
    stat_result.st_mtime = time.time()
    stat_result.st_size = 100 # Non-empty file
    return stat_result

@pytest.fixture(autouse=True)
def clear_processed_cache():
    watcher.processed_files_cache.clear()
    yield
    watcher.processed_files_cache.clear()

def test_event_handler_on_created_supported_file(mock_event_handler, mocker):
    """Test that process_file is called for supported file types on creation."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/fake/path/test.md"
    mock_event_handler.on_created(event)
    mock_event_handler.process_file.assert_called_once_with("/fake/path/test.md")

def test_event_handler_on_created_unsupported_file(mock_event_handler):
    """Test that process_file is NOT called for unsupported file types."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/fake/path/test.py"
    mock_event_handler.on_created(event)
    mock_event_handler.process_file.assert_not_called()

def test_event_handler_on_modified_supported_file(mock_event_handler, mocker):
    """Test that process_file is called for supported file types on modification."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/fake/path/another.txt"
    mock_event_handler.on_modified(event)
    mock_event_handler.process_file.assert_called_once_with("/fake/path/another.txt")

def test_event_handler_on_created_pdf_file(mock_event_handler, mocker):
    """Test that process_file is called for PDF files on creation."""
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/fake/path/document.pdf"
    mock_event_handler.on_created(event)
    mock_event_handler.process_file.assert_called_once_with("/fake/path/document.pdf")

class TestProcessFile:

    def test_process_file_success_md(self, mocker, mock_file_stat):
        """Test successful processing and ingestion of a new markdown file."""
        file_path = "/test/data/sample.md"
        file_content = "# Hello Markdown"
        
        mocker.patch('os.stat', return_value=mock_file_stat)
        m_open = mock_open(read_data=file_content)
        mocker.patch('builtins.open', m_open)
        mock_post = mocker.patch('requests.post')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "123", "status": "ok"}
        mocker.patch('os.path.abspath', return_value=file_path) # Ensure abspath returns the mocked path

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        m_open.assert_called_once_with(file_path, 'r', encoding='utf-8')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == watcher.INGEST_ENDPOINT
        assert kwargs['json'] == {
            "text": file_content,
            "source_type": "markdown",
            "source_title": "sample.md",
            "source_url": file_path
        }
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id in watcher.processed_files_cache

    def test_process_file_success_txt(self, mocker, mock_file_stat):
        """Test successful processing and ingestion of a new text file."""
        file_path = "/test/data/sample.txt"
        file_content = "Hello Text"
        
        mocker.patch('os.stat', return_value=mock_file_stat)
        m_open = mock_open(read_data=file_content)
        mocker.patch('builtins.open', m_open)
        mock_post = mocker.patch('requests.post')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "123"}
        mocker.patch('os.path.abspath', return_value=file_path)

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_called_once()
        assert mock_post.call_args.kwargs['json']['source_type'] == "textfile"
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id in watcher.processed_files_cache

    def test_process_file_already_processed(self, mocker, mock_file_stat):
        """Test skipping a file that has already been processed (same path and mtime)."""
        file_path = "/test/data/processed.md"
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        watcher.processed_files_cache.add(file_id)

        mocker.patch('os.stat', return_value=mock_file_stat)
        mock_post = mocker.patch('requests.post')
        m_open = mocker.patch('builtins.open')

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called()
        m_open.assert_not_called()

    def test_process_file_empty_file(self, mocker, mock_file_stat):
        """Test skipping an empty file (size 0)."""
        file_path = "/test/data/empty.md"
        mock_file_stat.st_size = 0 # Empty file
        mocker.patch('os.stat', return_value=mock_file_stat)
        mock_post = mocker.patch('requests.post')
        m_open = mocker.patch('builtins.open')
        
        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called()
        m_open.assert_not_called()
        # Ensure not added to cache if skipped before content check
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache

    def test_process_file_no_content(self, mocker, mock_file_stat):
        """Test skipping a file with no actual content (e.g., only whitespace)."""
        file_path = "/test/data/whitespace.txt"
        mocker.patch('os.stat', return_value=mock_file_stat)
        m_open = mock_open(read_data="   \n  \t ")
        mocker.patch('builtins.open', m_open)
        mock_post = mocker.patch('requests.post')

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called()
        # Ensure not added to cache if skipped after content check
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache

    def test_process_file_api_error(self, mocker, mock_file_stat):
        """Test handling of API error during ingestion."""
        file_path = "/test/data/api_fail.md"
        mocker.patch('os.stat', return_value=mock_file_stat)
        m_open = mock_open(read_data="# Content")
        mocker.patch('builtins.open', m_open)
        mock_post = mocker.patch('requests.post')
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"
        mocker.patch('os.path.abspath', return_value=file_path)

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_called_once()
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache # Should not add to cache on error

    def test_process_file_api_conflict_409(self, mocker, mock_file_stat):
        """Test handling of API conflict (409) during ingestion, should cache."""
        file_path = "/test/data/api_conflict.md"
        mocker.patch('os.stat', return_value=mock_file_stat)
        m_open = mock_open(read_data="# Conflict Content")
        mocker.patch('builtins.open', m_open)
        mock_post = mocker.patch('requests.post')
        mock_post.return_value.status_code = 409
        mock_post.return_value.json.return_value = {"detail": "duplicate"}
        mocker.patch('os.path.abspath', return_value=file_path)

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_called_once()
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id in watcher.processed_files_cache # Should add to cache on 409

    def test_process_file_not_found(self, mocker):
        """Test handling FileNotFoundError during processing."""
        file_path = "/test/data/ghost.md"
        mocker.patch('os.stat', side_effect=FileNotFoundError)
        mock_post = mocker.patch('requests.post')

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called()
        # No specific cache check needed as it errors out before cache logic for new files.

    def test_process_file_generic_exception(self, mocker, mock_file_stat):
        """Test handling of a generic exception during file reading."""
        file_path = "/test/data/corrupt.md"
        mocker.patch('os.stat', return_value=mock_file_stat)
        mocker.patch('builtins.open', side_effect=IOError("Disk read error"))
        mock_post = mocker.patch('requests.post')

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called()
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache

    def test_process_file_success_pdf(self, mocker, mock_file_stat):
        """Test successful processing and ingestion of a new PDF file."""
        file_path = "/test/data/mydoc.pdf"
        pdf_text_content = "This is page 1.This is page 2."

        mocker.patch('os.stat', return_value=mock_file_stat)
        
        # Mock PyMuPDF (fitz)
        mock_fitz_doc = MagicMock()
        mock_fitz_page1 = MagicMock()
        mock_fitz_page1.get_text.return_value = "This is page 1."
        mock_fitz_page2 = MagicMock()
        mock_fitz_page2.get_text.return_value = "This is page 2."
        
        mock_fitz_doc.load_page.side_effect = [mock_fitz_page1, mock_fitz_page2]
        mock_fitz_doc.__len__.return_value = 2 # Two pages
        mock_fitz_open = mocker.patch('file_watcher.watcher.fitz.open', return_value=mock_fitz_doc)
        
        mock_post = mocker.patch('requests.post')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "pdf123"}
        mocker.patch('os.path.abspath', return_value=file_path)

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_fitz_open.assert_called_once_with(file_path)
        assert mock_fitz_doc.load_page.call_count == 2
        mock_fitz_doc.close.assert_called_once()

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == watcher.INGEST_ENDPOINT
        assert kwargs['json'] == {
            "text": pdf_text_content,
            "source_type": "pdf",
            "source_title": "mydoc.pdf",
            "source_url": file_path
        }
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id in watcher.processed_files_cache

    def test_process_file_pdf_extraction_fails(self, mocker, mock_file_stat):
        """Test PDF processing when text extraction fails."""
        file_path = "/test/data/corrupt.pdf"
        mocker.patch('os.stat', return_value=mock_file_stat)
        mock_fitz_open = mocker.patch('file_watcher.watcher.fitz.open', side_effect=Exception("PDF parse error"))
        mock_post = mocker.patch('requests.post')
        mocker.patch('os.path.abspath', return_value=file_path)
        mock_print = mocker.patch('builtins.print')

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_fitz_open.assert_called_once_with(file_path)
        mock_post.assert_not_called() # Should not call API if text extraction fails
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache
        assert any("Error extracting text from PDF /test/data/corrupt.pdf" in call.args[0] for call in mock_print.call_args_list if call.args)

    def test_process_file_pdf_empty_extracted_text(self, mocker, mock_file_stat):
        """Test PDF processing when extracted text is empty/whitespace."""
        file_path = "/test/data/empty_content.pdf"
        mocker.patch('os.stat', return_value=mock_file_stat)
        
        mock_fitz_doc = MagicMock()
        mock_fitz_page = MagicMock()
        mock_fitz_page.get_text.return_value = "   \n " # Whitespace only
        mock_fitz_doc.load_page.return_value = mock_fitz_page
        mock_fitz_doc.__len__.return_value = 1
        mocker.patch('file_watcher.watcher.fitz.open', return_value=mock_fitz_doc)
        
        mock_post = mocker.patch('requests.post')
        mocker.patch('os.path.abspath', return_value=file_path)

        handler = watcher.WatcherEventHandler()
        handler.process_file(file_path)

        mock_post.assert_not_called() # Should not call API if extracted text is blank
        file_id = f"{file_path}::{mock_file_stat.st_mtime}"
        assert file_id not in watcher.processed_files_cache

@patch('file_watcher.watcher.Observer')
def test_start_watching_single_dir_exists(MockObserver, mocker):
    """Test start_watching with a single existing directory."""
    mock_observer_instance = MockObserver.return_value
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.abspath', lambda x: x) # Simple pass-through for abspath
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt) # To break the loop

    watcher.start_watching("/test/watch_dir")

    MockObserver.assert_called_once()
    mock_observer_instance.schedule.assert_called_once()
    assert mock_observer_instance.schedule.call_args[0][1] == "/test/watch_dir"
    mock_observer_instance.start.assert_called_once()
    mock_observer_instance.join.assert_called_once()

@patch('file_watcher.watcher.Observer')
def test_start_watching_multiple_dirs(MockObserver, mocker):
    """Test start_watching with multiple comma-separated directories."""
    mock_observer_instance = MockObserver.return_value
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.abspath', side_effect=lambda x: f"/abs/{x.strip()}")
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt)

    watcher.start_watching("dir1, dir2 , dir3")

    assert mock_observer_instance.schedule.call_count == 3
    calls = mock_observer_instance.schedule.call_args_list
    scheduled_paths = {call[0][1] for call in calls}
    assert scheduled_paths == {"/abs/dir1", "/abs/dir2", "/abs/dir3"}

@patch('file_watcher.watcher.Observer')
def test_start_watching_dir_does_not_exist_create_success(MockObserver, mocker):
    """Test directory creation when a watched directory does not exist."""
    mock_observer_instance = MockObserver.return_value
    mocker.patch('os.path.isdir', return_value=False)
    mock_makedirs = mocker.patch('os.makedirs')
    mocker.patch('os.path.abspath', lambda x: x)
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt)

    watcher.start_watching("/new_dir")

    mock_makedirs.assert_called_once_with("/new_dir", exist_ok=True)
    mock_observer_instance.schedule.assert_called_once_with(mocker.ANY, "/new_dir", recursive=True)

@patch('file_watcher.watcher.Observer')
def test_start_watching_dir_creation_fails(MockObserver, mocker):
    """Test scenario where directory creation fails."""
    mock_observer_instance = MockObserver.return_value
    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.makedirs', side_effect=OSError("Permission denied"))
    mocker.patch('os.path.abspath', lambda x: x)
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt) # In case it still tries to start

    # Capture print output to verify warnings
    mock_print = mocker.patch('builtins.print')

    watcher.start_watching("/bad_dir")

    mock_observer_instance.schedule.assert_not_called() # Should not schedule if dir creation fails
    # Check if the error print for OSError was called
    assert any("Error creating directory /bad_dir" in call.args[0] for call in mock_print.call_args_list if call.args)

@patch('file_watcher.watcher.Observer')
def test_start_watching_no_valid_dirs(MockObserver, mocker):
    """Test start_watching when no valid directories are provided or can be created."""
    mock_observer_instance = MockObserver.return_value
    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.makedirs', side_effect=OSError("Failed for all"))
    mocker.patch('os.path.abspath', lambda x: x)
    
    # Capture print output
    mock_print = mocker.patch('builtins.print')

    watcher.start_watching("nonexistent1,nonexistent2")

    mock_observer_instance.schedule.assert_not_called()
    mock_observer_instance.start.assert_not_called()
    assert any("No valid directories to watch. Exiting." in call.args[0] for call in mock_print.call_args_list if call.args)

# Example of how one might test the __main__ block if needed, though often it's tested implicitly.
# For this, you might need to structure it to be importable or use subprocess.
# For now, focusing on the core watcher logic.

# To run these tests: `pytest file_watcher/test_watcher.py` 