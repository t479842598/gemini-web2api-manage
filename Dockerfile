FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY gemini_web2api/ ./gemini_web2api/
COPY config.example.json ./config.json
EXPOSE 8081

CMD ["python", "-m", "gemini_web2api", "--config", "/app/config.json"]
