package com.modelforge.service

import com.modelforge.dto.AuthResponse
import com.modelforge.dto.LoginRequest
import com.modelforge.dto.RegisterRequest
import com.modelforge.entity.User
import com.modelforge.repository.UserRepository
import org.slf4j.LoggerFactory
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service

@Service
class AuthService(
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,
    private val jwtService: JwtService
) {

    private val logger = LoggerFactory.getLogger(AuthService::class.java)

    fun register(request: RegisterRequest): AuthResponse {
        if (userRepository.existsByEmail(request.email)) {
            throw IllegalArgumentException("Пользователь с email ${request.email} уже существует")
        }

        val user = User(
            email = request.email,
            passwordHash = passwordEncoder.encode(request.password)
        )

        userRepository.save(user)
        logger.info("Зарегистрирован пользователь: ${user.email}")

        return createAuthResponse(user)
    }

    fun login(request: LoginRequest): AuthResponse {
        val user = userRepository.findByEmail(request.email)
            ?: throw IllegalArgumentException("Неверный email или пароль")

        if (!passwordEncoder.matches(request.password, user.passwordHash)) {
            throw IllegalArgumentException("Неверный email или пароль")
        }

        logger.info("Авторизован пользователь: ${user.email}")
        return createAuthResponse(user)
    }

    private fun createAuthResponse(user: User): AuthResponse {
        val token = jwtService.generateToken(user.id, user.email)
        return AuthResponse(
            accessToken = token,
            expiresIn = jwtService.getExpirationSeconds()
        )
    }
}
