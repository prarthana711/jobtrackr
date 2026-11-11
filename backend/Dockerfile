FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install packages first. This layer is cached until requirements.txt changes,
# so editing your code doesn't reinstall everything.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a normal user instead of root, and make the uploads folder writable
RUN useradd --create-home appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

# Apply database migrations, then start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]