package com.modelforge.repository

import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository

@Repository
class AppSettingsRepository(
    private val jdbcTemplate: JdbcTemplate
) {

    fun getAll(): Map<String, String> {
        val sql = "SELECT setting_key, setting_value FROM app_settings"
        val result = mutableMapOf<String, String>()
        jdbcTemplate.query(sql) { rs, _ ->
            result[rs.getString("setting_key")] = rs.getString("setting_value")
        }
        return result
    }

    fun get(key: String): String? {
        val sql = "SELECT setting_value FROM app_settings WHERE setting_key = ?"
        return jdbcTemplate.query(sql, { rs, _ -> rs.getString("setting_value") }, key)
            .firstOrNull()
    }

    fun set(key: String, value: String) {
        val updated = jdbcTemplate.update(
            "UPDATE app_settings SET setting_value = ? WHERE setting_key = ?", value, key
        )
        if (updated == 0) {
            jdbcTemplate.update(
                "INSERT INTO app_settings (setting_key, setting_value) VALUES (?, ?)", key, value
            )
        }
    }
}
