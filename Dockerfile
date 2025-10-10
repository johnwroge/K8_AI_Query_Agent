FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env* ./

# Add gunicorn to requirements or install here
RUN pip install --no-cache-dir gunicorn

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Run with gunicorn, pointing to the factory in src/main.py
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "src.main:create_app()"]