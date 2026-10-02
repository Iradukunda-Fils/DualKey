# SPDX-License-Identifier: MIT
# DualKey Multi-Stage Optimized Dockerfile

# ==============================================================================
# Stage 1: Builder (Dependency compilation & environment building)
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install minimal build tools required for C-extension wheel building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python virtual environment for runtime export
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy package manifests and source code
COPY pyproject.toml /build/
COPY app /build/app
COPY models /build/models
COPY tools /build/tools
COPY docs/README.md /build/docs/README.md

# Build wheels and install package into the virtual environment
RUN pip install --upgrade pip && \
    pip install .

# ==============================================================================
# Stage 2: Minimal Runtime (Tested base image with shared libraries)
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install tested, minimal runtime-only libraries for OpenCV, V4L2 webcam & USB serial
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    v4l-utils \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app /app/app
COPY models /app/models
COPY tools /app/tools

# Create data directories for SQLite db, face crops, logs, and benchmark output
RUN mkdir -p data/models data/faces data/logs data/evaluation

ENTRYPOINT ["dualkey"]
CMD ["--run", "--model", "lbph"]
