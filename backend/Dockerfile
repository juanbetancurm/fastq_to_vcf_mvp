FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect Django admin static assets into the image.
# Dummy secrets are safe here — collectstatic never touches the database.
RUN SECRET_KEY=build-only DB_PASSWORD=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# migrate runs before gunicorn so the schema is always current on startup.
# The celery service overrides CMD, so it skips this migration step.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
