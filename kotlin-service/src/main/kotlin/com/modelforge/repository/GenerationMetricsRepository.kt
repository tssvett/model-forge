package com.modelforge.repository

import com.modelforge.entity.GenerationMetrics
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.stereotype.Repository
import java.sql.ResultSet
import java.util.UUID

@Repository
class GenerationMetricsRepository(private val jdbcTemplate: JdbcTemplate) {

    private val rowMapper = RowMapper { rs: ResultSet, _: Int ->
        GenerationMetrics(
            id = UUID.fromString(rs.getString("id")),
            taskId = UUID.fromString(rs.getString("task_id")),
            chamferDistance = rs.getDouble("chamfer_distance").takeUnless { rs.wasNull() },
            iou3d = rs.getDouble("iou_3d").takeUnless { rs.wasNull() },
            fScore = rs.getDouble("f_score").takeUnless { rs.wasNull() },
            normalConsistency = rs.getDouble("normal_consistency").takeUnless { rs.wasNull() },
            vertices = rs.getInt("vertices").takeUnless { rs.wasNull() },
            faces = rs.getInt("faces").takeUnless { rs.wasNull() },
            inferenceTimeSec = rs.getDouble("inference_time_sec").takeUnless { rs.wasNull() },
            isMock = rs.getBoolean("is_mock"),
            createdAt = rs.getTimestamp("created_at").toInstant()
        )
    }

    fun findByTaskId(taskId: UUID): GenerationMetrics? {
        val results = jdbcTemplate.query(
            "SELECT * FROM generation_metrics WHERE task_id = ?",
            rowMapper, taskId
        )
        return results.firstOrNull()
    }
}
