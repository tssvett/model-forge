package com.modelforge.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.dto.CreateTaskRequest
import com.modelforge.dto.PagedResponse
import com.modelforge.dto.TaskCreatedEvent
import com.modelforge.dto.TaskDownloadResult
import com.modelforge.dto.TaskResponse
import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.Task
import com.modelforge.exception.TaskAccessDeniedException
import com.modelforge.exception.TaskNotFoundException
import com.modelforge.exception.TaskNotCompletedException
import com.modelforge.repository.OutboxRepository
import com.modelforge.repository.TaskRepository
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import com.modelforge.entity.TaskStatus
import java.util.UUID

@Service
class TaskService(
    private val taskRepository: TaskRepository,
    private val outboxRepository: OutboxRepository,
    private val objectMapper: ObjectMapper,
    private val minioService: MinioService
) {

    private val logger = LoggerFactory.getLogger(TaskService::class.java)

    @Transactional
    fun createTask(userId: UUID, request: CreateTaskRequest): TaskResponse {
        val task = Task(
            userId = userId,
            prompt = request.prompt,
            s3InputKey = request.s3InputKey
        )

        taskRepository.save(task)

        val event = TaskCreatedEvent(
            taskId = task.id,
            userId = task.userId,
            prompt = task.prompt,
            s3InputKey = task.s3InputKey,
            createdAt = task.createdAt
        )

        val outboxEvent = OutboxEvent(
            eventType = "TASK_CREATED",
            payload = objectMapper.writeValueAsString(event)
        )

        outboxRepository.save(outboxEvent)
        logger.info("Создана задача {} с outbox событием {}", task.id, outboxEvent.id)

        return toResponse(task)
    }

    fun getTask(taskId: UUID, userId: UUID): TaskResponse {
        val task = taskRepository.findById(taskId)
            ?: throw IllegalArgumentException("Задача не найдена: $taskId")

        if (task.userId != userId) {
            throw IllegalArgumentException("Нет доступа к задаче: $taskId")
        }

        return toResponse(task)
    }

    fun getUserTasks(userId: UUID): List<TaskResponse> {
        return taskRepository.findByUserId(userId).map { toResponse(it) }
    }

    fun getUserTasksPaged(userId: UUID, page: Int, size: Int, status: TaskStatus?): PagedResponse<TaskResponse> {
        val offset = page.toLong() * size
        val tasks = taskRepository.findByUserIdPaged(userId, status, offset, size)
        val totalElements = taskRepository.countByUserId(userId, status)
        val totalPages = if (totalElements == 0L) 0 else ((totalElements - 1) / size + 1).toInt()

        return PagedResponse(
            content = tasks.map { toResponse(it) },
            page = page,
            size = size,
            totalElements = totalElements,
            totalPages = totalPages
        )
    }

    fun downloadTask(taskId: UUID, userId: UUID): TaskDownloadResult {
        val task = taskRepository.findById(taskId)
            ?: throw TaskNotFoundException(taskId)

        if (task.userId != userId) {
            throw TaskAccessDeniedException(taskId)
        }

        if (task.status != TaskStatus.COMPLETED) {
            throw TaskNotCompletedException(taskId, task.status)
        }

        val outputKey = task.s3OutputKey
            ?: throw IllegalStateException("Task $taskId has no output key")

        val fileBytes = minioService.downloadFile(outputKey)
        val format = minioService.getFileFormat(outputKey)

        logger.info("Downloaded model for task {}, format={}, size={} bytes", taskId, format, fileBytes.size)

        return TaskDownloadResult(
            taskId = taskId,
            fileBytes = fileBytes,
            format = format,
            generatedAt = task.updatedAt
        )
    }

    private fun toResponse(task: Task): TaskResponse {
        return TaskResponse(
            id = task.id,
            userId = task.userId,
            status = task.status,
            prompt = task.prompt,
            s3InputKey = task.s3InputKey,
            s3OutputKey = task.s3OutputKey,
            createdAt = task.createdAt,
            updatedAt = task.updatedAt
        )
    }
}
