package com.modelforge.dto

import com.modelforge.entity.TaskStatus
import java.time.Instant
import java.util.UUID

data class CreateTaskRequest(
    val prompt: String? = null,
    val s3InputKey: String? = null
)

data class TaskResponse(
    val id: UUID,
    val userId: UUID,
    val status: TaskStatus,
    val prompt: String?,
    val s3InputKey: String?,
    val s3OutputKey: String?,
    val createdAt: Instant,
    val updatedAt: Instant
)

data class TaskCreatedEvent(
    val taskId: UUID,
    val userId: UUID,
    val prompt: String?,
    val s3InputKey: String?,
    val createdAt: Instant
)
