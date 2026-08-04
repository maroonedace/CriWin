# Pull Python image
FROM python:3.12-slim

WORKDIR /app

# Install OS libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*


# Install required libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY bot/ ./bot

# Run the bot
CMD ["python", "-m", "bot"]