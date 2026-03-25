package com.modelforge.repository

import com.modelforge.entity.User
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.stereotype.Repository
import java.sql.ResultSet
import java.util.UUID

@Repository
class UserRepository(private val jdbcTemplate: JdbcTemplate) {

    private val rowMapper = RowMapper { rs: ResultSet, _: Int ->
        User(
            id = UUID.fromString(rs.getString("id")),
            email = rs.getString("email"),
            passwordHash = rs.getString("password_hash"),
            createdAt = rs.getTimestamp("created_at").toInstant()
        )
    }

    fun save(user: User): User {
        jdbcTemplate.update(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            user.id, user.email, user.passwordHash, java.sql.Timestamp.from(user.createdAt)
        )
        return user
    }

    fun findByEmail(email: String): User? {
        val users = jdbcTemplate.query(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            rowMapper, email
        )
        return users.firstOrNull()
    }

    fun existsByEmail(email: String): Boolean {
        val count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM users WHERE email = ?",
            Int::class.java, email
        )
        return count!! > 0
    }

    fun findById(id: UUID): User? {
        val users = jdbcTemplate.query(
            "SELECT id, email, password_hash, created_at FROM users WHERE id = ?",
            rowMapper, id
        )
        return users.firstOrNull()
    }
}
