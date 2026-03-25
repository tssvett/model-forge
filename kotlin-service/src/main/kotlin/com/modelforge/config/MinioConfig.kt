package com.modelforge.config

import io.minio.MinioClient
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Profile

@Configuration
@Profile("!test & !integration")
class MinioConfig(
    @Value("\${modelforge.minio.endpoint}") private val endpoint: String,
    @Value("\${modelforge.minio.access-key}") private val accessKey: String,
    @Value("\${modelforge.minio.secret-key}") private val secretKey: String
) {

    @Bean
    fun minioClient(): MinioClient = MinioClient.builder()
        .endpoint(endpoint)
        .credentials(accessKey, secretKey)
        .build()
}
