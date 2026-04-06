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

data class TaskDownloadResult(
    val taskId: UUID,
    val fileBytes: ByteArray,
    val format: String,
    val generatedAt: Instant
)

data class PagedResponse<T>(
    val content: List<T>,
    val page: Int,
    val size: Int,
    val totalElements: Long,
    val totalPages: Int
)

data class GenerationMetricsResponse(
    val taskId: UUID,
    val chamferDistance: Double?,
    val iou3d: Double?,
    val fScore: Double?,
    val normalConsistency: Double?,
    val vertices: Int?,
    val faces: Int?,
    val inferenceTimeSec: Double?,
    val isMock: Boolean,
    val createdAt: Instant
)
