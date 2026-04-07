package com.modelforge.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.dto.GenerationMetricsResponse
import com.modelforge.dto.PagedResponse
import com.modelforge.dto.TaskAnalyticsSummaryResponse
import com.modelforge.dto.TaskCreatedEvent
import com.modelforge.dto.TaskDownloadResult
import com.modelforge.dto.TaskResponse
import com.modelforge.dto.TaskTimelineEntry
import com.modelforge.dto.TaskTimelineResponse
import com.modelforge.dto.TaskWithMetricsResponse
import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.Task
import com.modelforge.exception.InvalidFileException
import com.modelforge.exception.TaskAccessDeniedException
import com.modelforge.exception.TaskNotFoundException
import com.modelforge.exception.TaskNotCompletedException
import com.modelforge.repository.GenerationMetricsRepository
import com.modelforge.repository.OutboxRepository
import com.modelforge.repository.TaskRepository
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.multipart.MultipartFile
import com.modelforge.entity.TaskStatus
import java.util.UUID

@Service
class TaskService(
    private val taskRepository: TaskRepository,
    private val outboxRepository: OutboxRepository,
    private val generationMetricsRepository: GenerationMetricsRepository,
    private val objectMapper: ObjectMapper,
    private val minioService: MinioService
) {

    private val logger = LoggerFactory.getLogger(TaskService::class.java)

    companion object {
        private const val MAX_FILE_SIZE = 10L * 1024 * 1024 // 10 MB
        private val ALLOWED_EXTENSIONS = setOf("jpg", "jpeg", "png", "webp")
    }

    @Transactional
    fun createTask(userId: UUID, file: MultipartFile, prompt: String?): TaskResponse {
        validateFile(file)

        val extension = file.originalFilename?.substringAfterLast('.', "")?.lowercase() ?: ""
        val s3Key = "uploads/${UUID.randomUUID()}.$extension"

        minioService.uploadFile(s3Key, file.inputStream, file.size, file.contentType ?: "application/octet-stream")

        val task = Task(
            userId = userId,
            prompt = prompt,
            s3InputKey = s3Key
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

    private fun validateFile(file: MultipartFile) {
        if (file.isEmpty) {
            throw InvalidFileException("Файл не может быть пустым")
        }

        if (file.size > MAX_FILE_SIZE) {
            throw InvalidFileException("Файл превышает максимальный размер 10 МБ")
        }

        val extension = file.originalFilename?.substringAfterLast('.', "")?.lowercase() ?: ""
        if (extension !in ALLOWED_EXTENSIONS) {
            throw InvalidFileException("Неподдерживаемый формат файла: $extension. Допустимые форматы: ${ALLOWED_EXTENSIONS.joinToString(", ")}")
        }
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

    fun getTaskMetrics(taskId: UUID, userId: UUID): GenerationMetricsResponse {
        val task = taskRepository.findById(taskId)
            ?: throw TaskNotFoundException(taskId)

        if (task.userId != userId) {
            throw TaskAccessDeniedException(taskId)
        }

        val metrics = generationMetricsRepository.findByTaskId(taskId)
            ?: throw TaskNotFoundException(taskId)

        return GenerationMetricsResponse(
            taskId = metrics.taskId,
            chamferDistance = metrics.chamferDistance,
            iou3d = metrics.iou3d,
            fScore = metrics.fScore,
            normalConsistency = metrics.normalConsistency,
            vertices = metrics.vertices,
            faces = metrics.faces,
            inferenceTimeSec = metrics.inferenceTimeSec,
            isMock = metrics.isMock,
            createdAt = metrics.createdAt
        )
    }

    fun getAnalyticsSummary(userId: UUID): TaskAnalyticsSummaryResponse {
        val total = taskRepository.countByUserId(userId, null)
        val completed = taskRepository.countByUserIdAndStatus(userId, TaskStatus.COMPLETED)
        val failed = taskRepository.countByUserIdAndStatus(userId, TaskStatus.FAILED)
        val pending = taskRepository.countByUserIdAndStatus(userId, TaskStatus.PENDING)
        val processing = taskRepository.countByUserIdAndStatus(userId, TaskStatus.PROCESSING)
        val successRate = if (total > 0) completed.toDouble() / total * 100 else 0.0
        val avgMetrics = generationMetricsRepository.getAverageMetricsByUserId(userId)

        return TaskAnalyticsSummaryResponse(
            totalTasks = total,
            completedTasks = completed,
            failedTasks = failed,
            pendingTasks = pending,
            processingTasks = processing,
            successRate = successRate,
            avgInferenceTimeSec = avgMetrics["avg_inference_time"],
            avgChamferDistance = avgMetrics["avg_chamfer_distance"],
            avgIou3d = avgMetrics["avg_iou_3d"],
            avgFScore = avgMetrics["avg_f_score"],
            avgNormalConsistency = avgMetrics["avg_normal_consistency"],
            avgVertices = avgMetrics["avg_vertices"],
            avgFaces = avgMetrics["avg_faces"]
        )
    }

    fun getTaskTimeline(userId: UUID, days: Int): TaskTimelineResponse {
        val effectiveDays = days.coerceIn(1, 365)
        val rows = taskRepository.getTaskTimeline(userId, effectiveDays)
        val entries = rows.map { row ->
            TaskTimelineEntry(
                date = row["date"] as String,
                total = row["total"] as Long,
                completed = row["completed"] as Long,
                failed = row["failed"] as Long
            )
        }
        return TaskTimelineResponse(entries = entries, period = "${effectiveDays}d")
    }

    fun getUserTasksWithMetrics(userId: UUID, page: Int, size: Int, status: TaskStatus?): PagedResponse<TaskWithMetricsResponse> {
        val offset = page.toLong() * size
        val tasks = taskRepository.findByUserIdPaged(userId, status, offset, size)
        val totalElements = taskRepository.countByUserId(userId, status)
        val totalPages = if (totalElements == 0L) 0 else ((totalElements - 1) / size + 1).toInt()

        val content = tasks.map { task ->
            val metrics = generationMetricsRepository.findByTaskId(task.id)
            TaskWithMetricsResponse(
                task = toResponse(task),
                metrics = metrics?.let {
                    GenerationMetricsResponse(
                        taskId = it.taskId,
                        chamferDistance = it.chamferDistance,
                        iou3d = it.iou3d,
                        fScore = it.fScore,
                        normalConsistency = it.normalConsistency,
                        vertices = it.vertices,
                        faces = it.faces,
                        inferenceTimeSec = it.inferenceTimeSec,
                        isMock = it.isMock,
                        createdAt = it.createdAt
                    )
                }
            )
        }

        return PagedResponse(
            content = content,
            page = page,
            size = size,
            totalElements = totalElements,
            totalPages = totalPages
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
