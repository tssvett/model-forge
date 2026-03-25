package com.modelforge.exception

import com.modelforge.entity.TaskStatus
import java.util.UUID

class TaskNotFoundException(taskId: UUID) :
    RuntimeException("Task not found: $taskId")

class TaskAccessDeniedException(taskId: UUID) :
    RuntimeException("Access denied to task: $taskId")

class TaskNotCompletedException(taskId: UUID, status: TaskStatus) :
    RuntimeException("Task $taskId is not completed (status: $status)")

class InvalidFileException(message: String) :
    RuntimeException(message)
