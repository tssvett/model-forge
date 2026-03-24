package com.modelforge.config

import io.swagger.v3.oas.models.Components
import io.swagger.v3.oas.models.OpenAPI
import io.swagger.v3.oas.models.info.Info
import io.swagger.v3.oas.models.security.SecurityRequirement
import io.swagger.v3.oas.models.security.SecurityScheme
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class OpenApiConfig {

    @Bean
    fun openAPI(): OpenAPI {
        val bearerScheme = SecurityScheme()
            .type(SecurityScheme.Type.HTTP)
            .scheme("bearer")
            .bearerFormat("JWT")

        return OpenAPI()
            .info(
                Info()
                    .title("ModelForge API")
                    .version("0.1.0")
                    .description("REST API для системы генерации 3D-моделей")
            )
            .components(
                Components()
                    .addSecuritySchemes("bearerAuth", bearerScheme)
            )
            .addSecurityItem(
                SecurityRequirement().addList("bearerAuth")
            )
    }
}
