package api

import (
	"log"

	"github.com/denys89/syn-office/backend/repository"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// InternalHandler handles internal service-to-service endpoints
type InternalHandler struct {
	wsHandler        *WSHandler
	conversationRepo *repository.ConversationRepository
}

// NewInternalHandler creates a new InternalHandler
func NewInternalHandler(wsHandler *WSHandler, conversationRepo *repository.ConversationRepository) *InternalHandler {
	return &InternalHandler{
		wsHandler:        wsHandler,
		conversationRepo: conversationRepo,
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
