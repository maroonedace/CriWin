# Pull Python image
FROM python:3.12-slim

WORKDIR /app

# Install required libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY bot/ ./bot

# Run the bot
CMD ["python", "-m", "bot"]