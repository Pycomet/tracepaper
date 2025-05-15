FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ENV WATCH_DIRECTORIES="/data/watched_files" # Example, can be overridden
# ENV BACKEND_API_URL="http://backend:8000"  # Example, can be overridden

CMD ["python", "watcher.py"] 