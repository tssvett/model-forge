package com.modelforge

import com.modelforge.controller.AuthController
import com.modelforge.controller.HealthController
import com.modelforge.repository.UserRepository
import com.modelforge.service.AuthService
import com.modelforge.service.JwtService
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles

@SpringBootTest
@ActiveProfiles("test")
class ApplicationTest {

    @Autowired
    lateinit var authController: AuthController

    @Autowired
    lateinit var healthController: HealthController

    @Autowired
    lateinit var authService: AuthService

    @Autowired
    lateinit var jwtService: JwtService

    @Autowired
    lateinit var userRepository: UserRepository

    @Test
    fun contextLoads() {
        assertNotNull(authController)
        assertNotNull(healthController)
        assertNotNull(authService)
        assertNotNull(jwtService)
        assertNotNull(userRepository)
    }
}
