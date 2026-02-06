package api

import (
	"strconv"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// ChatHandler handles chat-related endpoints
type ChatHandler struct {
	chatService *service.ChatService
}

// NewChatHandler creates a new ChatHandler
func NewChatHandler(chatService *service.ChatService) *ChatHandler {
	return &ChatHandler{chatService: chatService}
}

// CreateConversationRequest represents a request to create a conversation
type CreateConversationRequest struct {
	Type     string   `json:"type"` // "direct" or "group"
	Name     string   `json:"name,omitempty"`
	AgentIDs []string `json:"agent_ids"`
}

// CreateConversation creates a new conversation
// POST /conversations
func (h *ChatHandler) CreateConversation(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)

	var req CreateConversationRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	// Validate conversation type
	convType := domain.ConversationType(req.Type)
	if convType != domain.ConversationTypeDirect && convType != domain.ConversationTypeGroup {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "type must be 'direct' or 'group'",
		})
	}

	// Parse agent IDs
	var agentIDs []uuid.UUID
	for _, idStr := range req.AgentIDs {
		id, err := uuid.Parse(idStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "invalid agent_id: " + idStr,
			})
		}
		agentIDs = append(agentIDs, id)
	}

	conversation, err := h.chatService.CreateConversation(c.Context(), service.CreateConversationInput{
		OfficeID: officeID,
		Type:     convType,
		Name:     req.Name,
		AgentIDs: agentIDs,
	})
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to create conversation",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(conversation)
}

// GetConversations returns all conversations for the office
// GET /conversations
func (h *ChatHandler) GetConversations(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)

	conversations, err := h.chatService.GetConversations(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get conversations",
		})
	}

	return c.JSON(fiber.Map{
		"conversations": conversations,
	})
}

// GetConversation returns a specific conversation
// GET /conversations/:id
func (h *ChatHandler) GetConversation(c *fiber.Ctx) error {
	conversationIDStr := c.Params("id")
	conversationID, err := uuid.Parse(conversationIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid conversation id",
		})
	}

	conversation, err := h.chatService.GetConversation(c.Context(), conversationID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error": "conversation not found",
		})
	}

	return c.JSON(conversation)
}

// SendMessageRequest represents a request to send a message
type SendMessageRequest struct {
	Content string `json:"content"`
}

// SendMessage sends a message in a conversation
// POST /conversations/:id/messages
func (h *ChatHandler) SendMessage(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)
	userID := c.Locals("user_id").(uuid.UUID)

	conversationIDStr := c.Params("id")
	conversationID, err := uuid.Parse(conversationIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid conversation id",
		})
	}

	var req SendMessageRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	if req.Content == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "content is required",
		})
	}

	message, err := h.chatService.SendMessage(c.Context(), service.SendMessageInput{
		OfficeID:       officeID,
		ConversationID: conversationID,
		SenderType:     domain.SenderTypeUser,
		SenderID:       userID,
		Content:        req.Content,
	})
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to send message",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(message)
}

// GetMessages returns messages for a conversation
// GET /conversations/:id/messages
func (h *ChatHandler) GetMessages(c *fiber.Ctx) error {
	conversationIDStr := c.Params("id")
	conversationID, err := uuid.Parse(conversationIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid conversation id",
		})
	}

	limit, _ := strconv.Atoi(c.Query("limit", "50"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	messages, err := h.chatService.GetMessages(c.Context(), conversationID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get messages",
		})
	}

	return c.JSON(fiber.Map{
		"messages": messages,
	})
}
