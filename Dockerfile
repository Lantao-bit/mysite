FROM --platform=linux/amd64 python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer caching)
COPY portfolio/requirements.txt requirements.txt
RUN pip install --no-cache-dir gunicorn && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY portfolio/ portfolio/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Default environment variables
ENV SECRET_KEY=change-me-in-production
ENV DATABASE_PATH=/app/data/portfolio.db
ENV FLASK_APP=portfolio.app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "portfolio.app:create_app()"]
