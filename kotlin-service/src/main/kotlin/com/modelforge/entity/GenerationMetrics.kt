package com.modelforge.entity

import java.time.Instant
import java.util.UUID

data class GenerationMetrics(
    val id: UUID,
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
