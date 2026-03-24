package com.modelforge.repository

import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.OutboxStatus
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.stereotype.Repository
import java.sql.ResultSet
import java.util.UUID

@Repository
class OutboxRepository(private val jdbcTemplate: JdbcTemplate) {

    private val rowMapper = RowMapper { rs: ResultSet, _: Int ->
        OutboxEvent(
            id = UUID.fromString(rs.getString("id")),
            eventType = rs.getString("event_type"),
            payload = rs.getString("payload"),
            status = OutboxStatus.valueOf(rs.getString("status")),
            createdAt = rs.getTimestamp("created_at").toInstant(),
            publishedAt = rs.getTimestamp("published_at")?.toInstant(),
            retryCount = rs.getInt("retry_count")
        )
    }

    fun save(event: OutboxEvent): OutboxEvent {
        jdbcTemplate.update(
            """INSERT INTO outbox_events (id, event_type, payload, status, created_at, published_at, retry_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            event.id, event.eventType, event.payload, event.status.name,
            java.sql.Timestamp.from(event.createdAt),
            event.publishedAt?.let { java.sql.Timestamp.from(it) },
            event.retryCount
        )
        return event
    }

    fun findPending(limit: Int): List<OutboxEvent> {
        return jdbcTemplate.query(
            "SELECT * FROM outbox_events WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT ?",
            rowMapper, limit
        )
    }

    fun markPublished(id: UUID) {
        jdbcTemplate.update(
            "UPDATE outbox_events SET status = 'PUBLISHED', published_at = NOW() WHERE id = ?",
            id
        )
    }

    fun markFailed(id: UUID) {
        jdbcTemplate.update(
            "UPDATE outbox_events SET status = 'FAILED', retry_count = retry_count + 1 WHERE id = ?",
            id
        )
    }

    fun incrementRetry(id: UUID) {
        jdbcTemplate.update(
            "UPDATE outbox_events SET retry_count = retry_count + 1 WHERE id = ?",
            id
        )
    }

    fun deletePublishedOlderThan(days: Int): Int {
        return jdbcTemplate.update(
            "DELETE FROM outbox_events WHERE status = 'PUBLISHED' AND published_at < DATEADD('DAY', ?, NOW())",
            -days
        )
    }

    fun countByStatus(status: OutboxStatus): Long {
        return jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM outbox_events WHERE status = ?",
            Long::class.java, status.name
        ) ?: 0
    }
}
