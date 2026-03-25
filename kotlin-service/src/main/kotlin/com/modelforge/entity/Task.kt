package com.modelforge.entity

import java.time.Instant
import java.util.UUID

data class Task(
    val id: UUID = UUID.randomUUID(),
    val userId: UUID,
    val status: TaskStatus = TaskStatus.PENDING,
    val prompt: String? = null,
    val s3InputKey: String? = null,
    val s3OutputKey: String? = null,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
)

enum class TaskStatus {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED
}
