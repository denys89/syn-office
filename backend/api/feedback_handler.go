package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// FeedbackHandler handles feedback-related API endpoints
type FeedbackHandler struct {
	feedbackService *service.FeedbackService
}

// NewFeedbackHandler creates a new FeedbackHandler
func NewFeedbackHandler(feedbackService *service.FeedbackService) *FeedbackHandler {
	return &FeedbackHandler{
		feedbackService: feedbackService,
	}
}

// CreateMessageFeedbackRequest represents the request body for message feedback
type CreateMessageFeedbackRequest struct {
	FeedbackType      string `json:"feedback_type" validate:"required,oneof=positive negative correction"`
	Rating            int    `json:"rating,omitempty" validate:"omitempty,min=1,max=5"`
	Comment           string `json:"comment,omitempty"`
	CorrectionContent string `json:"correction_content,omitempty"`
}

// CreateMessageFeedback handles POST /api/v1/messages/:id/feedback
func (h *FeedbackHandler) CreateMessageFeedback(c *fiber.Ctx) error {
	// Get user_id from context (set by AuthMiddleware)
	userID, ok := c.Locals("user_id").(uuid.UUID)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Invalid user ID in context",
		})
	}

	// Parse message ID
	messageIDStr := c.Params("id")
	messageID, err := uuid.Parse(messageIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid message ID",
		})
	}

	// Parse request body
	var req CreateMessageFeedbackRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	// Create feedback
	feedback, err := h.feedbackService.CreateMessageFeedback(
		c.Context(),
		userID,
		messageID,
		domain.FeedbackType(req.FeedbackType),
		req.Rating,
		req.Comment,
		req.CorrectionContent,
	)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.Status(fiber.StatusCreated).JSON(feedback)
}

// GetAgentFeedbackSummary handles GET /api/v1/agents/:id/feedback-summary
func (h *FeedbackHandler) GetAgentFeedbackSummary(c *fiber.Ctx) error {
	// Get user_id from context (set by AuthMiddleware)
	userID, ok := c.Locals("user_id").(uuid.UUID)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Invalid user ID in context",
		})
	}

	// Parse agent ID
	agentIDStr := c.Params("id")
	agentID, err := uuid.Parse(agentIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid agent ID",
		})
	}

	// Get feedback summary
	summary, err := h.feedbackService.GetAgentFeedbackSummary(c.Context(), userID, agentID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(summary)
}

// GetAgentMemories handles GET /api/v1/agents/:id/memories
func (h *FeedbackHandler) GetAgentMemories(c *fiber.Ctx) error {
	// Get user_id from context (set by AuthMiddleware)
	userID, ok := c.Locals("user_id").(uuid.UUID)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Invalid user ID in context",
		})
	}

	// Parse agent ID
	agentIDStr := c.Params("id")
	agentID, err := uuid.Parse(agentIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid agent ID",
		})
	}

	// Get query params for filtering
	memoryType := c.Query("type", "")
	limitStr := c.Query("limit", "50")
	limit := 50
	if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 100 {
		limit = l
	}

	// Get memories
	memories, err := h.feedbackService.GetAgentMemories(c.Context(), userID, agentID, memoryType, limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"memories": memories,
		"count":    len(memories),
	})
}
