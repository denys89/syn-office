package api

import (
	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// SubscriptionHandler handles subscription API endpoints
type SubscriptionHandler struct {
	subService *service.SubscriptionService
}

// NewSubscriptionHandler creates a new subscription handler
func NewSubscriptionHandler(subService *service.SubscriptionService) *SubscriptionHandler {
	return &SubscriptionHandler{subService: subService}
}

// getOfficeID extracts office ID from context
func (h *SubscriptionHandler) getOfficeID(c *fiber.Ctx) (uuid.UUID, error) {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return uuid.Nil, fiber.ErrUnauthorized
	}
	return uuid.Parse(officeIDStr.(string))
}

// GetSubscription returns the office's subscription
// GET /api/v1/subscription
func (h *SubscriptionHandler) GetSubscription(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	sub, err := h.subService.GetSubscriptionByOffice(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error": "subscription not found",
		})
	}

	return c.JSON(sub)
}

// GetSubscriptionSummary returns subscription with usage summary
// GET /api/v1/subscription/summary
func (h *SubscriptionHandler) GetSubscriptionSummary(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	summary, err := h.subService.GetSubscriptionSummary(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(summary)
}

// GetTiers returns all available tiers
// GET /api/v1/subscription/tiers
func (h *SubscriptionHandler) GetTiers(c *fiber.Ctx) error {
	tiers := h.subService.GetAllTiers()

	tierList := make([]fiber.Map, 0, len(tiers))
	for tier, def := range tiers {
		tierList = append(tierList, fiber.Map{
			"tier":       tier,
			"definition": def,
		})
	}

	return c.JSON(fiber.Map{"tiers": tierList})
}

// GetTier returns a specific tier definition
// GET /api/v1/subscription/tiers/:tier
func (h *SubscriptionHandler) GetTier(c *fiber.Ctx) error {
	tierParam := c.Params("tier")
	tier := domain.SubscriptionTier(tierParam)

	def, err := h.subService.GetTier(tier)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error": "tier not found",
		})
	}

	return c.JSON(def)
}

// UpgradeRequest represents a tier upgrade request
type UpgradeRequest struct {
	Tier string `json:"tier"`
}

// UpgradeTier upgrades the office's subscription tier
// POST /api/v1/subscription/upgrade
func (h *SubscriptionHandler) UpgradeTier(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	var req UpgradeRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	tier := domain.SubscriptionTier(req.Tier)
	if _, err := h.subService.GetTier(tier); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid tier",
		})
	}

	if err := h.subService.UpgradeTier(c.Context(), officeID, tier); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"message": "tier upgraded successfully",
		"tier":    tier,
	})
}

// CheckModelAccessRequest represents a model access check request
type CheckModelAccessRequest struct {
	Provider string `json:"provider"`
}

// CheckModelAccess checks if office has access to a model provider
// POST /api/v1/subscription/check-model-access
func (h *SubscriptionHandler) CheckModelAccess(c *fiber.Ctx) error {
	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	var req CheckModelAccessRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	hasAccess, err := h.subService.CheckModelAccess(c.Context(), officeID, req.Provider)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"provider":   req.Provider,
		"has_access": hasAccess,
	})
}

// HandleStripeWebhook handles incoming Stripe webhook events
// POST /api/v1/webhooks/stripe
func (h *SubscriptionHandler) HandleStripeWebhook(c *fiber.Ctx) error {
	// TODO: Verify Stripe signature
	// signature := c.Get("Stripe-Signature")
	// webhookSecret := os.Getenv("STRIPE_WEBHOOK_SECRET")

	var payload map[string]any
	if err := c.BodyParser(&payload); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid payload",
		})
	}

	eventType, ok := payload["type"].(string)
	if !ok {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "missing event type",
		})
	}

	data, _ := payload["data"].(map[string]any)

	if err := h.subService.ProcessStripeWebhook(c.Context(), eventType, data); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{"received": true})
}
