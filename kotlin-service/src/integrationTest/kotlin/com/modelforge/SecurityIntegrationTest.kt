package com.modelforge

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.config.TestKafkaConfig
import com.modelforge.dto.RegisterRequest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.http.MediaType
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.get

/**
 * E2E тесты безопасности: JWT, доступ к защищённым и публичным ресурсам.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@ActiveProfiles("integration")
@Import(TestKafkaConfig::class)
class SecurityIntegrationTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var objectMapper: ObjectMapper

    @Test
    fun `защищённые эндпоинты недоступны без токена`() {
        mockMvc.get("/api/tasks").andExpect { status { isForbidden() } }
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = "{}"
        }.andExpect { status { isForbidden() } }
    }

    @Test
    fun `защищённые эндпоинты недоступны с невалидным токеном`() {
        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer invalid-token-123")
        }.andExpect { status { isForbidden() } }
    }

    @Test
    fun `защищённые эндпоинты доступны с валидным токеном`() {
        val email = "security-test-${System.nanoTime()}@example.com"
        val register = RegisterRequest(email = email, password = "password123")

        val result = mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(register)
        }.andReturn()

        val token = objectMapper.readTree(result.response.contentAsString)
            .get("accessToken").asText()

        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $token")
        }.andExpect { status { isOk() } }
    }

    @Test
    fun `публичные эндпоинты доступны без токена`() {
        mockMvc.get("/health").andExpect { status { isOk() } }
        mockMvc.get("/actuator/health").andExpect { status { isOk() } }
        mockMvc.get("/swagger-ui/index.html").andExpect { status { isOk() } }
        mockMvc.get("/v3/api-docs").andExpect { status { isOk() } }
    }

    @Test
    fun `auth эндпоинты доступны без токена`() {
        val register = RegisterRequest(
            email = "auth-public-${System.nanoTime()}@example.com",
            password = "password123"
        )

        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(register)
        }.andExpect { status { isCreated() } }
    }

    @Test
    fun `пользователь видит только свои задачи`() {
        // Регистрируем двух пользователей
        val email1 = "user1-${System.nanoTime()}@example.com"
        val email2 = "user2-${System.nanoTime()}@example.com"

        val token1 = registerAndGetToken(email1)
        val token2 = registerAndGetToken(email2)

        // User1 создаёт задачу
        mockMvc.post("/api/tasks") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"prompt":"задача user1"}"""
            header("Authorization", "Bearer $token1")
        }.andExpect { status { isCreated() } }

        // User2 видит пустой список
        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $token2")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { value(0) }
            jsonPath("$.totalElements") { value(0) }
        }

        // User1 видит свою задачу
        mockMvc.get("/api/tasks") {
            header("Authorization", "Bearer $token1")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { value(1) }
            jsonPath("$.content[0].prompt") { value("задача user1") }
        }
    }

    private fun registerAndGetToken(email: String): String {
        val result = mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(
                RegisterRequest(email = email, password = "password123")
            )
        }.andReturn()

        return objectMapper.readTree(result.response.contentAsString)
            .get("accessToken").asText()
    }
}
