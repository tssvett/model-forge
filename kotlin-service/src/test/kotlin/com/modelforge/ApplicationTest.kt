package com.modelforge

import com.modelforge.config.TestKafkaConfig
import com.modelforge.controller.AuthController
import com.modelforge.controller.HealthController
import com.modelforge.controller.TaskController
import com.modelforge.repository.OutboxRepository
import com.modelforge.repository.TaskRepository
import com.modelforge.repository.UserRepository
import com.modelforge.service.AuthService
import com.modelforge.service.JwtService
import com.modelforge.service.TaskService
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.annotation.Import
import org.springframework.test.context.ActiveProfiles

@SpringBootTest
@ActiveProfiles("test")
@Import(TestKafkaConfig::class)
class ApplicationTest {

    @Autowired
    lateinit var authController: AuthController

    @Autowired
    lateinit var healthController: HealthController

    @Autowired
    lateinit var taskController: TaskController

    @Autowired
    lateinit var authService: AuthService

    @Autowired
    lateinit var jwtService: JwtService

    @Autowired
    lateinit var taskService: TaskService

    @Autowired
    lateinit var userRepository: UserRepository

    @Autowired
    lateinit var taskRepository: TaskRepository

    @Autowired
    lateinit var outboxRepository: OutboxRepository

    @Test
    fun contextLoads() {
        assertNotNull(authController)
        assertNotNull(healthController)
        assertNotNull(taskController)
        assertNotNull(authService)
        assertNotNull(jwtService)
        assertNotNull(taskService)
        assertNotNull(userRepository)
        assertNotNull(taskRepository)
        assertNotNull(outboxRepository)
    }
}
