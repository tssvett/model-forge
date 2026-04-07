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

    fun getAverageMetricsByUserId(userId: UUID): Map<String, Double?> {
        val sql = """
            SELECT AVG(gm.inference_time_sec) as avg_inference_time,
                   AVG(gm.chamfer_distance) as avg_chamfer_distance,
                   AVG(gm.iou_3d) as avg_iou_3d,
                   AVG(gm.f_score) as avg_f_score,
                   AVG(gm.normal_consistency) as avg_normal_consistency,
                   AVG(gm.vertices) as avg_vertices,
                   AVG(gm.faces) as avg_faces
            FROM generation_metrics gm
            JOIN tasks t ON t.id = gm.task_id
            WHERE t.user_id = ?
        """
        return jdbcTemplate.queryForMap(sql, userId).mapValues { (_, v) ->
            (v as? Number)?.toDouble()
        }
    }

    fun findByUserIdPaged(userId: UUID, offset: Long, limit: Int): List<GenerationMetrics> {
        val sql = """
            SELECT gm.* FROM generation_metrics gm
            JOIN tasks t ON t.id = gm.task_id
            WHERE t.user_id = ?
            ORDER BY gm.created_at DESC
            LIMIT ? OFFSET ?
        """
        return jdbcTemplate.query(sql, rowMapper, userId, limit, offset)
    }
}
