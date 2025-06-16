FROM python:3.9-slim

# Install tesseract-ocr
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Expose the port (Render will set the PORT env var)
EXPOSE $PORT

# Start command
CMD ["python", "schedule.py"]