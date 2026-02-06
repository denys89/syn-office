package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// CreditHandler handles credit wallet endpoints
type CreditHandler struct {
	creditService *service.CreditService
}

// NewCreditHandler creates a new CreditHandler
func NewCreditHandler(creditService *service.CreditService) *CreditHandler {
	return &CreditHandler{creditService: creditService}
}

// GetWallet returns the credit wallet for the current office
// GET /credits/wallet
func (h *CreditHandler) GetWallet(c *fiber.Ctx) error {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	officeID, err := uuid.Parse(officeIDStr.(string))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	wallet, err := h.creditService.GetWallet(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get wallet",
		})
	}

	return c.JSON(wallet)
}

// GetBalance returns the current credit balance
// GET /credits/balance
func (h *CreditHandler) GetBalance(c *fiber.Ctx) error {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	officeID, err := uuid.Parse(officeIDStr.(string))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	balance, err := h.creditService.GetBalance(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get balance",
		})
	}

	return c.JSON(fiber.Map{
		"balance": balance,
	})
}

// GetWalletSummary returns a summary of the wallet
// GET /credits/summary
func (h *CreditHandler) GetWalletSummary(c *fiber.Ctx) error {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	officeID, err := uuid.Parse(officeIDStr.(string))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	summary, err := h.creditService.GetWalletSummary(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get wallet summary",
		})
	}

	return c.JSON(summary)
}

// GetTransactions returns credit transaction history
// GET /credits/transactions?limit=50&offset=0
func (h *CreditHandler) GetTransactions(c *fiber.Ctx) error {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	officeID, err := uuid.Parse(officeIDStr.(string))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	// Parse pagination params
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

	transactions, err := h.creditService.GetTransactionHistory(c.Context(), officeID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get transactions",
		})
	}

	return c.JSON(fiber.Map{
		"transactions": transactions,
		"limit":        limit,
		"offset":       offset,
	})
}

// CheckBalance checks if there are sufficient credits for an operation
// POST /credits/check
type CheckBalanceRequest struct {
	RequiredCredits int64 `json:"required_credits"`
}

func (h *CreditHandler) CheckBalance(c *fiber.Ctx) error {
	officeIDStr := c.Locals("office_id")
	if officeIDStr == nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "office_id not found in context",
		})
	}

	officeID, err := uuid.Parse(officeIDStr.(string))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	var req CheckBalanceRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	hasSufficient, currentBalance, err := h.creditService.CheckSufficientCredits(c.Context(), officeID, req.RequiredCredits)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to check balance",
		})
	}

	return c.JSON(fiber.Map{
		"has_sufficient":   hasSufficient,
		"current_balance":  currentBalance,
		"required_credits": req.RequiredCredits,
	})
}
