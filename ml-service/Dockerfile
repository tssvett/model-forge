# syntax=docker/dockerfile:1
#
# Unified Dockerfile for ModelForge ML Service
# Usage:
#   docker build --build-arg MODE=mock .   (default, no torch)
#   docker build --build-arg MODE=cpu .    (torch CPU + TripoSR)
#   docker build --build-arg MODE=gpu .    (torch CUDA + TripoSR)

ARG MODE=mock

# ── Base images per mode ─────────────────────────────────────────────────────
FROM python:3.9-slim AS base-mock
FROM python:3.9-slim AS base-cpu
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04 AS base-gpu

# ── Builder stage ────────────────────────────────────────────────────────────
FROM base-${MODE} AS builder

ARG MODE
ENV DEBIAN_FRONTEND=noninteractive

# GPU mode: nvidia/cuda base has no python — add deadsnakes PPA for python3.9
SHELL ["/bin/bash", "-c"]
RUN if [ "$MODE" = "gpu" ]; then \
      apt-get update && apt-get install -y --no-install-recommends software-properties-common \
      && add-apt-repository -y ppa:deadsnakes/ppa; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    $(if [ "$MODE" != "mock" ]; then echo "g++ git"; fi) \
    $(if [ "$MODE" = "gpu" ]; then echo "python3.9 python3.9-venv python3.9-dev python3-pip"; fi) \
    && rm -rf /var/lib/apt/lists/* \
    && if [ "$MODE" = "gpu" ]; then \
         ln -sf /usr/bin/python3.9 /usr/bin/python \
         && ln -sf /usr/bin/pip3 /usr/bin/pip; \
       fi

WORKDIR /app

# Install all pip packages to /install prefix — predictable path regardless of base image.
# This avoids the site-packages vs dist-packages divergence between python:3.9-slim and nvidia/cuda.

# Layer 1: Base Python deps (~50MB, changes occasionally)
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# Layer 2: Torch (~800MB CPU / ~2GB GPU, changes VERY rarely)
# Separate layer = cached forever until torch version bumps
COPY requirements-torch-cpu.txt requirements-torch-gpu.txt ./
RUN if [ "$MODE" = "cpu" ]; then pip install --no-cache-dir --prefix=/install -r requirements-torch-cpu.txt; \
    elif [ "$MODE" = "gpu" ]; then pip install --no-cache-dir --prefix=/install -r requirements-torch-gpu.txt; fi

# Layer 3: TripoSR + ML deps (changes rarely)
# TripoSR has no setup.py/pyproject.toml — clone via git, add to PYTHONPATH.
# Model weights are NOT in the image — loaded at runtime from HF_HOME volume,
# so fine-tuned weights can be swapped without rebuilding.
COPY requirements-triposr.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /opt/triposr \
    && if [ "$MODE" != "mock" ]; then \
         pip install --prefix=/install -r requirements-triposr.txt \
         && git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git /opt/triposr; \
       fi

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM base-${MODE} AS runtime

ARG MODE
ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-c"]
RUN if [ "$MODE" = "gpu" ]; then \
      apt-get update && apt-get install -y --no-install-recommends software-properties-common \
      && add-apt-repository -y ppa:deadsnakes/ppa; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    $(if [ "$MODE" = "gpu" ]; then echo "python3.9 python3-pip"; fi) \
    && rm -rf /var/lib/apt/lists/* \
    && if [ "$MODE" = "gpu" ]; then \
         ln -sf /usr/bin/python3.9 /usr/bin/python; \
       fi

WORKDIR /app

# Copy all pip packages from builder's /install prefix into the runtime Python path.
# --prefix=/install puts libs in /install/lib/python3.9/site-packages for ALL base images.
COPY --from=builder /install /usr/local
COPY --from=builder /opt/triposr /opt/triposr

# App code — LAST layer, changes most often
COPY src/ ./src/
COPY scripts/ ./scripts/

# Common environment
ENV PYTHONPATH=/app/src:/opt/triposr \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    HF_HOME=/app/.cache/huggingface

# Thread defaults (overridden by compose environment)
ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1

# GPU-specific (harmless on non-GPU images)
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["python", "-m", "modelforge.worker.main"]
