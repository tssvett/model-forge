package com.modelforge

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.config.TestKafkaConfig
import com.modelforge.dto.CreateTaskRequest
import com.modelforge.dto.LoginRequest
import com.modelforge.dto.RegisterRequest
import org.junit.jupiter.api.*
import org.junit.jupiter.api.Assertions.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.get

/**
 * E2E интеграционные тесты: полный поток от регистрации до создания задачи.
 * Проверяет систему целиком — контроллеры, сервисы, репозитории, базу данных, outbox.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@ActiveProfiles("integration")
@Import(TestKafkaConfig::class)
@TestMethodOrder(MethodOrderer.OrderAnnotation::class)
class FullFlowIntegrationTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var objectMapper: ObjectMapper

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    companion object {
        private const val TEST_EMAIL = "e2e-flow@example.com"
        private const val TEST_PASSWORD = "securePassword123"
        private var accessToken: String = ""
        private var taskId: String = ""
    }

    @Test
    @Order(1)
    fun `01 - регистрация нового пользователя`() {
        val request = RegisterRequest(email = TEST_EMAIL, password = TEST_PASSWORD)

        val result = mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isCreated() }
            jsonPath("$.accessToken") { exists() }
            jsonPath("$.tokenType") { value("Bearer") }
            jsonPath("$.expiresIn") { exists() }
        }.andReturn()

        val body = objectMapper.readTree(result.response.contentAsString)
        accessToken = body.get("accessToken").asText()
        assertTrue(accessToken.isNotBlank())
    }

    @Test
    @Order(2)
    fun `02 - повторная регистрация с тем же email возвращает 400`() {
        val request = RegisterRequest(email = TEST_EMAIL, password = TEST_PASSWORD)

        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isBadRequest() }
            jsonPath("$.code") { value(400) }
        }
    }

    @Test
    @Order(3)
    fun `03 - логин с правильными данными`() {
        val request = LoginRequest(email = TEST_EMAIL, password = TEST_PASSWORD)

        val result = mockMvc.post("/auth/login") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isOk() }
            jsonPath("$.accessToken") { exists() }
            jsonPath("$.tokenType") { value("Bearer") }
        }.andReturn()

        val body = objectMapper.readTree(result.response.contentAsString)
        accessToken = body.get("accessToken").asText()
    }

    @Test
    @Order(4)
    fun `04 - логин с неверным паролем возвращает 400`() {
        val request = LoginRequest(email = TEST_EMAIL, password = "wrongPassword")

        mockMvc.post("/auth/login") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isBadRequest() }
        }
    }

    @Test
    @Order(5)
    fun `05 - создание задачи с JWT токеном`() {
        val request = CreateTaskRequest(prompt = "Сгенерировать 3D-модель стула")

        val result = mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
            header("Authorization", "Bearer $accessToken")
        }.andExpect {
            status { isCreated() }
            jsonPath("$.id") { exists() }
            jsonPath("$.status") { value("PENDING") }
            jsonPath("$.prompt") { value("Сгенерировать 3D-модель стула") }
            jsonPath("$.userId") { exists() }
            jsonPath("$.createdAt") { exists() }
        }.andReturn()

        val body = objectMapper.readTree(result.response.contentAsString)
        taskId = body.get("id").asText()
        assertTrue(taskId.isNotBlank())
    }

    @Test
    @Order(6)
    fun `06 - outbox событие создано в БД после создания задачи`() {
        val events = jdbcTemplate.queryForList(
            "SELECT * FROM outbox_events WHERE event_type = 'TASK_CREATED' ORDER BY created_at DESC"
        )

        assertTrue(events.isNotEmpty(), "Outbox должен содержать хотя бы одно событие TASK_CREATED")

        val latestEvent = events.first()
        assertEquals("PENDING", latestEvent["status"])
        assertEquals(0, latestEvent["retry_count"])

        val payload = objectMapper.readTree(latestEvent["payload"] as String)
        assertEquals(taskId, payload.get("taskId").asText())
    }

    @Test
    @Order(7)
    fun `07 - получение задачи по ID`() {
        mockMvc.get("/api/tasks/$taskId") {
            header("Authorization", "Bearer $accessToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.id") { value(taskId) }
            jsonPath("$.status") { value("PENDING") }
            jsonPath("$.prompt") { value("Сгенерировать 3D-модель стула") }
        }
    }

    @Test
    @Order(8)
    fun `08 - получение списка задач пользователя`() {
        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $accessToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content") { isArray() }
            jsonPath("$.content.length()") { value(1) }
            jsonPath("$.content[0].id") { value(taskId) }
            jsonPath("$.totalElements") { value(1) }
        }
    }

    @Test
    @Order(9)
    fun `09 - создание нескольких задач и проверка списка`() {
        val request2 = CreateTaskRequest(prompt = "Вторая модель")
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request2)
            header("Authorization", "Bearer $accessToken")
        }.andExpect { status { isCreated() } }

        val request3 = CreateTaskRequest(prompt = "Третья модель", s3InputKey = "uploads/input.obj")
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request3)
            header("Authorization", "Bearer $accessToken")
        }.andExpect { status { isCreated() } }

        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $accessToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { value(3) }
            jsonPath("$.totalElements") { value(3) }
        }
    }

    @Test
    @Order(10)
    fun `10 - outbox содержит 3 события после 3 задач`() {
        val count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM outbox_events WHERE event_type = 'TASK_CREATED'",
            Int::class.java
        )
        assertEquals(3, count)
    }

    @Test
    @Order(11)
    fun `11 - запросы без токена возвращают 403`() {
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(CreateTaskRequest(prompt = "test"))
        }.andExpect { status { isForbidden() } }

        mockMvc.get("/api/tasks").andExpect { status { isForbidden() } }

        mockMvc.get("/api/tasks/$taskId").andExpect { status { isForbidden() } }
    }

    @Test
    @Order(12)
    fun `12 - health и actuator доступны без авторизации`() {
        mockMvc.get("/health").andExpect { status { isOk() } }
        mockMvc.get("/actuator/health").andExpect { status { isOk() } }
    }

    @Test
    @Order(13)
    fun `13 - swagger доступен и содержит эндпоинты задач`() {
        mockMvc.get("/v3/api-docs").andExpect {
            status { isOk() }
            jsonPath("$.paths./api/tasks") { exists() }
            jsonPath("$.paths./api/tasks/{id}") { exists() }
            jsonPath("$.paths./auth/register") { exists() }
            jsonPath("$.paths./auth/login") { exists() }
        }
    }

    @Test
    @Order(14)
    fun `14 - задача и пользователь связаны в БД`() {
        val task = jdbcTemplate.queryForMap(
            "SELECT t.*, u.email FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.id = ?",
            java.util.UUID.fromString(taskId)
        )
        assertEquals(TEST_EMAIL, task["email"])
        assertEquals("PENDING", task["status"])
    }

    @Test
    @Order(15)
    fun `15 - prometheus метрики доступны`() {
        mockMvc.get("/actuator/prometheus").andExpect {
            status { isOk() }
        }
    }
}
