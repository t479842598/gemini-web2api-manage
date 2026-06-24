FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制核心模块
COPY gemini_web2api/ ./gemini_web2api/

# 复制默认配置（生产环境用环境变量覆写）
COPY config.example.json ./config.json

EXPOSE 8081

# 可通过环境变量 PORT 覆盖端口
ENV PORT=8081

CMD ["sh", "-c", "python -m gemini_web2api --port $PORT"]
