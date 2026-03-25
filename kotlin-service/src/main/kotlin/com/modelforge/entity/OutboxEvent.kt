package com.modelforge.entity

import java.time.Instant
import java.util.UUID

data class OutboxEvent(
    val id: UUID = UUID.randomUUID(),
    val eventType: String,
    val payload: String,
    val status: OutboxStatus = OutboxStatus.PENDING,
    val createdAt: Instant = Instant.now(),
    val publishedAt: Instant? = null,
    val retryCount: Int = 0
)

enum class OutboxStatus {
    PENDING,
    PUBLISHED,
    FAILED
}
