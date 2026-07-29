# Python Image
FROM python:3.12-slim

# Set Work Directory
WORKDIR /criwin

# Install OS libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libpq-dev gcc curl unzip && \
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh && \
    rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p cache/sounds downloads cookies

# Install required libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Command to run application
CMD ["python", "main.py"]