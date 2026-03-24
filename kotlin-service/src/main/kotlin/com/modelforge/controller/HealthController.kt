package com.modelforge.controller

import org.slf4j.LoggerFactory
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import java.time.Instant

@RestController
class HealthController {

    private val logger = LoggerFactory.getLogger(HealthController::class.java)

    @GetMapping("/health")
    fun health(): Map<String, Any> {
        logger.info("Health check requested")
        return mapOf(
            "status" to "UP",
            "service" to "modelforge-kotlin-service",
            "timestamp" to Instant.now().toString()
        )
    }
}
