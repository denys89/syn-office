package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// EarningsHandler handles marketplace earnings API endpoints
type EarningsHandler struct {
	earningsService *service.EarningsService
}

// NewEarningsHandler creates a new earnings handler
func NewEarningsHandler(earningsService *service.EarningsService) *EarningsHandler {
	return &EarningsHandler{earningsService: earningsService}
}

// getUserID extracts user ID from context
func (h *EarningsHandler) getUserID(c *fiber.Ctx) (uuid.UUID, error) {
	userIDVal := c.Locals("user_id")
	if userIDVal == nil {
		return uuid.Nil, fiber.ErrUnauthorized
	}
	userID, ok := userIDVal.(uuid.UUID)
	if !ok {
		return uuid.Nil, fiber.ErrBadRequest
	}
	return userID, nil
}

// getOfficeID extracts office ID from context
func (h *EarningsHandler) getOfficeID(c *fiber.Ctx) (uuid.UUID, error) {
	officeIDVal := c.Locals("office_id")
	if officeIDVal == nil {
		return uuid.Nil, fiber.ErrUnauthorized
	}
	officeID, ok := officeIDVal.(uuid.UUID)
	if !ok {
		return uuid.Nil, fiber.ErrBadRequest
	}
	return officeID, nil
}

// PurchaseRequest represents a template purchase request
type PurchaseTemplateRequest struct {
	TemplateID            string `json:"template_id"`
	StripePaymentIntentID string `json:"stripe_payment_intent_id"`
}

// PurchaseTemplate handles template purchase
// POST /api/v1/marketplace/purchase
func (h *EarningsHandler) PurchaseTemplate(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	officeID, err := h.getOfficeID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	var req PurchaseTemplateRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	templateID, err := uuid.Parse(req.TemplateID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid template_id",
		})
	}

	earningID, err := h.earningsService.PurchaseTemplate(
		c.Context(),
		templateID,
		userID,
		officeID,
		req.StripePaymentIntentID,
	)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"success":    true,
		"earning_id": earningID,
	})
}

// GetAuthorEarnings retrieves earnings for the current user (author)
// GET /api/v1/author/earnings?limit=50&offset=0
func (h *EarningsHandler) GetAuthorEarnings(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	limit := 50
	offset := 0
	if l := c.Query("limit"); l != "" {
		if parsed, err := strconv.Atoi(l); err == nil && parsed > 0 && parsed <= 100 {
			limit = parsed
		}
	}
	if o := c.Query("offset"); o != "" {
		if parsed, err := strconv.Atoi(o); err == nil && parsed >= 0 {
			offset = parsed
		}
	}

	earnings, err := h.earningsService.GetAuthorEarnings(c.Context(), userID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"earnings": earnings,
		"limit":    limit,
		"offset":   offset,
	})
}

// GetAuthorBalance retrieves balance for the current user
// GET /api/v1/author/balance
func (h *EarningsHandler) GetAuthorBalance(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	balance, err := h.earningsService.GetAuthorBalance(c.Context(), userID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(balance)
}

// GetEarningsSummary retrieves earnings summary for the current user
// GET /api/v1/author/summary
func (h *EarningsHandler) GetEarningsSummary(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	summary, err := h.earningsService.GetEarningsSummary(c.Context(), userID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(summary)
}

// PayoutRequest represents a payout request body
type PayoutRequestBody struct {
	AmountCents int `json:"amount_cents"`
}

// RequestPayout creates a payout request
// POST /api/v1/author/payout/request
func (h *EarningsHandler) RequestPayout(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	var req PayoutRequestBody
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	payoutID, err := h.earningsService.RequestPayout(c.Context(), userID, req.AmountCents)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"success":   true,
		"payout_id": payoutID,
	})
}

// GetPayoutRequests retrieves payout requests for the current user
// GET /api/v1/author/payouts?limit=50&offset=0
func (h *EarningsHandler) GetPayoutRequests(c *fiber.Ctx) error {
	userID, err := h.getUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "user_id not found in context",
		})
	}

	limit := 50
	offset := 0
	if l := c.Query("limit"); l != "" {
		if parsed, err := strconv.Atoi(l); err == nil && parsed > 0 && parsed <= 100 {
			limit = parsed
		}
	}
	if o := c.Query("offset"); o != "" {
		if parsed, err := strconv.Atoi(o); err == nil && parsed >= 0 {
			offset = parsed
		}
	}

	payouts, err := h.earningsService.GetPayoutRequests(c.Context(), userID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"payouts": payouts,
		"limit":   limit,
		"offset":  offset,
	})
}
