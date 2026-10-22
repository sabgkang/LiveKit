FROM python:3.12.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY web/ ./
# Bundle the pinned SDK into the image; clients need no CDN access at runtime.
RUN python -c "import urllib.request; urllib.request.urlretrieve('https://cdn.jsdelivr.net/npm/livekit-client@2.23.0/dist/livekit-client.umd.js', 'static/livekit-client.js')"
USER 10001:10001
CMD ["python", "server.py"]
