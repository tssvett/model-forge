package com.modelforge.entity

import java.time.Instant
import java.util.UUID

data class User(
    val id: UUID = UUID.randomUUID(),
    val email: String,
    val passwordHash: String,
    val createdAt: Instant = Instant.now()
)
