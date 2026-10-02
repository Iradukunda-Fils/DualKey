# SPDX-License-Identifier: MIT
# Dockerfile for DualKey Two-Factor Access Control System
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for OpenCV and V4L2 webcam / serial hardware
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    v4l-utils \
    usbutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests and package files
COPY pyproject.toml /app/
COPY app /app/app
COPY models /app/models
COPY tools /app/tools
COPY docs/README.md /app/docs/README.md

# Install Python dependencies and DualKey package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p data/models data/faces data/logs data/evaluation

# Default entrypoint
ENTRYPOINT ["dualkey"]
CMD ["--run", "--model", "lbph"]
