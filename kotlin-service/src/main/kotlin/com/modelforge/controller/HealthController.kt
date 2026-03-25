package com.modelforge.controller

import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.security.SecurityRequirements
import io.swagger.v3.oas.annotations.tags.Tag
import org.slf4j.LoggerFactory
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import java.time.Instant

@RestController
@Tag(name = "Health", description = "Проверка работоспособности")
@SecurityRequirements
class HealthController {

    private val logger = LoggerFactory.getLogger(HealthController::class.java)

    @GetMapping("/health")
    @Operation(summary = "Health check")
    fun health(): Map<String, Any> {
        logger.info("Health check requested")
        return mapOf(
            "status" to "UP",
            "service" to "modelforge-kotlin-service",
            "timestamp" to Instant.now().toString()
        )
    }
}
