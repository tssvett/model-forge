package com.modelforge.controller

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.config.TestKafkaConfig
import com.modelforge.dto.RegisterRequest
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.mock.web.MockMultipartFile
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.multipart
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.get
import java.util.UUID

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Import(TestKafkaConfig::class)
class TaskControllerTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var objectMapper: ObjectMapper

    @Autowired
    lateinit var jdbcTemplate: JdbcTemplate

    private lateinit var authToken: String

    @BeforeEach
    fun setUp() {
        // Регистрируем пользователя и получаем JWT
        val register = RegisterRequest(
            email = "task-test-${System.nanoTime()}@example.com",
            password = "password123"
        )

        val result = mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(register)
        }.andReturn()

        val body = objectMapper.readTree(result.response.contentAsString)
        authToken = body.get("accessToken").asText()
    }

    private fun createTestFile(
        name: String = "test.jpg",
        content: ByteArray = "fake-image-data".toByteArray(),
        contentType: String = "image/jpeg"
    ): MockMultipartFile = MockMultipartFile("file", name, contentType, content)

    private fun createTaskViaMultipart(prompt: String? = null, file: MockMultipartFile = createTestFile()) =
        mockMvc.multipart("/api/tasks") {
            file(file)
            if (prompt != null) param("prompt", prompt)
            header("Authorization", "Bearer $authToken")
        }

    @Test
    fun `POST tasks возвращает 201 с созданной задачей`() {
        createTaskViaMultipart(prompt = "Сгенерировать 3D-модель стула")
            .andExpect {
                status { isCreated() }
                jsonPath("$.id") { exists() }
                jsonPath("$.status") { value("PENDING") }
                jsonPath("$.prompt") { value("Сгенерировать 3D-модель стула") }
                jsonPath("$.s3InputKey") { exists() }
            }
    }

    @Test
    fun `POST tasks возвращает 400 для неподдерживаемого формата`() {
        val file = createTestFile(name = "test.gif", contentType = "image/gif")
        createTaskViaMultipart(file = file)
            .andExpect {
                status { isBadRequest() }
                jsonPath("$.code") { value(400) }
            }
    }

    @Test
    fun `POST tasks возвращает 400 для пустого файла`() {
        val file = MockMultipartFile("file", "empty.jpg", "image/jpeg", ByteArray(0))
        createTaskViaMultipart(file = file)
            .andExpect {
                status { isBadRequest() }
                jsonPath("$.code") { value(400) }
            }
    }

    @Test
    fun `POST tasks возвращает 403 без токена`() {
        val file = createTestFile()
        mockMvc.multipart("/api/tasks") {
            file(file)
        }.andExpect {
            status { isForbidden() }
        }
    }

    @Test
    fun `GET tasks возвращает страницу задач пользователя`() {
        createTaskViaMultipart(prompt = "test-list")

        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content") { isArray() }
            jsonPath("$.content[0].prompt") { value("test-list") }
            jsonPath("$.page") { value(0) }
            jsonPath("$.size") { value(20) }
            jsonPath("$.totalElements") { exists() }
            jsonPath("$.totalPages") { exists() }
        }
    }

    @Test
    fun `GET tasks с параметрами пагинации`() {
        repeat(2) {
            createTaskViaMultipart(prompt = "paged-$it")
        }

        mockMvc.get("/api/tasks?page=0&size=1") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { value(1) }
            jsonPath("$.size") { value(1) }
            jsonPath("$.totalPages") { value(2) }
        }
    }

    @Test
    fun `GET tasks с фильтрацией по статусу`() {
        createTaskViaMultipart(prompt = "filter-test")

        mockMvc.get("/api/tasks?status=COMPLETED") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content") { isArray() }
            jsonPath("$.content.length()") { value(0) }
            jsonPath("$.totalElements") { value(0) }
        }

        mockMvc.get("/api/tasks?status=PENDING") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { exists() }
        }
    }

    @Test
    fun `GET tasks по ID возвращает задачу`() {
        val createResult = createTaskViaMultipart(prompt = "test-get-by-id").andReturn()

        val taskId = objectMapper.readTree(createResult.response.contentAsString).get("id").asText()

        mockMvc.get("/api/tasks/$taskId") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$.id") { value(taskId) }
            jsonPath("$.prompt") { value("test-get-by-id") }
        }
    }

    @Test
    fun `GET tasks возвращает 403 без токена`() {
        mockMvc.get("/api/tasks").andExpect {
            status { isForbidden() }
        }
    }

    @Test
    fun `GET tasks download возвращает 403 без токена`() {
        mockMvc.get("/api/tasks/${UUID.randomUUID()}/download").andExpect {
            status { isForbidden() }
        }
    }

    @Test
    fun `GET tasks download возвращает 409 для незавершённой задачи`() {
        val createResult = createTaskViaMultipart(prompt = "test-download-pending").andReturn()

        val taskId = objectMapper.readTree(createResult.response.contentAsString).get("id").asText()

        mockMvc.get("/api/tasks/$taskId/download") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isConflict() }
            jsonPath("$.code") { value(409) }
        }
    }

    @Test
    fun `GET tasks download возвращает 404 для несуществующей задачи`() {
        mockMvc.get("/api/tasks/${UUID.randomUUID()}/download") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isNotFound() }
            jsonPath("$.code") { value(404) }
        }
    }
}
