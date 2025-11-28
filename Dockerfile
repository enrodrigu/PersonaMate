FROM python:3.11-slim

WORKDIR /app

# Ensure the application package is importable as `src` inside the container
ENV PYTHONPATH=/app

# Install build deps and cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
<<<<<<< HEAD
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package installation
RUN pip install uvicorn uv

COPY requirements.txt /app/requirements.txt

# Install all dependencies using uv (much faster than pip)
RUN uv pip install --system -r /app/requirements.txt
=======
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
>>>>>>> origin/master

# Copy source
COPY src /app/src

WORKDIR /app/src/python

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
