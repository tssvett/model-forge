package com.modelforge.service

import com.modelforge.repository.OutboxRepository
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Component

@Component
class OutboxCleanupScheduler(
    private val outboxRepository: OutboxRepository,
    @Value("\${modelforge.outbox.retention-days:7}") private val retentionDays: Int
) {

    private val logger = LoggerFactory.getLogger(OutboxCleanupScheduler::class.java)

    @Scheduled(cron = "\${modelforge.outbox.cleanup-cron:0 0 3 * * *}")
    fun cleanupPublishedEvents() {
        val deleted = outboxRepository.deletePublishedOlderThan(retentionDays)
        if (deleted > 0) {
            logger.info("Очищено {} PUBLISHED событий старше {} дней", deleted, retentionDays)
        }
    }
}
