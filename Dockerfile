FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies as root during image build
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user inside the Docker image
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --create-home appuser

# Copy application code with non-root ownership
COPY --chown=appuser:appgroup app ./app

# Copy Alembic migration files
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini

# Run application as non-root user
USER appuser

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]