# Use an official Python runtime with a specific version
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables to prevent Python from buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Explicitly install CPU-only version of PyTorch to save massive space (2GB+ savings)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the transformer model to the image cache to ensure fast startup
# This prevents downloading it at runtime which causes timeouts
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application code
COPY . .

# Initialize database if it doesn't exist
RUN if [ ! -f storage/library.db ]; then echo "Building database..."; python pipeline.py --db; fi

# Build embeddings if they don't exist
RUN if [ ! -f recommender/embeddings.pkl ]; then echo "Building embeddings..."; python recommender/build_embeddings.py; fi

# Expose port 8000 for the API
EXPOSE 8000

# Copy and prepare startup script
COPY start.sh .
RUN chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]
