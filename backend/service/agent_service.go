package service

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
)

// AgentService handles agent-related operations
type AgentService struct {
	agentRepo         domain.AgentRepository
	agentTemplateRepo domain.AgentTemplateRepository
}

// NewAgentService creates a new AgentService instance
func NewAgentService(agentRepo domain.AgentRepository, agentTemplateRepo domain.AgentTemplateRepository) *AgentService {
	return &AgentService{
		agentRepo:         agentRepo,
		agentTemplateRepo: agentTemplateRepo,
	}
}

// GetAvailableTemplates returns all available agent templates
func (s *AgentService) GetAvailableTemplates(ctx context.Context) ([]*domain.AgentTemplate, error) {
	return s.agentTemplateRepo.GetAll(ctx)
}

// SelectAgentInput contains input for selecting an agent
type SelectAgentInput struct {
	OfficeID   uuid.UUID
	TemplateID uuid.UUID
	CustomName string
}

// SelectAgent adds an agent template to an office
func (s *AgentService) SelectAgent(ctx context.Context, input SelectAgentInput) (*domain.Agent, error) {
	// Verify template exists
	template, err := s.agentTemplateRepo.GetByID(ctx, input.TemplateID)
	if err != nil {
		return nil, domain.ErrNotFound
	}

	// Create agent for office
	agent := &domain.Agent{
		ID:         uuid.New(),
		OfficeID:   input.OfficeID,
		TemplateID: input.TemplateID,
		Template:   template,
		CustomName: input.CustomName,
		IsActive:   true,
		CreatedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}

	if err := s.agentRepo.Create(ctx, agent); err != nil {
		return nil, err
	}

	return agent, nil
}

// SelectMultipleAgentsInput contains input for selecting multiple agents
type SelectMultipleAgentsInput struct {
	OfficeID    uuid.UUID
	TemplateIDs []uuid.UUID
}

// SelectMultipleAgents adds multiple agent templates to an office
func (s *AgentService) SelectMultipleAgents(ctx context.Context, input SelectMultipleAgentsInput) ([]*domain.Agent, error) {
	var agents []*domain.Agent

	for _, templateID := range input.TemplateIDs {
		agent, err := s.SelectAgent(ctx, SelectAgentInput{
			OfficeID:   input.OfficeID,
			TemplateID: templateID,
		})
		if err != nil {
			return nil, err
		}
		agents = append(agents, agent)
	}

	return agents, nil
}

// GetOfficeAgents returns all agents in an office
func (s *AgentService) GetOfficeAgents(ctx context.Context, officeID uuid.UUID) ([]*domain.Agent, error) {
	return s.agentRepo.GetByOfficeID(ctx, officeID)
}

// GetAgent returns an agent by ID
func (s *AgentService) GetAgent(ctx context.Context, agentID uuid.UUID) (*domain.Agent, error) {
	return s.agentRepo.GetByID(ctx, agentID)
}

// DeactivateAgent marks an agent as inactive
func (s *AgentService) DeactivateAgent(ctx context.Context, agentID uuid.UUID) error {
	agent, err := s.agentRepo.GetByID(ctx, agentID)
	if err != nil {
		return domain.ErrNotFound
	}

	agent.IsActive = false
	agent.UpdatedAt = time.Now()

	return s.agentRepo.Update(ctx, agent)
}
