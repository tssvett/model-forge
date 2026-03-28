package com.modelforge.repository

import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository

@Repository
class AppSettingsRepository(
    private val jdbcTemplate: JdbcTemplate
) {

    fun getAll(): Map<String, String> {
        val sql = """SELECT "key", "value" FROM app_settings"""
        val result = mutableMapOf<String, String>()
        jdbcTemplate.query(sql) { rs, _ ->
            result[rs.getString("key")] = rs.getString("value")
        }
        return result
    }

    fun get(key: String): String? {
        val sql = """SELECT "value" FROM app_settings WHERE "key" = ?"""
        return jdbcTemplate.query(sql, { rs, _ -> rs.getString("value") }, key)
            .firstOrNull()
    }

    fun set(key: String, value: String) {
        val updated = jdbcTemplate.update(
            """UPDATE app_settings SET "value" = ? WHERE "key" = ?""", value, key
        )
        if (updated == 0) {
            jdbcTemplate.update(
                """INSERT INTO app_settings ("key", "value") VALUES (?, ?)""", key, value
            )
        }
    }
}
