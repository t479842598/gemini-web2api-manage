FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Optional source deployment. The official release path is the Linux binary.
COPY _upstream/ ./_upstream/
COPY gemini_web2api_manage/ ./gemini_web2api_manage/
COPY config.example.json /app/config.example.json

# /data contains all mutable state and must be mounted by the caller.
RUN mkdir -p /data && cp /app/config.example.json /data/config.json
ENV GEMINI_WEB2API_DATA_DIR=/data
ENV PORT=8081

EXPOSE 8081

CMD ["sh", "-c", "python -m gemini_web2api_manage --port ${PORT}"]
