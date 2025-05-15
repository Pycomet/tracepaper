# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for Pillow, which might be a sub-dependency, or other C extensions)
# Add more as needed. For now, keeping it minimal.
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev musl-dev && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# This includes the 'app' directory (main.py, models.py, etc.) and any other necessary files at this level
COPY ./app ./app
# If you have other directories/files at the root of 'backend' that need to be in the image, copy them too.
# For example, if your .env file was here and needed by the app (though typically .env is not copied into images)

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run your app using uvicorn
# This assumes your FastAPI app instance is named 'app' in 'app.main'
# The host 0.0.0.0 makes it accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 