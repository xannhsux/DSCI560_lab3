FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY src/ ./src/
COPY config/ ./config/


ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]