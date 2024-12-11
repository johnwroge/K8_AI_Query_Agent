FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Updated CMD with better logging
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "debug", "--capture-output", "--enable-stdio-inheritance", "--access-logfile", "-", "--error-logfile", "-", "main:app"]