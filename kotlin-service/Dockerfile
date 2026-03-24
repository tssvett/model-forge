# === Stage 1: Сборка ===
FROM gradle:8.5-jdk17 AS builder

WORKDIR /app

# Кэширование зависимостей
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle/ ./gradle/
RUN gradle dependencies --no-daemon || true

# Сборка приложения
COPY src/ ./src/
RUN gradle bootJar --no-daemon

# === Stage 2: Runtime ===
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Системные зависимости для healthcheck
RUN apk add --no-cache curl

# Копирование JAR
COPY --from=builder /app/build/libs/*.jar app.jar

# JVM оптимизация для контейнеров
ENV JAVA_OPTS="-Xmx256m -Xms256m -XX:MaxMetaspaceSize=128m -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
