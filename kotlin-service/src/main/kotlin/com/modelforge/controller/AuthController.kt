package com.modelforge.controller

import com.modelforge.dto.AuthResponse
import com.modelforge.dto.ErrorResponse
import com.modelforge.dto.LoginRequest
import com.modelforge.dto.RegisterRequest
import com.modelforge.service.AuthService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import io.swagger.v3.oas.annotations.responses.ApiResponses
import io.swagger.v3.oas.annotations.security.SecurityRequirements
import io.swagger.v3.oas.annotations.tags.Tag
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/auth")
@Tag(name = "Auth", description = "Регистрация и аутентификация")
@SecurityRequirements
class AuthController(
    private val authService: AuthService
) {

    @PostMapping("/register")
    @Operation(summary = "Регистрация нового пользователя")
    @ApiResponses(
        ApiResponse(responseCode = "201", description = "Пользователь зарегистрирован",
            content = [Content(schema = Schema(implementation = AuthResponse::class))]),
        ApiResponse(responseCode = "400", description = "Некорректные данные или email занят",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))])
    )
    fun register(@Valid @RequestBody request: RegisterRequest): ResponseEntity<AuthResponse> {
        val response = authService.register(request)
        return ResponseEntity.status(HttpStatus.CREATED).body(response)
    }

    @PostMapping("/login")
    @Operation(summary = "Аутентификация пользователя")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Успешная аутентификация",
            content = [Content(schema = Schema(implementation = AuthResponse::class))]),
        ApiResponse(responseCode = "400", description = "Неверный email или пароль",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))])
    )
    fun login(@Valid @RequestBody request: LoginRequest): ResponseEntity<AuthResponse> {
        val response = authService.login(request)
        return ResponseEntity.ok(response)
    }
}
