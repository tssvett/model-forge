package com.modelforge.controller

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.dto.ErrorResponse
import com.modelforge.dto.GenerationMetricsResponse
import com.modelforge.dto.PagedResponse
import com.modelforge.dto.TaskResponse
import com.modelforge.entity.TaskStatus
import com.modelforge.service.TaskService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import io.swagger.v3.oas.annotations.responses.ApiResponses
import io.swagger.v3.oas.annotations.tags.Tag
import jakarta.servlet.http.HttpServletResponse
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.security.core.Authentication
import org.springframework.web.bind.annotation.*
import org.springframework.web.multipart.MultipartFile
import java.util.UUID

@RestController
@RequestMapping("/api/tasks")
@Tag(name = "Tasks", description = "Управление задачами генерации 3D-моделей")
class TaskController(
    private val taskService: TaskService,
    private val objectMapper: ObjectMapper
) {

    @PostMapping(consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
    @Operation(summary = "Создать задачу на генерацию")
    @ApiResponses(
        ApiResponse(responseCode = "201", description = "Задача создана",
            content = [Content(schema = Schema(implementation = TaskResponse::class))]),
        ApiResponse(responseCode = "400", description = "Некорректный файл (размер/формат)",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "403", description = "Не авторизован"),
        ApiResponse(responseCode = "500", description = "Внутренняя ошибка сервера",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))])
    )
    fun createTask(
        @RequestParam("file") file: MultipartFile,
        @RequestParam("prompt", required = false) prompt: String?,
        authentication: Authentication
    ): ResponseEntity<TaskResponse> {
        val userId = authentication.principal as UUID
        val response = taskService.createTask(userId, file, prompt)
        return ResponseEntity.status(HttpStatus.CREATED).body(response)
    }

    @GetMapping("/{id}")
    @Operation(summary = "Получить задачу по ID")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Задача найдена",
            content = [Content(schema = Schema(implementation = TaskResponse::class))]),
        ApiResponse(responseCode = "404", description = "Задача не найдена",
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
    @Operation(
        summary = "Получить задачи текущего пользователя (с пагинацией)",
        description = "Возвращает список задач с пагинацией и опциональной фильтрацией по статусу"
    )
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Страница задач",
            content = [Content(schema = Schema(implementation = PagedResponse::class))]),
        ApiResponse(responseCode = "400", description = "Некорректные параметры",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "403", description = "Не авторизован")
    )
    fun getUserTasks(
        @RequestParam(defaultValue = "0") page: Int,
        @RequestParam(defaultValue = "20") size: Int,
        @RequestParam(required = false) status: TaskStatus?,
        authentication: Authentication
    ): ResponseEntity<PagedResponse<TaskResponse>> {
        val effectiveSize = size.coerceIn(1, 100)
        val userId = authentication.principal as UUID
        val response = taskService.getUserTasksPaged(userId, page, effectiveSize, status)
        return ResponseEntity.ok(response)
    }

    @GetMapping("/{id}/metrics")
    @Operation(summary = "Получить метрики генерации")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Метрики найдены",
            content = [Content(schema = Schema(implementation = GenerationMetricsResponse::class))]),
        ApiResponse(responseCode = "404", description = "Задача или метрики не найдены",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "403", description = "Не авторизован")
    )
    fun getTaskMetrics(
        @PathVariable id: UUID,
        authentication: Authentication
    ): ResponseEntity<GenerationMetricsResponse> {
        val userId = authentication.principal as UUID
        val response = taskService.getTaskMetrics(id, userId)
        return ResponseEntity.ok(response)
    }

    @GetMapping("/{id}/download")
    @Operation(summary = "Скачать сгенерированную 3D-модель")
    @ApiResponses(
        ApiResponse(responseCode = "200", description = "Файл модели (multipart/form-data: metadata + model)"),
        ApiResponse(responseCode = "403", description = "Нет доступа к задаче",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "404", description = "Задача не найдена",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))]),
        ApiResponse(responseCode = "409", description = "Задача ещё не завершена",
            content = [Content(schema = Schema(implementation = ErrorResponse::class))])
    )
    fun downloadTask(
        @PathVariable id: UUID,
        authentication: Authentication,
        response: HttpServletResponse
    ) {
        val userId = authentication.principal as UUID
        val result = taskService.downloadTask(id, userId)

        val boundary = "boundary-${UUID.randomUUID().toString().replace("-", "")}"
        response.contentType = "${MediaType.MULTIPART_FORM_DATA_VALUE}; boundary=$boundary"
        response.status = HttpServletResponse.SC_OK

        val out = response.outputStream

        // Part 1: metadata JSON
        val metadata = objectMapper.writeValueAsBytes(
            mapOf(
                "task_id" to result.taskId.toString(),
                "format" to result.format,
                "generated_at" to result.generatedAt.toString()
            )
        )
        out.write("--$boundary\r\n".toByteArray())
        out.write("Content-Type: ${MediaType.APPLICATION_JSON_VALUE}\r\n".toByteArray())
        out.write("Content-Disposition: form-data; name=\"metadata\"\r\n\r\n".toByteArray())
        out.write(metadata)
        out.write("\r\n".toByteArray())

        // Part 2: binary model file
        out.write("--$boundary\r\n".toByteArray())
        out.write("Content-Type: ${MediaType.APPLICATION_OCTET_STREAM_VALUE}\r\n".toByteArray())
        out.write("Content-Disposition: form-data; name=\"model\"; filename=\"model.${result.format}\"\r\n\r\n".toByteArray())
        out.write(result.fileBytes)
        out.write("\r\n".toByteArray())

        out.write("--$boundary--\r\n".toByteArray())
        out.flush()
    }
}
