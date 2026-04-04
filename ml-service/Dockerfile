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

# System deps: g++ and git needed only for cpu/gpu (native extensions, TripoSR from git)
# python3.9-dev needed only for gpu (nvidia/cuda base has no python)
SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    $(if [ "$MODE" != "mock" ]; then echo "g++ git"; fi) \
    $(if [ "$MODE" = "gpu" ]; then echo "python3.9 python3.9-venv python3.9-dev python3-pip"; fi) \
    && rm -rf /var/lib/apt/lists/* \
    && if [ "$MODE" = "gpu" ]; then \
         ln -sf /usr/bin/python3.9 /usr/bin/python \
         && ln -sf /usr/bin/pip3 /usr/bin/pip; \
       fi

WORKDIR /app

# Layer 1: Base Python deps (~50MB, changes occasionally)
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Layer 2: Torch (~800MB CPU / ~2GB GPU, changes VERY rarely)
# Separate layer = cached forever until torch version bumps
COPY requirements-torch-cpu.txt requirements-torch-gpu.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$MODE" = "cpu" ]; then pip install -r requirements-torch-cpu.txt; \
    elif [ "$MODE" = "gpu" ]; then pip install -r requirements-torch-gpu.txt; fi

# Layer 3: TripoSR + ML deps (changes rarely, pinned commit)
COPY requirements-triposr.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$MODE" != "mock" ]; then pip install -r requirements-triposr.txt; fi

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM base-${MODE} AS runtime

ARG MODE
ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    $(if [ "$MODE" = "gpu" ]; then echo "python3.9 python3-pip"; fi) \
    && rm -rf /var/lib/apt/lists/* \
    && if [ "$MODE" = "gpu" ]; then \
         ln -sf /usr/bin/python3.9 /usr/bin/python; \
       fi

WORKDIR /app

# Copy installed packages from builder
# python:3.9-slim uses /usr/local/lib/python3.9/site-packages
# nvidia/cuda + apt python3.9 uses /usr/local/lib/python3.9/dist-packages
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
RUN if [ "$MODE" = "gpu" ]; then \
      cp -rn /usr/local/lib/python3.9/site-packages/* /usr/local/lib/python3.9/dist-packages/ 2>/dev/null || true \
      && cp -rn /usr/local/lib/python3.9/site-packages/* /usr/lib/python3/dist-packages/ 2>/dev/null || true; \
    fi

# App code — LAST layer, changes most often
COPY src/ ./src/
COPY scripts/ ./scripts/

# Common environment
ENV PYTHONPATH=/app/src \
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
