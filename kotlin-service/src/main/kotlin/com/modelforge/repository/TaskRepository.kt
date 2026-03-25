package com.modelforge.repository

import com.modelforge.entity.Task
import com.modelforge.entity.TaskStatus
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.stereotype.Repository
import java.sql.ResultSet
import java.util.UUID

@Repository
class TaskRepository(private val jdbcTemplate: JdbcTemplate) {

    private val rowMapper = RowMapper { rs: ResultSet, _: Int ->
        Task(
            id = UUID.fromString(rs.getString("id")),
            userId = UUID.fromString(rs.getString("user_id")),
            status = TaskStatus.valueOf(rs.getString("status")),
            prompt = rs.getString("prompt"),
            s3InputKey = rs.getString("s3_input_key"),
            s3OutputKey = rs.getString("s3_output_key"),
            createdAt = rs.getTimestamp("created_at").toInstant(),
            updatedAt = rs.getTimestamp("updated_at").toInstant()
        )
    }

    fun save(task: Task): Task {
        jdbcTemplate.update(
            """INSERT INTO tasks (id, user_id, status, prompt, s3_input_key, s3_output_key, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            task.id, task.userId, task.status.name, task.prompt,
            task.s3InputKey, task.s3OutputKey,
            java.sql.Timestamp.from(task.createdAt),
            java.sql.Timestamp.from(task.updatedAt)
        )
        return task
    }

    fun findById(id: UUID): Task? {
        val tasks = jdbcTemplate.query(
            "SELECT * FROM tasks WHERE id = ?",
            rowMapper, id
        )
        return tasks.firstOrNull()
    }

    fun findByUserId(userId: UUID): List<Task> {
        return jdbcTemplate.query(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
            rowMapper, userId
        )
    }

    fun findByUserIdPaged(userId: UUID, status: TaskStatus?, offset: Long, limit: Int): List<Task> {
        val sql = StringBuilder("SELECT * FROM tasks WHERE user_id = ?")
        val params = mutableListOf<Any>(userId)

        if (status != null) {
            sql.append(" AND status = ?")
            params.add(status.name)
        }

        sql.append(" ORDER BY created_at DESC LIMIT ? OFFSET ?")
        params.add(limit)
        params.add(offset)

        return jdbcTemplate.query(sql.toString(), rowMapper, *params.toTypedArray())
    }

    fun countByUserId(userId: UUID, status: TaskStatus?): Long {
        val sql = StringBuilder("SELECT COUNT(*) FROM tasks WHERE user_id = ?")
        val params = mutableListOf<Any>(userId)

        if (status != null) {
            sql.append(" AND status = ?")
            params.add(status.name)
        }

        return jdbcTemplate.queryForObject(sql.toString(), Long::class.java, *params.toTypedArray())!!
    }

    fun updateStatus(id: UUID, status: TaskStatus) {
        jdbcTemplate.update(
            "UPDATE tasks SET status = ?, updated_at = NOW() WHERE id = ?",
            status.name, id
        )
    }
}
