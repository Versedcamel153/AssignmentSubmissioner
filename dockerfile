FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Install Python dependencies first (better caching)
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Fix permissions for all app files
RUN chown -R appuser:appuser /app

# Collect static files (optional)
RUN python manage.py collectstatic --noinput || true

# Switch to non-root user
# USER appuser  # Commented out for development with volume mounts

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "AssSub.wsgi:application", "--bind", "0.0.0.0:8000"]