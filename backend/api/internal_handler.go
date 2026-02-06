package api

import (
	"log"

	"github.com/denys89/syn-office/backend/repository"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// InternalHandler handles internal service-to-service endpoints
type InternalHandler struct {
	wsHandler        *WSHandler
	conversationRepo *repository.ConversationRepository
	creditService    *service.CreditService
}

// NewInternalHandler creates a new InternalHandler
func NewInternalHandler(
	wsHandler *WSHandler,
	conversationRepo *repository.ConversationRepository,
	creditService *service.CreditService,
) *InternalHandler {
	return &InternalHandler{
		wsHandler:        wsHandler,
		conversationRepo: conversationRepo,
		creditService:    creditService,
	}
}

// TaskCompleteRequest represents a task completion notification from the orchestrator
type TaskCompleteRequest struct {
	TaskID         string `json:"task_id"`
	ConversationID string `json:"conversation_id"`
	AgentID        string `json:"agent_id"`
	Output         string `json:"output"`
}

// TaskComplete handles task completion notifications from the agent orchestrator
// POST /internal/task-complete
func (h *InternalHandler) TaskComplete(c *fiber.Ctx) error {
	var req TaskCompleteRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	// Parse UUIDs
	conversationID, err := uuid.Parse(req.ConversationID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid conversation_id",
		})
	}

	agentID, err := uuid.Parse(req.AgentID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid agent_id",
		})
	}

	log.Printf("Task completed: %s for conversation %s by agent %s", req.TaskID, conversationID, agentID)

	// Get the conversation to find the office_id
	conversation, err := h.conversationRepo.GetByID(c.Context(), conversationID)
	if err != nil {
		log.Printf("Failed to get conversation: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get conversation",
		})
	}

	// Broadcast the new message to WebSocket clients
	h.wsHandler.BroadcastToOffice(conversation.OfficeID, WSMessage{
		EventID:   uuid.New().String(),
		EventType: "new_message",
		Payload: map[string]any{
			"conversation_id": req.ConversationID,
			"sender_type":     "agent",
			"sender_id":       req.AgentID,
			"content":         req.Output,
		},
	})

	log.Printf("Broadcasted message to office %s", conversation.OfficeID)

	return c.JSON(fiber.Map{
		"status":  "ok",
		"message": "task completion received and broadcasted",
	})
}

// =============================================================================
// Internal Credit Endpoints (for orchestrator service-to-service calls)
// =============================================================================

// CreditCheckRequest represents a credit balance check request
type CreditCheckRequest struct {
	OfficeID        string `json:"office_id"`
	RequiredCredits int64  `json:"required_credits"`
}

// CheckCredits checks if an office has sufficient credits
// POST /internal/credits/check
func (h *InternalHandler) CheckCredits(c *fiber.Ctx) error {
	var req CreditCheckRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	officeID, err := uuid.Parse(req.OfficeID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	hasSufficient, currentBalance, err := h.creditService.CheckSufficientCredits(c.Context(), officeID, req.RequiredCredits)
	if err != nil {
		log.Printf("Credit check failed: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to check credits",
		})
	}

	return c.JSON(fiber.Map{
		"has_sufficient":   hasSufficient,
		"current_balance":  currentBalance,
		"required_credits": req.RequiredCredits,
	})
}

// CreditConsumeRequest represents a credit consumption request
type CreditConsumeRequest struct {
	OfficeID    string `json:"office_id"`
	TaskID      string `json:"task_id"`
	Credits     int64  `json:"credits"`
	Description string `json:"description"`
}

// ConsumeCredits consumes credits for a task execution
// POST /internal/credits/consume
func (h *InternalHandler) ConsumeCredits(c *fiber.Ctx) error {
	var req CreditConsumeRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	officeID, err := uuid.Parse(req.OfficeID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	taskID, err := uuid.Parse(req.TaskID)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid task_id",
		})
	}

	tx, err := h.creditService.ConsumeCreditsForTask(c.Context(), officeID, taskID, req.Credits, req.Description)
	if err != nil {
		log.Printf("Credit consumption failed: %v", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"success":        true,
		"transaction_id": tx.ID.String(),
		"new_balance":    tx.BalanceAfter,
	})
}

// GetBalance returns the credit balance for an office
// GET /internal/credits/balance/:officeId
func (h *InternalHandler) GetBalance(c *fiber.Ctx) error {
	officeIDStr := c.Params("officeId")
	officeID, err := uuid.Parse(officeIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid office_id",
		})
	}

	balance, err := h.creditService.GetBalance(c.Context(), officeID)
	if err != nil {
		log.Printf("Get balance failed: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get balance",
		})
	}

	return c.JSON(fiber.Map{
		"balance": balance,
	})
}
