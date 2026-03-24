package com.modelforge.config

import org.mockito.Mockito.mock
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.context.annotation.Bean
import org.springframework.kafka.core.KafkaTemplate

@TestConfiguration
class TestKafkaConfig {

    @Suppress("UNCHECKED_CAST")
    @Bean
    fun kafkaTemplate(): KafkaTemplate<String, String> {
        return mock(KafkaTemplate::class.java) as KafkaTemplate<String, String>
    }
}
