package com.modelforge.controller

import com.modelforge.repository.AppSettingsRepository
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/settings")
@Tag(name = "Settings", description = "ML pipeline runtime configuration")
class SettingsController(
    private val repository: AppSettingsRepository
) {

    @GetMapping
    @Operation(summary = "Get all ML settings")
    fun getAll(): ResponseEntity<Map<String, String>> {
        return ResponseEntity.ok(repository.getAll())
    }

    @PutMapping
    @Operation(summary = "Update ML settings")
    fun update(@RequestBody body: Map<String, String>): ResponseEntity<Map<String, String>> {
        val allowed = setOf("ml_mock_mode", "ml_device")
        body.forEach { (key, value) ->
            if (key in allowed) {
                repository.set(key, value)
            }
        }
        return ResponseEntity.ok(repository.getAll())
    }
}
