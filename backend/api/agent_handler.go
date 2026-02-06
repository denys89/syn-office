package api

import (
	"github.com/denys89/syn-office/backend/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// AgentHandler handles agent-related endpoints
type AgentHandler struct {
	agentService *service.AgentService
}

// NewAgentHandler creates a new AgentHandler
func NewAgentHandler(agentService *service.AgentService) *AgentHandler {
	return &AgentHandler{agentService: agentService}
}

// GetTemplates returns all available agent templates
// GET /agents/templates
func (h *AgentHandler) GetTemplates(c *fiber.Ctx) error {
	templates, err := h.agentService.GetAvailableTemplates(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get agent templates",
		})
	}

	return c.JSON(fiber.Map{
		"templates": templates,
	})
}

// SelectAgentRequest represents a request to select an agent
type SelectAgentRequest struct {
	TemplateID string `json:"template_id"`
	CustomName string `json:"custom_name,omitempty"`
}

// SelectAgent adds an agent to the user's office
// POST /agents/select
func (h *AgentHandler) SelectAgent(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)

	var req SelectAgentRequest
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

	agent, err := h.agentService.SelectAgent(c.Context(), service.SelectAgentInput{
		OfficeID:   officeID,
		TemplateID: templateID,
		CustomName: req.CustomName,
	})
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to select agent",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(agent)
}

// SelectMultipleAgentsRequest represents a request to select multiple agents
type SelectMultipleAgentsRequest struct {
	TemplateIDs []string `json:"template_ids"`
}

// SelectMultipleAgents adds multiple agents to the user's office
// POST /agents/select-multiple
func (h *AgentHandler) SelectMultipleAgents(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)

	var req SelectMultipleAgentsRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid request body",
		})
	}

	var templateIDs []uuid.UUID
	for _, idStr := range req.TemplateIDs {
		id, err := uuid.Parse(idStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "invalid template_id: " + idStr,
			})
		}
		templateIDs = append(templateIDs, id)
	}

	agents, err := h.agentService.SelectMultipleAgents(c.Context(), service.SelectMultipleAgentsInput{
		OfficeID:    officeID,
		TemplateIDs: templateIDs,
	})
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to select agents",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(fiber.Map{
		"agents": agents,
	})
}

// GetAgents returns all agents in the user's office
// GET /agents
func (h *AgentHandler) GetAgents(c *fiber.Ctx) error {
	officeID := c.Locals("office_id").(uuid.UUID)

	agents, err := h.agentService.GetOfficeAgents(c.Context(), officeID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to get agents",
		})
	}

	return c.JSON(fiber.Map{
		"agents": agents,
	})
}

// GetAgent returns a specific agent
// GET /agents/:id
func (h *AgentHandler) GetAgent(c *fiber.Ctx) error {
	agentIDStr := c.Params("id")
	agentID, err := uuid.Parse(agentIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid agent id",
		})
	}

	agent, err := h.agentService.GetAgent(c.Context(), agentID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error": "agent not found",
		})
	}

	return c.JSON(agent)
}

// DeactivateAgent deactivates an agent
// DELETE /agents/:id
func (h *AgentHandler) DeactivateAgent(c *fiber.Ctx) error {
	agentIDStr := c.Params("id")
	agentID, err := uuid.Parse(agentIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid agent id",
		})
	}

	if err := h.agentService.DeactivateAgent(c.Context(), agentID); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to deactivate agent",
		})
	}

	return c.SendStatus(fiber.StatusNoContent)
}
