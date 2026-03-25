package com.modelforge.controller

import com.modelforge.dto.ErrorResponse
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice

@RestControllerAdvice
class GlobalExceptionHandler {

    private val logger = LoggerFactory.getLogger(GlobalExceptionHandler::class.java)

    @ExceptionHandler(IllegalArgumentException::class)
    fun handleBadRequest(e: IllegalArgumentException): ResponseEntity<ErrorResponse> {
        logger.warn("Bad request: ${e.message}")
        return ResponseEntity.badRequest().body(
            ErrorResponse(code = 400, message = e.message ?: "Bad Request")
        )
    }

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(e: MethodArgumentNotValidException): ResponseEntity<ErrorResponse> {
        val message = e.bindingResult.fieldErrors
            .joinToString("; ") { "${it.field}: ${it.defaultMessage}" }
        logger.warn("Validation error: $message")
        return ResponseEntity.badRequest().body(
            ErrorResponse(code = 400, message = message)
        )
    }

    @ExceptionHandler(Exception::class)
    fun handleInternal(e: Exception): ResponseEntity<ErrorResponse> {
        logger.error("Internal error", e)
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(
            ErrorResponse(code = 500, message = "Internal Server Error")
        )
    }
}
