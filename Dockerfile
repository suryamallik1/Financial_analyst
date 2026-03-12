FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for vectorbt/pandas/numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Cloud Run expects
EXPOSE 8080

# Environment variables setup for Cloud Run
ENV PORT=8080
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app

# Command to run the FastApi application via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
