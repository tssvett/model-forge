package com.modelforge.service

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import java.util.UUID

class JwtServiceTest {

    private val jwtService = JwtService(
        secret = "test-secret-key-minimum-32-characters-long!!",
        expirationHours = 1
    )

    @Test
    fun `generateToken returns valid JWT`() {
        val userId = UUID.randomUUID()
        val email = "test@example.com"

        val token = jwtService.generateToken(userId, email)

        assertNotNull(token)
        assertTrue(token.split(".").size == 3)
    }

    @Test
    fun `validateToken returns claims for valid token`() {
        val userId = UUID.randomUUID()
        val email = "test@example.com"
        val token = jwtService.generateToken(userId, email)

        val claims = jwtService.validateToken(token)

        assertNotNull(claims)
        assertEquals(userId, jwtService.getUserId(claims!!))
        assertEquals(email, jwtService.getEmail(claims))
    }

    @Test
    fun `validateToken returns null for invalid token`() {
        val claims = jwtService.validateToken("invalid.token.here")

        assertNull(claims)
    }

    @Test
    fun `validateToken returns null for tampered token`() {
        val token = jwtService.generateToken(UUID.randomUUID(), "test@example.com")
        val tampered = token.dropLast(5) + "XXXXX"

        val claims = jwtService.validateToken(tampered)

        assertNull(claims)
    }

    @Test
    fun `getExpirationSeconds returns correct value`() {
        assertEquals(3600, jwtService.getExpirationSeconds())
    }
}
