package com.modelforge.service

import io.jsonwebtoken.Claims
import io.jsonwebtoken.Jwts
import io.jsonwebtoken.security.Keys
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.util.Date
import java.util.UUID
import javax.crypto.SecretKey

@Service
class JwtService(
    @Value("\${modelforge.jwt.secret}") private val secret: String,
    @Value("\${modelforge.jwt.expiration-hours}") private val expirationHours: Long
) {

    private val key: SecretKey by lazy {
        Keys.hmacShaKeyFor(secret.toByteArray())
    }

    fun generateToken(userId: UUID, email: String): String {
        val now = Date()
        val expiration = Date(now.time + expirationHours * 3600 * 1000)

        return Jwts.builder()
            .subject(userId.toString())
            .claim("email", email)
            .issuedAt(now)
            .expiration(expiration)
            .signWith(key)
            .compact()
    }

    fun validateToken(token: String): Claims? {
        return try {
            Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .payload
        } catch (e: Exception) {
            null
        }
    }

    fun getUserId(claims: Claims): UUID = UUID.fromString(claims.subject)

    fun getEmail(claims: Claims): String = claims["email"] as String

    fun getExpirationSeconds(): Long = expirationHours * 3600
}
