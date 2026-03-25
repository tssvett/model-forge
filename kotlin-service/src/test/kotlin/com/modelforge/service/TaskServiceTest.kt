package com.modelforge.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.modelforge.dto.CreateTaskRequest
import com.modelforge.entity.OutboxEvent
import com.modelforge.entity.Task
import com.modelforge.entity.TaskStatus
import com.modelforge.exception.TaskAccessDeniedException
import com.modelforge.exception.TaskNotFoundException
import com.modelforge.exception.TaskNotCompletedException
import com.modelforge.repository.OutboxRepository
import com.modelforge.repository.TaskRepository
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.mockito.kotlin.*
import java.util.UUID

class TaskServiceTest {

    private val taskRepository: TaskRepository = mock()
    private val outboxRepository: OutboxRepository = mock()
    private val objectMapper = ObjectMapper().findAndRegisterModules()
    private val minioService: MinioService = mock()

    private val taskService = TaskService(taskRepository, outboxRepository, objectMapper, minioService)

    private val userId = UUID.randomUUID()

    @Test
    fun `createTask сохраняет задачу и outbox событие`() {
        val request = CreateTaskRequest(prompt = "Сгенерировать 3D-модель")

        whenever(taskRepository.save(any())).thenAnswer { it.arguments[0] as Task }
        whenever(outboxRepository.save(any())).thenAnswer { it.arguments[0] as OutboxEvent }

        val response = taskService.createTask(userId, request)

        assertEquals(userId, response.userId)
        assertEquals(TaskStatus.PENDING, response.status)
        assertEquals("Сгенерировать 3D-модель", response.prompt)

        verify(taskRepository).save(any())
        verify(outboxRepository).save(any())
    }

    @Test
    fun `createTask создает outbox событие с типом TASK_CREATED`() {
        val request = CreateTaskRequest(prompt = "test")

        whenever(taskRepository.save(any())).thenAnswer { it.arguments[0] as Task }
        whenever(outboxRepository.save(any())).thenAnswer { it.arguments[0] as OutboxEvent }

        taskService.createTask(userId, request)

        val captor = argumentCaptor<OutboxEvent>()
        verify(outboxRepository).save(captor.capture())

        assertEquals("TASK_CREATED", captor.firstValue.eventType)
        assertTrue(captor.firstValue.payload.contains("taskId"))
    }

    @Test
    fun `getTask возвращает задачу для владельца`() {
        val taskId = UUID.randomUUID()
        val task = Task(id = taskId, userId = userId, prompt = "test")

        whenever(taskRepository.findById(taskId)).thenReturn(task)

        val response = taskService.getTask(taskId, userId)

        assertEquals(taskId, response.id)
        assertEquals(userId, response.userId)
    }

    @Test
    fun `getTask бросает исключение для несуществующей задачи`() {
        val taskId = UUID.randomUUID()
        whenever(taskRepository.findById(taskId)).thenReturn(null)

        assertThrows<IllegalArgumentException> {
            taskService.getTask(taskId, userId)
        }
    }

    @Test
    fun `getTask бросает исключение для чужой задачи`() {
        val taskId = UUID.randomUUID()
        val otherUserId = UUID.randomUUID()
        val task = Task(id = taskId, userId = otherUserId, prompt = "test")

        whenever(taskRepository.findById(taskId)).thenReturn(task)

        assertThrows<IllegalArgumentException> {
            taskService.getTask(taskId, userId)
        }
    }

    @Test
    fun `getUserTasks возвращает список задач пользователя`() {
        val tasks = listOf(
            Task(userId = userId, prompt = "task1"),
            Task(userId = userId, prompt = "task2")
        )

        whenever(taskRepository.findByUserId(userId)).thenReturn(tasks)

        val response = taskService.getUserTasks(userId)

        assertEquals(2, response.size)
    }

    @Test
    fun `downloadTask возвращает файл для завершённой задачи`() {
        val taskId = UUID.randomUUID()
        val fileBytes = "fake-model-data".toByteArray()
        val task = Task(
            id = taskId,
            userId = userId,
            status = TaskStatus.COMPLETED,
            s3OutputKey = "output/model.obj"
        )

        whenever(taskRepository.findById(taskId)).thenReturn(task)
        whenever(minioService.downloadFile("output/model.obj")).thenReturn(fileBytes)
        whenever(minioService.getFileFormat("output/model.obj")).thenReturn("obj")

        val result = taskService.downloadTask(taskId, userId)

        assertEquals(taskId, result.taskId)
        assertArrayEquals(fileBytes, result.fileBytes)
        assertEquals("obj", result.format)
        verify(minioService).downloadFile("output/model.obj")
    }

    @Test
    fun `downloadTask бросает TaskNotFoundException для несуществующей задачи`() {
        val taskId = UUID.randomUUID()
        whenever(taskRepository.findById(taskId)).thenReturn(null)

        assertThrows<TaskNotFoundException> {
            taskService.downloadTask(taskId, userId)
        }
    }

    @Test
    fun `downloadTask бросает TaskAccessDeniedException для чужой задачи`() {
        val taskId = UUID.randomUUID()
        val task = Task(id = taskId, userId = UUID.randomUUID(), status = TaskStatus.COMPLETED)

        whenever(taskRepository.findById(taskId)).thenReturn(task)

        assertThrows<TaskAccessDeniedException> {
            taskService.downloadTask(taskId, userId)
        }
    }

    @Test
    fun `downloadTask бросает TaskNotCompletedException для незавершённой задачи`() {
        val taskId = UUID.randomUUID()
        val task = Task(id = taskId, userId = userId, status = TaskStatus.PENDING)

        whenever(taskRepository.findById(taskId)).thenReturn(task)

        assertThrows<TaskNotCompletedException> {
            taskService.downloadTask(taskId, userId)
        }
    }
}
