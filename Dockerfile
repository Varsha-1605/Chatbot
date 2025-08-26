# Use an official Python 3.11 slim image as a base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Update package lists and install system dependencies for Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python packages from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download the NLTK data required by the sentiment analyzer
RUN python -m nltk.downloader punkt vader_lexicon

# Copy the rest of your application's code (including static/ and templates/)
COPY . .

# Let Render know which port your application is listening on
EXPOSE 5001

# Set an environment variable for Python
ENV PYTHONUNBUFFERED=1

# The command to run your application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]