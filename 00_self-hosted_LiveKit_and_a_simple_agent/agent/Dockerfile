FROM python:3.12.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 agent
COPY --chown=agent:agent agent/ ./
COPY --chown=agent:agent scripts/loadtest.py ./loadtest.py
USER agent
RUN python main.py download-files
CMD ["python", "main.py", "start"]
