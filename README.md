# 🧠 Tracepaper

> Your offline-first AI research assistant.

Tracepaper quietly and privately monitors your research activity—papers, podcasts, videos, code—and turns it into structured knowledge you can query, summarize, and review.

![Uploading Screenshot 2025-05-25 at 01.03.46.png…]()


## ✨ Features (MVP)

- Desktop App UI (Electron)
- FastAPI backend with Whisper + Summarization LLMs
- Chrome extension to track YouTube, GitHub, and blogs
- PDF folder monitoring & ingestion
- Semantic vector search
- "Daily knowledge summary" generation

## 🏗 Architecture

Tracepaper is designed with a modular, local-first architecture. The core components are:

1.  **Desktop Application (Electron + React + TailwindCSS)**:
    *   Provides the main user interface for viewing the semantic timeline, search results, and summaries.
    *   Manages user settings and input source toggles.
    *   Communicates with the Local AI Server via HTTP requests.

2.  **Local AI Server (Python FastAPI)**:
    *   The brain of Tracepaper, running entirely on the user's machine.
    *   **Content Ingestion API**: Receives data from various sources (browser extension, watchers).
    *   **Content Parser & Indexer**:
        *   Extracts text from PDFs, web pages, and other formats.
        *   Generates embeddings using sentence transformers (e.g., `intfloat/e5-small-v2`).
        *   Stores text and metadata in a local SQLite database.
        *   Indexes embeddings in a local vector database (FAISS or Qdrant) for semantic search.
    *   **AI Services**:
        *   **Transcription**: Uses Whisper for transcribing audio from videos or podcasts.
        *   **Summarization**: Uses models like T5 or Mistral to generate summaries.
        *   **Classification**: (Future) For auto-tagging content by topic.
    *   **Query Engine**: Handles semantic search requests and "daily learn" queries.

3.  **Browser Extension (Chrome - WebExtension APIs)**:
    *   Monitors user activity in the browser (active tabs, visited pages like arXiv, Medium, GitHub).
    *   Scrapes relevant content from web pages.
    *   Sends content to the Local AI Server for ingestion.

4.  **Watchers (Python - `watchdog`)**:
    *   **PDF Watcher**: Monitors specified folders (e.g., Downloads) for new PDF files.
    *   **Markdown/Text File Watcher**: Monitors specified folders for `.md` and `.txt` files, sending their content for ingestion.
    *   **Clipboard Watcher**: (Stretch Goal) Monitors clipboard for text/code snippets.
    *   Parses new files/content and sends them to the Local AI Server.

5.  **Data Stores**:
    *   **SQLite**: Stores metadata about ingested content (source, title, timestamp, tags, raw text paths).
    *   **Vector Database (FAISS/Qdrant)**: Stores semantic embeddings for efficient similarity search.
    *   **File System**: Stores raw extracted text, original PDFs, and potentially audio files.

### Text Representation of Flow:

```
+---------------------+        +------------------------+       +----------------------+
|  Browser Extension  | -----> |  Local FastAPI Server  | <---- |    Desktop GUI App   |
| (Sends Page Data)   |        |  (API, AI Models, DB)  |       | (UI, Search, Config) |
+---------------------+        +----------^-------------+       +----------+-----------+
                                          |                                |
+---------------------+                   |                      +---------v----------+
| PDF/Folder Watcher  | ------------------+                      |  Semantic Timeline  |
| (Sends File Data)   |                                          |  + Search/Summary   |
+---------------------+                                          +---------------------+

+---------------------+
| Clipboard Watcher   | ------------------> (Optional: Local AI Server)
| (Sends Copied Text) |
+---------------------+
```

## 🗺️ Project Roadmap (MVP Focus)

This outlines the planned development stages for the Minimum Viable Product (MVP).

1.  **Phase 1: Core Backend Setup**
    *   [x] Initialize FastAPI project structure.
    *   [x] Define core data models (Source, ContentItem, Summary) using SQLModel.
    *   [x] Setup SQLite database and basic CRUD operations for models.
    *   [x] Implement initial VectorDB manager (FAISS) with embedding generation (`intfloat/e5-small-v2`).
    *   [x] Create basic API endpoints for:
        *   `POST /ingest/text` (for simple text ingestion)
        *   `GET /search?query=<query>` (basic semantic search)
        *   `GET /health`
        *   `GET /content_items` & `GET /content_items/{item_id}`

2.  **Phase 2: Desktop Application Shell & Basic UI (TypeScript)**
    *   [x] Initialize Electron project with React, TailwindCSS, and **TypeScript** (`desktop` directory, `package.json`, `tsconfig.json`).
    *   [x] Setup basic Electron `main.js` and `preload.js`.
    *   [x] Create a simple React UI (`App.tsx`) with placeholders for search and results, styled with TailwindCSS, and converted to TypeScript.
    *   [x] Connect Desktop App to FastAPI backend (initial `fetch` to `/health` and `/search` implemented in `App.tsx`).
    *   [x] Refine basic UI layout for timeline view (placeholder components `TimelineView.tsx`, `TimelineItem.tsx` created and integrated; basic data fetching from `/content_items` added, all in TypeScript).

3.  **Phase 3: Content Ingestion - File Watchers**
    *   [+] **Markdown/Text File Watcher**:
        *   [x] Develop Python `watchdog` script for monitoring folders for `.md`, `.txt` files (`file_watcher/watcher.py`).
        *   [x] Integrate with backend `/ingest/text` endpoint.
        *   [x] Dockerize the file watcher service and add to `docker-compose.yml`.
    *   [+] **PDF Watcher**:
        *   [x] Update `file_watcher/watcher.py` to detect `.pdf` files.
        *   [x] Implement PDF text extraction using `PyMuPDF` within the watcher.
        *   [x] Integrate with existing backend `/ingest/text` endpoint by sending extracted text (source_type="pdf").
        *   [x] Add `PyMuPDF` to `file_watcher/requirements.txt`.
        *   [x] Backend tests updated for `source_type="pdf"`.
        *   [x] File watcher tests updated for PDF processing.

4.  **Phase 4: Content Ingestion - Browser Extension**
    *   [x] Initialize Chrome Extension structure (`browser_extension/` with `manifest.json`, `background.js`, `popup.html/js`, `content_script.js`).
    *   [x] Implement basic content script (`content_script.js`) for text extraction (very naive initial version).
    *   [x] Implement popup (`popup.js`) to trigger content script execution and message background script.
    *   [x] Implement background script (`background.js`) to listen for messages, coordinate with content script, and make API calls.
    *   [x] Create backend endpoint `POST /ingest/webpage` in `backend/app/main.py`.
    *   [x] Add backend tests for `/ingest/webpage`.
    *   Note: Content extraction in `content_script.js` is very basic and needs significant improvement for reliability across different websites. Placeholder icons need to be added to `browser_extension/images/`.

5.  **Phase 5: AI Features - Summarization & Timeline**
    *   [x] Integrate a summarization model (e.g., `google/flan-t5-base`) into the FastAPI server.
    *   [x] Create API endpoint `POST /summarize` (accepts text or content IDs).
    *   [x] Develop "Daily Knowledge Summary":
        *   Query content items for "today".
        *   Summarize them.
        *   Endpoint `GET /summary/today`.
    *   [x] Enhance Desktop UI to display ingested content in a timeline view.
    *   [x] Allow users to view summaries in the UI.

6.  **Phase 6: Advanced Features & Refinements (MVP Polish)**
    *   [ ] (Optional) Integrate Whisper for audio transcription if YouTube/podcast ingestion is prioritized for MVP.
        *   Endpoint `POST /ingest/audio_url` (downloads audio, transcribes, ingests).
    *   [ ] Refine search functionality and UI.
    *   [ ] Add basic settings to the Desktop App (e.g., PDF folder path).
    *   [ ] Improve error handling and logging across all components.
    *   [ ] Write comprehensive "Getting Started" and usage instructions in README.

7.  **Stretch Goals (Post-MVP)**
    *   [ ] VS Code extension.
    *   [ ] Clipboard watcher for text/code.
    *   [ ] Podcast mode (live transcription).
    *   [ ] Advanced semantic timeline (topic grouping, idea tagging).
    *   [ ] More sophisticated query interface ("What did I learn about X this week?").

## 🛠 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/tracepaper
cd tracepaper
```

### 2. Run the backend (Python)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Run the Electron app

```bash
cd desktop
npm install
npm start
```

### 4. Install the Chrome Extension (Development)

1.  Open Chrome and navigate to `chrome://extensions`.
2.  Enable **Developer mode** (usually a toggle in the top right).
3.  Click **"Load unpacked"**.
4.  Select the `tracepaper/browser_extension` directory from your project.
5.  The Tracepaper Companion extension should now appear in your extensions list and toolbar.
    *   Remember to add placeholder icons (`icon16.png`, `icon48.png`, `icon128.png`) to `browser_extension/images/` to avoid icon errors.
    *   The content extraction is very basic. It will work best on simple article pages.

### 5. (Alternative) Running with Docker (Backend and File Watcher)

This method is useful for running the backend service and file watcher in containerized environments. Ensure you have Docker and Docker Compose installed.

1.  **Configure Watched Directories (Optional)**:
    *   By default, the `file-watcher` service in `docker-compose.yml` is set to watch a directory named `watched_markdown_files` in the project root, which gets mounted into `/data/watched_markdown_files` inside the container.
    *   You can create this directory: `mkdir watched_markdown_files`
    *   Place any `.md`, `.txt`, or `.pdf` files you want to be ingested into this folder.
    *   To watch other directories, you can modify the `volumes` section for the `file-watcher` service in `docker-compose.yml` and update the `WATCH_DIRECTORIES` environment variable accordingly. For multiple directories, provide a comma-separated string to `WATCH_DIRECTORIES` (e.g., `/data/notes1,/data/docs2`) and ensure all corresponding volumes are mounted.

2.  **Build and Run the Services**:
    From the project root directory (where `docker-compose.yml` is located):
    ```bash
    docker-compose up --build
    ```
    To run in detached mode (in the background):
    ```bash
    docker-compose up --build -d
    ```
    The backend API will be available at `http://localhost:8000`. The file watcher will start monitoring the configured directories.

3.  **Stopping the Services**:
    If running in detached mode, or in another terminal:
    ```bash
    docker-compose down
    ```

## 🤖 LLM Models Used

* `openai/whisper-base` (ASR)
* `google/flan-t5-base` or `mistralai/Mistral-7B-Instruct` (Summarization)
* `intfloat/e5-small-v2` (Embedding for semantic indexing)

## 📄 License

MIT

---

## 🧪 Testing

A comprehensive test suite will be developed to ensure the reliability of all components. This will include:

*   **Backend Unit Tests (pytest)**: For individual functions, models, and helper utilities. (Setup in `backend/tests`)
*   **Backend Integration Tests (pytest + HTTPX)**: For API endpoints, database interactions, and vector DB integration. (Setup in `backend/tests`)
*   **Frontend Unit/Component Tests (Jest + React Testing Library)**: For React components in the `desktop` app (now `.tsx` files). (Initial tests for `App.tsx` and timeline components created. Run with `cd desktop && npm test`.)
*   **E2E Tests (Playwright/Cypress)**: (Future) For testing user flows across the desktop app and browser extension.

_(Test suite development will proceed in parallel with feature development. Frontend component tests can be run locally. Dockerization of test execution is a future enhancement.)_

## 🐳 Dockerization

To simplify development, testing, and deployment, Tracepaper components will be Dockerized:

*   **`docker-compose.yml`**: Located in the project root, this file orchestrates the backend service. It handles building the backend Docker image, port mapping, and volume mounting for persistent data (`backend/data`).
*   **`backend/Dockerfile`**: Defines the image for the Python FastAPI backend application, including dependency installation and server execution.
*   **`file_watcher/Dockerfile`**: Defines the image for the Python file watcher service.
*   **Desktop App Dockerization**: (Future Consideration) Dockerizing Electron apps for development or testing can be complex and might involve X11 forwarding or VNC. Initially, the desktop app will be run directly on the host.

_(Docker setup for the backend and file watcher is complete. This facilitates consistent testing and development environments.)_ 
