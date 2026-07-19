# Use an official Python runtime with a specific version
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables to prevent Python from buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (wget is required by start.sh to download large files)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install CPU-only PyTorch (saves 2GB+ vs GPU version)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformer model into the image cache
# This avoids downloading it at runtime which causes slow cold starts
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application code
# NOTE: embeddings.pkl and library.db are NOT in the repo (too large for GitHub)
#       start.sh downloads them from GitHub Releases at first startup
COPY . .

# Expose port 8000
EXPOSE 8000

# Prepare startup script
COPY start.sh .
RUN chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]
