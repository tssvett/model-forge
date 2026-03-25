package com.modelforge.controller

import com.modelforge.dto.CreateTaskRequest
import com.modelforge.dto.ErrorResponse
import com.modelforge.dto.TaskResponse
import com.modelforge.service.TaskService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.media.ArraySchema
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import io.swagger.v3.oas.annotations.responses.ApiResponses
import io.swagger.v3.oas.annotations.tags.Tag
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.security.core.Authentication
import org.springframework.web.bind.annotation.*
import java.util.UUID

@RestController
@RequestMapping("/api/tasks")
@Tag(name = "Tasks", description = "Управление задачами генерации 3D-моделей")
class TaskController(
    private val taskService: TaskService
) {

    @PostMapping
    @Operation(summary = "Создать задачу на генерацию")
    @ApiResponses(
        ApiResponse(responseCode = "201", description = "Задача создана",
            content = [Content(schema = Schema(implementation = TaskResponse::class))]),
        ApiResponse(responseCode = "400", description = "Некорректные данные",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "403", description = "Не авторизован")
    )
    fun createTask(
        @RequestBody request: CreateTaskRequest,
        authentication: Authentication
    ): ResponseEntity<TaskResponse> {
        val userId = authentication.principal as UUID
        val response = taskService.createTask(userId, request)
        return ResponseEntity.status(HttpStatus.CREATED).body(response)
    }

    @GetMapping("/{id}")
    @Operation(summary = "Получить задачу по ID")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Задача найдена",
            content = [Content(schema = Schema(implementation = TaskResponse::class))]),
        ApiResponse(responseCode = "400", description = "Задача не найдена",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "403", description = "Не авторизован")
    )
    fun getTask(
        @PathVariable id: UUID,
        authentication: Authentication
    ): ResponseEntity<TaskResponse> {
        val userId = authentication.principal as UUID
        val response = taskService.getTask(id, userId)
        return ResponseEntity.ok(response)
    }

    @GetMapping
    @Operation(summary = "Получить все задачи текущего пользователя")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Список задач",
            content = [Content(array = ArraySchema(schema = Schema(implementation = TaskResponse::class)))]),
        ApiResponse(responseCode = "403", description = "Не авторизован")
    )
    fun getUserTasks(authentication: Authentication): ResponseEntity<List<TaskResponse>> {
        val userId = authentication.principal as UUID
        val response = taskService.getUserTasks(userId)
        return ResponseEntity.ok(response)
    }
}
