package com.modelforge.service

import com.modelforge.entity.OutboxStatus
import com.modelforge.repository.OutboxRepository
import io.micrometer.core.instrument.MeterRegistry
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Component

@Component
class OutboxScheduler(
    private val outboxRepository: OutboxRepository,
    private val kafkaTemplate: KafkaTemplate<String, String>,
    private val meterRegistry: MeterRegistry,
    @Value("\${modelforge.kafka.topic:modelforge.generation.requests}") private val topic: String,
    @Value("\${modelforge.outbox.max-retry:3}") private val maxRetry: Int,
    @Value("\${modelforge.outbox.batch-size:50}") private val batchSize: Int
) {

    private val logger = LoggerFactory.getLogger(OutboxScheduler::class.java)

    @Scheduled(fixedDelayString = "\${modelforge.outbox.poll-interval-ms:5000}")
    fun publishPendingEvents() {
        val events = outboxRepository.findPending(batchSize)
        if (events.isEmpty()) return

        logger.debug("Найдено {} PENDING событий для публикации", events.size)

        for (event in events) {
            try {
                kafkaTemplate.send(topic, event.id.toString(), event.payload).get()
                outboxRepository.markPublished(event.id)
                logger.info("Опубликовано событие {} типа {}", event.id, event.eventType)
                meterRegistry.counter("outbox.events.published", "event_type", event.eventType).increment()
            } catch (e: Exception) {
                logger.error("Ошибка публикации события {}: {}", event.id, e.message)
                outboxRepository.incrementRetry(event.id)

                if (event.retryCount + 1 >= maxRetry) {
                    outboxRepository.markFailed(event.id)
                    logger.error("Событие {} помечено как FAILED после {} попыток", event.id, maxRetry)
                    meterRegistry.counter("outbox.events.failed", "event_type", event.eventType).increment()
                }
            }
        }

        updateMetrics()
    }

    private fun updateMetrics() {
        OutboxStatus.entries.forEach { status ->
            val count = outboxRepository.countByStatus(status)
            meterRegistry.gauge("outbox.events.count", listOf(io.micrometer.core.instrument.Tag.of("status", status.name)), count)
        }
    }
}
