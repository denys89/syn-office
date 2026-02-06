package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// AnalyticsHandler handles usage analytics API endpoints
type AnalyticsHandler struct {
	analyticsService *service.AnalyticsService
}

// NewAnalyticsHandler creates a new analytics handler
func NewAnalyticsHandler(analyticsService *service.AnalyticsService) *AnalyticsHandler {
	return &AnalyticsHandler{analyticsService: analyticsService}
}

// getOfficeID extracts office ID from context
func (h *AnalyticsHandler) getOfficeID(c *fiber.Ctx) (uuid.UUID, error) {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return uuid.Nil, fiber.ErrUnauthorized
	}
	return uuid.Parse(officeIDStr.(string))
}

// GetUsageSummary returns usage summary for the office
// GET /api/v1/usage/summary?period=30d
func (h *AnalyticsHandler) GetUsageSummary(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	period := c.Query("period", "30d")

	summary, err := h.analyticsService.GetUsageSummary(c.Context(), officeID, period)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(summary)
}

// GetUsageBreakdown returns detailed usage breakdown
// GET /api/v1/usage/breakdown?days=30
func (h *AnalyticsHandler) GetUsageBreakdown(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	days := 30
	if d := c.Query("days"); d != "" {
		if parsed, err := strconv.Atoi(d); err == nil && parsed > 0 && parsed <= 90 {
			days = parsed
		}
	}

	breakdown, err := h.analyticsService.GetUsageBreakdown(c.Context(), officeID, days)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(breakdown)
}

// GetDailyUsage returns daily usage trends
// GET /api/v1/usage/daily?days=30
func (h *AnalyticsHandler) GetDailyUsage(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	days := 30
	if d := c.Query("days"); d != "" {
		if parsed, err := strconv.Atoi(d); err == nil && parsed > 0 && parsed <= 90 {
			days = parsed
		}
	}

	usage, err := h.analyticsService.GetDailyUsage(c.Context(), officeID, days)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"days":  days,
		"usage": usage,
	})
}

// GetModelUsage returns usage breakdown by model
// GET /api/v1/usage/by-model?days=30
func (h *AnalyticsHandler) GetModelUsage(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	days := 30
	if d := c.Query("days"); d != "" {
		if parsed, err := strconv.Atoi(d); err == nil && parsed > 0 && parsed <= 90 {
			days = parsed
		}
	}

	usage, err := h.analyticsService.GetModelUsage(c.Context(), officeID, days)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"days":   days,
		"models": usage,
	})
}

// GetAgentUsage returns usage breakdown by agent
// GET /api/v1/usage/by-agent?days=30
func (h *AnalyticsHandler) GetAgentUsage(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	days := 30
	if d := c.Query("days"); d != "" {
		if parsed, err := strconv.Atoi(d); err == nil && parsed > 0 && parsed <= 90 {
			days = parsed
		}
	}

	usage, err := h.analyticsService.GetAgentUsage(c.Context(), officeID, days)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"days":   days,
		"agents": usage,
	})
}
