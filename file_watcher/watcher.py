import time
import os
import requests
import fitz # PyMuPDF
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Set

# Configuration
WATCH_DIRECTORIES_ENV = os.getenv("WATCH_DIRECTORIES", "./watched_folders") # Comma-separated
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000") # Ensure this is correct for your setup
INGEST_ENDPOINT = f"{BACKEND_API_URL}/ingest/text"
SUPPORTED_EXTENSIONS = (".md", ".txt", ".pdf")

# Keep track of processed files (path and modification time) to avoid reprocessing identical states
# This is a simple in-memory cache. For persistence, a small DB or file could be used.
processed_files_cache: Set[str] = set()

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts all text content from a PDF file."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF {file_path}: {e}")
        return "" # Return empty string on error
    return text

class WatcherEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(SUPPORTED_EXTENSIONS):
            print(f"File created: {event.src_path}")
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(SUPPORTED_EXTENSIONS):
            print(f"File modified: {event.src_path}")
            self.process_file(event.src_path)

    def process_file(self, file_path):
        try:
            file_stat = os.stat(file_path)
            file_id = f"{file_path}::{file_stat.st_mtime}"

            if file_id in processed_files_cache:
                print(f"Skipping already processed file state: {file_path}")
                return

            if file_stat.st_size == 0:
                print(f"Skipping empty file: {file_path}")
                return

            print(f"Processing file: {file_path}")
            
            filename = os.path.basename(file_path)
            file_ext = os.path.splitext(filename)[1].lower()
            content = ""
            source_type = ""

            if file_ext == ".pdf":
                source_type = "pdf"
                content = extract_text_from_pdf(file_path)
            elif file_ext in (".md", ".txt"):
                source_type = "markdown" if file_ext == ".md" else "textfile"
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading text file {file_path}: {e}")
                    return # Skip if reading fails
            else:
                # Should not happen if SUPPORTED_EXTENSIONS check in on_created/on_modified is working
                print(f"Skipping unsupported file type during processing: {file_path}")
                return

            if not content.strip():
                print(f"Skipping file with no actual content: {file_path}")
                return

            payload = {
                "text": content,
                "source_type": source_type,
                "source_title": filename,
                "source_url": os.path.abspath(file_path) # Using absolute path as the unique URL
            }

            response = requests.post(INGEST_ENDPOINT, json=payload)

            if response.status_code == 200:
                print(f"Successfully ingested: {file_path}. Response: {response.json()}")
                processed_files_cache.add(file_id)
            elif response.status_code == 409: # Assuming 409 for conflict/duplicate hash if backend implements this
                print(f"Content from {file_path} might already exist or conflict. Response: {response.json()}")
                # Add to cache even if it's a known duplicate to avoid re-processing
                processed_files_cache.add(file_id)
            else:
                print(f"Error ingesting {file_path}: {response.status_code} - {response.text}")

        except FileNotFoundError:
            print(f"File not found (may have been deleted quickly): {file_path}")
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

def start_watching(directories_str: str):
    observer = Observer()
    event_handler = WatcherEventHandler()
    
    abs_paths = []
    for d in directories_str.split(','):
        d = d.strip()
        if not os.path.isdir(d):
            print(f"Warning: Directory '{d}' does not exist. Creating it.")
            try:
                os.makedirs(d, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory {d}: {e}. Skipping.")
                continue
        abs_path = os.path.abspath(d)
        abs_paths.append(abs_path)
        observer.schedule(event_handler, abs_path, recursive=True)
        print(f"Watching directory: {abs_path}")

    if not abs_paths:
        print("No valid directories to watch. Exiting.")
        return

    observer.start()
    print("File watcher started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("File watcher stopped.")
    observer.join()

if __name__ == "__main__":
    # Create a dummy watched_folders directory if it doesn't exist for local testing
    # In Docker, this would typically be a mounted volume.
    if not os.path.exists("./watched_folders"):
        os.makedirs("./watched_folders/subdir", exist_ok=True)
        with open("./watched_folders/sample.md", "w") as f:
            f.write("# Sample Markdown\nHello World!")
        with open("./watched_folders/subdir/another.txt", "w") as f:
            f.write("This is another text file in a subdirectory.")
        # Add a dummy PDF for local testing if PyMuPDF is available
        try:
            doc = fitz.open() # Create a new empty PDF
            page = doc.new_page()
            page.insert_text(fitz.Point(50, 72), "Hello PDF from Tracepaper watcher test!")
            doc.save("./watched_folders/sample.pdf")
            doc.close()
            print("Created dummy ./watched_folders/sample.pdf for local testing.")
        except Exception as e:
            print(f"Could not create dummy PDF for testing (PyMuPDF may not be fully working): {e}")
        print("Created dummy ./watched_folders with sample files for local testing.")
        
    print(f"Watching directories from ENV: {WATCH_DIRECTORIES_ENV}")
    print(f"Backend API URL: {BACKEND_API_URL}")
    start_watching(WATCH_DIRECTORIES_ENV) 