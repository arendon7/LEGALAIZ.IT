FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# pg_dump/pg_restore forman parte del ensayo M31.5. Se eliminan índices APT
# para no conservar cachés ni ampliar innecesariamente la imagen final.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt
COPY --chown=10001:10001 . .
RUN useradd --create-home --uid 10001 legalaiz \
    && mkdir -p /app/runtime /app/canonical_sources \
    && chown -R legalaiz:legalaiz /app
USER legalaiz
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/live', timeout=3)" || exit 1
CMD ["python", "run.py", "--lan", "--no-browser"]

STOPSIGNAL SIGTERM
