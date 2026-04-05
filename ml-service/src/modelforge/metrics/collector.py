"""Prometheus metric definitions for ML Worker."""

from prometheus_client import Counter, Histogram, Gauge, Info

# Task-level metrics
TASKS_PROCESSED = Counter(
    "tasks_processed_total",
    "Total number of tasks processed",
    ["status"],  # "success" or "failed"
)

TASKS_ERRORS = Counter(
    "tasks_errors_total",
    "Total number of task processing errors",
    ["error_type"],
)

TASK_DURATION = Histogram(
    "task_processing_duration_seconds",
    "Time spent processing a single task end-to-end",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

TASKS_IN_PROGRESS = Gauge(
    "tasks_in_progress",
    "Number of tasks currently being processed",
)

# ML inference metrics
ML_INFERENCE_DURATION = Histogram(
    "ml_inference_duration_seconds",
    "Time spent on ML inference only",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

# Preprocessing metrics
PREPROCESSING_DURATION = Histogram(
    "preprocessing_duration_seconds",
    "Time spent on image preprocessing (validation, background removal, resize)",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

# S3 operation metrics
S3_OPERATION_DURATION = Histogram(
    "s3_operation_duration_seconds",
    "Time spent on S3 operations (upload/download)",
    ["operation"],  # "download" or "upload"
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

# Worker info
WORKER_INFO = Info(
    "ml_worker",
    "ML Worker metadata",
)
