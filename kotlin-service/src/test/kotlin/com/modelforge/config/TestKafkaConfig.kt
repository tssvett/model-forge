package com.modelforge.config

import io.minio.MinioClient
import org.mockito.Mockito.mock
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Primary
import org.springframework.kafka.core.KafkaTemplate

@TestConfiguration
class TestKafkaConfig {

    @Suppress("UNCHECKED_CAST")
    @Bean
    @Primary
    fun kafkaTemplate(): KafkaTemplate<String, String> {
        return mock(KafkaTemplate::class.java) as KafkaTemplate<String, String>
    }

    @Bean
    @Primary
    fun minioClient(): MinioClient {
        return mock(MinioClient::class.java)
    }
}
