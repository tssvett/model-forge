--liquibase formatted sql

--changeset modelforge:006-create-generation-metrics-table
CREATE TABLE IF NOT EXISTS generation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    chamfer_distance DOUBLE PRECISION,
    iou_3d DOUBLE PRECISION,
    f_score DOUBLE PRECISION,
    normal_consistency DOUBLE PRECISION,
    vertices INTEGER,
    faces INTEGER,
    inference_time_sec DOUBLE PRECISION,
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_generation_metrics_task_id UNIQUE (task_id)
);
--rollback DROP TABLE IF EXISTS generation_metrics;

--changeset modelforge:006-create-generation-metrics-indexes
CREATE INDEX IF NOT EXISTS idx_generation_metrics_task_id ON generation_metrics(task_id);
--rollback DROP INDEX IF EXISTS idx_generation_metrics_task_id;
