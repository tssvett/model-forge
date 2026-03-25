package com.modelforge.dto

import jakarta.validation.constraints.Email
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size

data class RegisterRequest(
    @field:NotBlank(message = "Email обязателен")
    @field:Email(message = "Некорректный формат email")
    val email: String,

    @field:NotBlank(message = "Пароль обязателен")
    @field:Size(min = 6, max = 100, message = "Пароль должен быть от 6 до 100 символов")
    val password: String
)

data class LoginRequest(
    @field:NotBlank(message = "Email обязателен")
    @field:Email(message = "Некорректный формат email")
    val email: String,

    @field:NotBlank(message = "Пароль обязателен")
    val password: String
)

data class AuthResponse(
    val accessToken: String,
    val tokenType: String = "Bearer",
    val expiresIn: Long
)

data class ErrorResponse(
    val code: Int,
    val message: String,
    val timestamp: String = java.time.Instant.now().toString()
)
