package com.modelforge.controller

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.config.TestKafkaConfig
import com.modelforge.dto.CreateTaskRequest
import com.modelforge.dto.RegisterRequest
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.http.MediaType
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.get

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Import(TestKafkaConfig::class)
class TaskControllerTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var objectMapper: ObjectMapper

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

    @Test
    fun `POST tasks возвращает 201 с созданной задачей`() {
        val request = CreateTaskRequest(prompt = "Сгенерировать 3D-модель стула")

        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isCreated() }
            jsonPath("$.id") { exists() }
            jsonPath("$.status") { value("PENDING") }
            jsonPath("$.prompt") { value("Сгенерировать 3D-модель стула") }
        }
    }

    @Test
    fun `POST tasks возвращает 403 без токена`() {
        val request = CreateTaskRequest(prompt = "test")

        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isForbidden() }
        }
    }

    @Test
    fun `GET tasks возвращает список задач пользователя`() {
        // Создаем задачу
        val request = CreateTaskRequest(prompt = "test-list")
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
            header("Authorization", "Bearer $authToken")
        }

        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $authToken")
        }.andExpect {
            status { isOk() }
            jsonPath("$") { isArray() }
            jsonPath("$[0].prompt") { value("test-list") }
        }
    }

    @Test
    fun `GET tasks по ID возвращает задачу`() {
        val request = CreateTaskRequest(prompt = "test-get-by-id")
        val createResult = mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
            header("Authorization", "Bearer $authToken")
        }.andReturn()

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
}
