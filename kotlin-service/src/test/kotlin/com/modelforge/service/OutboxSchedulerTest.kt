package com.modelforge.service

import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.OutboxStatus
import com.modelforge.repository.OutboxRepository
import io.micrometer.core.instrument.MeterRegistry
import io.micrometer.core.instrument.simple.SimpleMeterRegistry
import org.junit.jupiter.api.Test
import org.mockito.kotlin.*
import org.springframework.kafka.core.KafkaTemplate
import java.util.UUID
import java.util.concurrent.CompletableFuture

class OutboxSchedulerTest {

    private val outboxRepository: OutboxRepository = mock()
    private val kafkaTemplate: KafkaTemplate<String, String> = mock()
    private val meterRegistry: MeterRegistry = SimpleMeterRegistry()

    private val scheduler = OutboxScheduler(
        outboxRepository = outboxRepository,
        kafkaTemplate = kafkaTemplate,
        meterRegistry = meterRegistry,
        topic = "test-topic",
        maxRetry = 3,
        batchSize = 50
    )

    @Test
    fun `publishPendingEvents публикует события в Kafka`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"123"}"""
        )

        whenever(outboxRepository.findPending(50)).thenReturn(listOf(event))
        whenever(kafkaTemplate.send(any<String>(), any(), any())).thenReturn(CompletableFuture.completedFuture(null))
        whenever(outboxRepository.countByStatus(any())).thenReturn(0)

        scheduler.publishPendingEvents()

        verify(kafkaTemplate).send(eq("test-topic"), eq(event.id.toString()), eq(event.payload))
        verify(outboxRepository).markPublished(event.id)
    }

    @Test
    fun `publishPendingEvents не вызывает Kafka при пустой очереди`() {
        whenever(outboxRepository.findPending(50)).thenReturn(emptyList())

        scheduler.publishPendingEvents()

        verifyNoInteractions(kafkaTemplate)
    }

    @Test
    fun `publishPendingEvents инкрементирует retry при ошибке`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"123"}""",
            retryCount = 0
        )

        whenever(outboxRepository.findPending(50)).thenReturn(listOf(event))
        whenever(kafkaTemplate.send(any<String>(), any(), any()))
            .thenReturn(CompletableFuture.failedFuture(RuntimeException("Kafka недоступна")))
        whenever(outboxRepository.countByStatus(any())).thenReturn(0)

        scheduler.publishPendingEvents()

        verify(outboxRepository).incrementRetry(event.id)
        verify(outboxRepository, never()).markPublished(any())
    }

    @Test
    fun `publishPendingEvents помечает FAILED после max retry`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"123"}""",
            retryCount = 2
        )

        whenever(outboxRepository.findPending(50)).thenReturn(listOf(event))
        whenever(kafkaTemplate.send(any<String>(), any(), any()))
            .thenReturn(CompletableFuture.failedFuture(RuntimeException("Kafka недоступна")))
        whenever(outboxRepository.countByStatus(any())).thenReturn(0)

        scheduler.publishPendingEvents()

        verify(outboxRepository).markFailed(event.id)
    }
}
