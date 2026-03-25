package com.modelforge.controller

import com.modelforge.dto.ErrorResponse
import com.modelforge.exception.InvalidFileException
import com.modelforge.exception.TaskAccessDeniedException
import com.modelforge.exception.TaskNotFoundException
import com.modelforge.exception.TaskNotCompletedException
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.multipart.MaxUploadSizeExceededException

@RestControllerAdvice
class GlobalExceptionHandler {

    private val logger = LoggerFactory.getLogger(GlobalExceptionHandler::class.java)

    @ExceptionHandler(TaskNotFoundException::class)
    fun handleNotFound(e: TaskNotFoundException): ResponseEntity<ErrorResponse> {
        logger.warn("Not found: ${e.message}")
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(
            ErrorResponse(code = 404, message = e.message ?: "Not Found")
        )
    }

    @ExceptionHandler(TaskAccessDeniedException::class)
    fun handleForbidden(e: TaskAccessDeniedException): ResponseEntity<ErrorResponse> {
        logger.warn("Access denied: ${e.message}")
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(
            ErrorResponse(code = 403, message = e.message ?: "Forbidden")
        )
    }

    @ExceptionHandler(TaskNotCompletedException::class)
    fun handleConflict(e: TaskNotCompletedException): ResponseEntity<ErrorResponse> {
        logger.warn("Task not completed: ${e.message}")
        return ResponseEntity.status(HttpStatus.CONFLICT).body(
            ErrorResponse(code = 409, message = e.message ?: "Conflict")
        )
    }

    @ExceptionHandler(InvalidFileException::class)
    fun handleInvalidFile(e: InvalidFileException): ResponseEntity<ErrorResponse> {
        logger.warn("Invalid file: ${e.message}")
        return ResponseEntity.badRequest().body(
            ErrorResponse(code = 400, message = e.message ?: "Invalid file")
        )
    }

    @ExceptionHandler(MaxUploadSizeExceededException::class)
    fun handleMaxUploadSize(e: MaxUploadSizeExceededException): ResponseEntity<ErrorResponse> {
        logger.warn("File too large: ${e.message}")
        return ResponseEntity.badRequest().body(
            ErrorResponse(code = 400, message = "Файл превышает максимальный размер 10 МБ")
        )
    }

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
