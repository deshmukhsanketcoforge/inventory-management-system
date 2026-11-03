# Pinned to an exact Python version, so a build next month uses the same Python
FROM python:3.12.16-slim

WORKDIR /app

# Dependencies change rarely, so they come first and stay cached
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The code changes most often, so it comes last
COPY . .

# The database lives in /data so a volume can keep it between containers
ENV INVENTORY_DB=/data/inventory.db
RUN mkdir -p /data

CMD ["python", "main.py"]
