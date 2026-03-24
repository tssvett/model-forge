package com.modelforge.service

import com.modelforge.dto.LoginRequest
import com.modelforge.dto.RegisterRequest
import com.modelforge.entity.User
import com.modelforge.repository.UserRepository
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.junit.jupiter.api.extension.ExtendWith
import org.mockito.InjectMocks
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.junit.jupiter.MockitoExtension
import org.springframework.security.crypto.password.PasswordEncoder

@ExtendWith(MockitoExtension::class)
class AuthServiceTest {

    @Mock
    lateinit var userRepository: UserRepository

    @Mock
    lateinit var passwordEncoder: PasswordEncoder

    @Mock
    lateinit var jwtService: JwtService

    @InjectMocks
    lateinit var authService: AuthService

    @Test
    fun `register creates user and returns token`() {
        val request = RegisterRequest(email = "test@example.com", password = "password123")

        `when`(userRepository.existsByEmail("test@example.com")).thenReturn(false)
        `when`(passwordEncoder.encode("password123")).thenReturn("hashed")
        `when`(userRepository.save(any())).thenAnswer { it.arguments[0] }
        `when`(jwtService.generateToken(any(), eq("test@example.com"))).thenReturn("jwt-token")
        `when`(jwtService.getExpirationSeconds()).thenReturn(86400)

        val response = authService.register(request)

        assertEquals("jwt-token", response.accessToken)
        assertEquals("Bearer", response.tokenType)
        assertEquals(86400, response.expiresIn)
        verify(userRepository).save(any())
    }

    @Test
    fun `register throws when email already exists`() {
        val request = RegisterRequest(email = "existing@example.com", password = "password123")
        `when`(userRepository.existsByEmail("existing@example.com")).thenReturn(true)

        val exception = assertThrows<IllegalArgumentException> {
            authService.register(request)
        }

        assertTrue(exception.message!!.contains("уже существует"))
    }

    @Test
    fun `login returns token for valid credentials`() {
        val request = LoginRequest(email = "test@example.com", password = "password123")
        val user = User(email = "test@example.com", passwordHash = "hashed")

        `when`(userRepository.findByEmail("test@example.com")).thenReturn(user)
        `when`(passwordEncoder.matches("password123", "hashed")).thenReturn(true)
        `when`(jwtService.generateToken(eq(user.id), eq("test@example.com"))).thenReturn("jwt-token")
        `when`(jwtService.getExpirationSeconds()).thenReturn(86400)

        val response = authService.login(request)

        assertEquals("jwt-token", response.accessToken)
    }

    @Test
    fun `login throws for wrong email`() {
        val request = LoginRequest(email = "wrong@example.com", password = "password123")
        `when`(userRepository.findByEmail("wrong@example.com")).thenReturn(null)

        val exception = assertThrows<IllegalArgumentException> {
            authService.login(request)
        }

        assertTrue(exception.message!!.contains("Неверный"))
    }

    @Test
    fun `login throws for wrong password`() {
        val request = LoginRequest(email = "test@example.com", password = "wrong")
        val user = User(email = "test@example.com", passwordHash = "hashed")

        `when`(userRepository.findByEmail("test@example.com")).thenReturn(user)
        `when`(passwordEncoder.matches("wrong", "hashed")).thenReturn(false)

        val exception = assertThrows<IllegalArgumentException> {
            authService.login(request)
        }

        assertTrue(exception.message!!.contains("Неверный"))
    }
}
