package com.modelforge.config

import io.micrometer.core.instrument.MeterRegistry
import org.springframework.boot.actuate.autoconfigure.metrics.MeterRegistryCustomizer
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class MetricsConfig {

    @Value("\${spring.application.name}")
    private lateinit var applicationName: String

    @Value("\${modelforge.environment:development}")
    private lateinit var environment: String

    @Bean
    fun metricsCommonTags(): MeterRegistryCustomizer<MeterRegistry> {
        return MeterRegistryCustomizer { registry ->
            registry.config()
                .commonTags(
                    "application", applicationName,
                    "environment", environment
                )
        }
    }
}
