package com.modelforge.controller

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.dto.RegisterRequest
import com.modelforge.dto.LoginRequest
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.http.MediaType
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.get

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthControllerTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var objectMapper: ObjectMapper

    @Test
    fun `register returns 201 with JWT token`() {
        val request = RegisterRequest(email = "new@example.com", password = "password123")

        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isCreated() }
            jsonPath("$.accessToken") { exists() }
            jsonPath("$.tokenType") { value("Bearer") }
            jsonPath("$.expiresIn") { exists() }
        }
    }

    @Test
    fun `register returns 400 for duplicate email`() {
        val request = RegisterRequest(email = "duplicate@example.com", password = "password123")

        // Первая регистрация
        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect { status { isCreated() } }

        // Дубликат
        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isBadRequest() }
            jsonPath("$.code") { value(400) }
        }
    }

    @Test
    fun `register returns 400 for invalid email`() {
        val request = mapOf("email" to "not-an-email", "password" to "password123")

        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isBadRequest() }
        }
    }

    @Test
    fun `register returns 400 for short password`() {
        val request = mapOf("email" to "test@example.com", "password" to "123")

        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(request)
        }.andExpect {
            status { isBadRequest() }
        }
    }

    @Test
    fun `login returns 200 with JWT token`() {
        val register = RegisterRequest(email = "login-test@example.com", password = "password123")
        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(register)
        }

        val login = LoginRequest(email = "login-test@example.com", password = "password123")
        mockMvc.post("/auth/login") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(login)
        }.andExpect {
            status { isOk() }
            jsonPath("$.accessToken") { exists() }
            jsonPath("$.tokenType") { value("Bearer") }
        }
    }

    @Test
    fun `login returns 400 for wrong password`() {
        val register = RegisterRequest(email = "login-wrong@example.com", password = "password123")
        mockMvc.post("/auth/register") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(register)
        }

        val login = LoginRequest(email = "login-wrong@example.com", password = "wrong-password")
        mockMvc.post("/auth/login") {
            contentType = MediaType.APPLICATION_JSON
            content = objectMapper.writeValueAsString(login)
        }.andExpect {
            status { isBadRequest() }
        }
    }

    @Test
    fun `protected endpoint returns 403 without token`() {
        mockMvc.get("/api/tasks").andExpect {
            status { isForbidden() }
        }
    }

    @Test
    fun `health endpoint is public`() {
        mockMvc.get("/health").andExpect {
            status { isOk() }
        }
    }

    @Test
    fun `actuator health is public`() {
        mockMvc.get("/actuator/health").andExpect {
            status { isOk() }
        }
    }
}
