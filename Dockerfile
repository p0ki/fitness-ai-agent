FROM python:3.11-slim

ARG APP_UID=1000
ARG APP_GID=1000

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip setuptools==83.0.0 \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY pytest.ini .
COPY tests/ ./tests/

RUN mkdir -p /data \
    && chown -R "$APP_UID:$APP_GID" /app /data

USER $APP_UID:$APP_GID

CMD ["python", "-m", "app.main"]
