# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/

# Create directory for database
RUN mkdir -p /app/data

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Run the application
# Use sh -c to expand the PORT environment variable
CMD sh -c "python -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}"

