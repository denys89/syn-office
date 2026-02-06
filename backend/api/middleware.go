package api

import (
	"log"
	"strings"

	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
)

// AuthMiddleware handles JWT authentication
func AuthMiddleware(authService *service.AuthService) fiber.Handler {
	return func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "missing authorization header",
			})
		}

		// Extract token from "Bearer <token>"
		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "invalid authorization header format",
			})
		}

		token := parts[1]
		claims, err := authService.ValidateToken(token)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "invalid or expired token",
			})
		}

		// Store claims in context
		c.Locals("user_id", claims.UserID)
		c.Locals("office_id", claims.OfficeID)
		c.Locals("email", claims.Email)

		return c.Next()
	}
}

// InternalAPIKeyMiddleware validates internal service-to-service requests
func InternalAPIKeyMiddleware(expectedKey string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		apiKey := c.Get("X-Internal-API-Key")

		// Debug logging
		log.Printf("[Internal API] Received key: %s... (length: %d)", apiKey[:min(10, len(apiKey))], len(apiKey))
		log.Printf("[Internal API] Expected key: %s... (length: %d)", expectedKey[:min(10, len(expectedKey))], len(expectedKey))

		if apiKey == "" {
			log.Printf("[Internal API] Missing API key")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "missing internal API key",
			})
		}

		if apiKey != expectedKey {
			log.Printf("[Internal API] Key mismatch!")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "invalid internal API key",
			})
		}

		log.Printf("[Internal API] Authentication successful")
		return c.Next()
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
