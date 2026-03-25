package com.modelforge.service

import io.minio.GetObjectArgs
import io.minio.MinioClient
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service

@Service
class MinioService(
    private val minioClient: MinioClient,
    @Value("\${modelforge.minio.bucket}") private val bucket: String
) {

    private val logger = LoggerFactory.getLogger(MinioService::class.java)

    fun downloadFile(key: String): ByteArray {
        logger.debug("Downloading file from MinIO: bucket={}, key={}", bucket, key)
        return minioClient.getObject(
            GetObjectArgs.builder().bucket(bucket).`object`(key).build()
        ).use { stream -> stream.readBytes() }
    }

    fun getFileFormat(key: String): String = key.substringAfterLast('.', "bin")
}
