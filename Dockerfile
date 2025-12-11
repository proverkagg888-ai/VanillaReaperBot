FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install pip deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY . /app

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser || true && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]
