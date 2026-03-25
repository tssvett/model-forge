package com.modelforge

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.config.TestKafkaConfig
import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.OutboxStatus
import com.modelforge.repository.OutboxRepository
import com.modelforge.service.OutboxCleanupScheduler
import com.modelforge.service.OutboxScheduler
import org.junit.jupiter.api.*
import org.junit.jupiter.api.Assertions.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.test.context.ActiveProfiles
import org.mockito.Mockito.*
import java.util.UUID
import java.util.concurrent.CompletableFuture

/**
 * E2E тесты механизма Outbox: планировщик, публикация, retry, cleanup.
 */
@SpringBootTest
@ActiveProfiles("integration")
@Import(TestKafkaConfig::class)
@TestMethodOrder(MethodOrderer.OrderAnnotation::class)
class OutboxMechanismIntegrationTest {

    @Autowired
    lateinit var outboxRepository: OutboxRepository

    @Autowired
    lateinit var outboxScheduler: OutboxScheduler

    @Autowired
    lateinit var outboxCleanupScheduler: OutboxCleanupScheduler

    @Autowired
    lateinit var kafkaTemplate: KafkaTemplate<String, String>

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    @Autowired
    lateinit var objectMapper: ObjectMapper

    @BeforeEach
    fun cleanOutbox() {
        jdbcTemplate.update("DELETE FROM outbox_events")
        reset(kafkaTemplate)
    }

    @Test
    @Order(1)
    fun `01 - планировщик публикует PENDING события`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"${UUID.randomUUID()}","test":true}"""
        )
        outboxRepository.save(event)

        `when`(kafkaTemplate.send(anyString(), anyString(), anyString()))
            .thenReturn(CompletableFuture.completedFuture(null))

        outboxScheduler.publishPendingEvents()

        verify(kafkaTemplate).send(anyString(), eq(event.id.toString()), eq(event.payload))

        val count = outboxRepository.countByStatus(OutboxStatus.PUBLISHED)
        assertEquals(1, count)
    }

    @Test
    @Order(2)
    fun `02 - планировщик инкрементирует retry при ошибке Kafka`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"${UUID.randomUUID()}"}"""
        )
        outboxRepository.save(event)

        `when`(kafkaTemplate.send(anyString(), anyString(), anyString()))
            .thenReturn(CompletableFuture.failedFuture(RuntimeException("Kafka unavailable")))

        outboxScheduler.publishPendingEvents()

        val updated = jdbcTemplate.queryForMap(
            "SELECT * FROM outbox_events WHERE id = ?", event.id
        )
        assertEquals(1, updated["retry_count"])
        assertEquals("PENDING", updated["status"])
    }

    @Test
    @Order(3)
    fun `03 - событие помечается FAILED после превышения max retry`() {
        val event = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = """{"taskId":"${UUID.randomUUID()}"}""",
            retryCount = 2
        )
        outboxRepository.save(event)

        `when`(kafkaTemplate.send(anyString(), anyString(), anyString()))
            .thenReturn(CompletableFuture.failedFuture(RuntimeException("Kafka unavailable")))

        outboxScheduler.publishPendingEvents()

        val updated = jdbcTemplate.queryForMap(
            "SELECT * FROM outbox_events WHERE id = ?", event.id
        )
        assertEquals("FAILED", updated["status"])
    }

    @Test
    @Order(4)
    fun `04 - cleanup удаляет старые PUBLISHED события`() {
        // Вставляем PUBLISHED событие с published_at в прошлом
        val eventId = UUID.randomUUID()
        jdbcTemplate.update(
            """INSERT INTO outbox_events (id, event_type, payload, status, created_at, published_at, retry_count)
               VALUES (?, 'TASK_CREATED', '{}', 'PUBLISHED', DATEADD('DAY', -30, NOW()), DATEADD('DAY', -30, NOW()), 0)""",
            eventId
        )

        val before = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM outbox_events WHERE status = 'PUBLISHED'",
            Int::class.java
        )
        assertTrue(before!! > 0)

        outboxCleanupScheduler.cleanupPublishedEvents()

        val after = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM outbox_events WHERE id = ?",
            Int::class.java, eventId
        )
        assertEquals(0, after)
    }

    @Test
    @Order(5)
    fun `05 - cleanup не удаляет свежие PUBLISHED события`() {
        val eventId = UUID.randomUUID()
        jdbcTemplate.update(
            """INSERT INTO outbox_events (id, event_type, payload, status, created_at, published_at, retry_count)
               VALUES (?, 'TASK_CREATED', '{}', 'PUBLISHED', NOW(), NOW(), 0)""",
            eventId
        )

        outboxCleanupScheduler.cleanupPublishedEvents()

        val count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM outbox_events WHERE id = ?",
            Int::class.java, eventId
        )
        assertEquals(1, count)
    }

    @Test
    @Order(6)
    fun `06 - пустая очередь не вызывает ошибок`() {
        assertDoesNotThrow { outboxScheduler.publishPendingEvents() }
        verifyNoInteractions(kafkaTemplate)
    }

    @Test
    @Order(7)
    fun `07 - batch обработка нескольких событий`() {
        repeat(5) { i ->
            outboxRepository.save(
                OutboxEvent(
                    eventType = "TASK_CREATED",
                    payload = """{"index":$i}"""
                )
            )
        }

        `when`(kafkaTemplate.send(anyString(), anyString(), anyString()))
            .thenReturn(CompletableFuture.completedFuture(null))

        outboxScheduler.publishPendingEvents()

        verify(kafkaTemplate, times(5)).send(anyString(), anyString(), anyString())

        val published = outboxRepository.countByStatus(OutboxStatus.PUBLISHED)
        assertEquals(5, published)
    }

    @Test
    @Order(8)
    fun `08 - countByStatus возвращает корректные значения`() {
        outboxRepository.save(OutboxEvent(eventType = "TEST", payload = "{}"))
        outboxRepository.save(OutboxEvent(eventType = "TEST", payload = "{}"))

        assertEquals(2, outboxRepository.countByStatus(OutboxStatus.PENDING))
        assertEquals(0, outboxRepository.countByStatus(OutboxStatus.PUBLISHED))
        assertEquals(0, outboxRepository.countByStatus(OutboxStatus.FAILED))
    }
}
