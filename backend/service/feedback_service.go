package service

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/repository"
	"github.com/google/uuid"
)

// FeedbackService handles feedback-related operations
type FeedbackService struct {
	feedbackRepo *repository.FeedbackRepository
	agentRepo    domain.AgentRepository
	officeRepo   domain.OfficeRepository
}

// NewFeedbackService creates a new FeedbackService instance
func NewFeedbackService(
	feedbackRepo *repository.FeedbackRepository,
	agentRepo domain.AgentRepository,
	officeRepo domain.OfficeRepository,
) *FeedbackService {
	return &FeedbackService{
		feedbackRepo: feedbackRepo,
		agentRepo:    agentRepo,
		officeRepo:   officeRepo,
	}
}

// CreateMessageFeedback creates feedback for a specific message
func (s *FeedbackService) CreateMessageFeedback(
	ctx context.Context,
	userID uuid.UUID,
	messageID uuid.UUID,
	feedbackType domain.FeedbackType,
	rating int,
	comment string,
	correctionContent string,
) (*domain.AgentFeedback, error) {
	// Get the message to extract agent and office info
	message, err := s.feedbackRepo.GetMessageByID(ctx, messageID)
	if err != nil {
		return nil, err
	}

	// Verify message is from an agent (not user)
	if message.SenderType != domain.SenderTypeAgent {
		return nil, domain.ErrInvalidInput
	}

	// Verify user has access to this office (check they have at least one office)
	offices, err := s.officeRepo.GetByUserID(ctx, userID)
	if err != nil || len(offices) == 0 {
		return nil, domain.ErrForbidden
	}
	// Verify the message's office belongs to the user
	hasAccess := false
	for _, office := range offices {
		if office.ID == message.OfficeID {
			hasAccess = true
			break
		}
	}
	if !hasAccess {
		return nil, domain.ErrForbidden
	}

	// Create feedback
	feedback := &domain.AgentFeedback{
		ID:                uuid.New(),
		OfficeID:          message.OfficeID,
		AgentID:           message.SenderID,
		MessageID:         &messageID,
		FeedbackType:      feedbackType,
		Rating:            rating,
		Comment:           comment,
		OriginalContent:   message.Content,
		CorrectionContent: correctionContent,
		CreatedAt:         time.Now(),
	}

	if err := s.feedbackRepo.CreateFeedback(ctx, feedback); err != nil {
		return nil, err
	}

	return feedback, nil
}

// FeedbackSummary represents aggregated feedback statistics
type FeedbackSummary struct {
	AgentID           string  `json:"agent_id"`
	TotalFeedback     int     `json:"total_feedback"`
	PositiveCount     int     `json:"positive_count"`
	NegativeCount     int     `json:"negative_count"`
	CorrectionCount   int     `json:"correction_count"`
	AverageRating     float64 `json:"average_rating"`
	MemoryCount       int     `json:"memory_count"`
	TotalInteractions int     `json:"total_interactions"`
}

// GetAgentFeedbackSummary returns aggregated feedback stats for an agent
func (s *FeedbackService) GetAgentFeedbackSummary(
	ctx context.Context,
	userID uuid.UUID,
	agentID uuid.UUID,
) (*FeedbackSummary, error) {
	// Verify agent exists and user has access
	agent, err := s.agentRepo.GetByID(ctx, agentID)
	if err != nil {
		return nil, err
	}

	// Verify user owns this office
	offices, err := s.officeRepo.GetByUserID(ctx, userID)
	if err != nil {
		return nil, domain.ErrForbidden
	}
	hasAccess := false
	for _, office := range offices {
		if office.ID == agent.OfficeID {
			hasAccess = true
			break
		}
	}
	if !hasAccess {
		return nil, domain.ErrForbidden
	}

	// Get feedback counts
	positive, negative, correction, avgRating, err := s.feedbackRepo.GetFeedbackSummary(ctx, agentID)
	if err != nil {
		return nil, err
	}

	// Get memory count
	memoryCount, err := s.feedbackRepo.GetAgentMemoryCount(ctx, agentID)
	if err != nil {
		memoryCount = 0 // Non-critical, continue
	}

	// Get interaction count
	interactionCount, err := s.feedbackRepo.GetAgentInteractionCount(ctx, agentID)
	if err != nil {
		interactionCount = 0 // Non-critical, continue
	}

	return &FeedbackSummary{
		AgentID:           agentID.String(),
		TotalFeedback:     positive + negative + correction,
		PositiveCount:     positive,
		NegativeCount:     negative,
		CorrectionCount:   correction,
		AverageRating:     avgRating,
		MemoryCount:       memoryCount,
		TotalInteractions: interactionCount,
	}, nil
}

// GetAgentMemories returns memories for an agent
func (s *FeedbackService) GetAgentMemories(
	ctx context.Context,
	userID uuid.UUID,
	agentID uuid.UUID,
	memoryType string,
	limit int,
) ([]*domain.AgentMemory, error) {
	// Verify agent exists and user has access
	agent, err := s.agentRepo.GetByID(ctx, agentID)
	if err != nil {
		return nil, err
	}

	// Verify user owns this office
	offices, err := s.officeRepo.GetByUserID(ctx, userID)
	if err != nil {
		return nil, domain.ErrForbidden
	}
	hasAccess := false
	for _, office := range offices {
		if office.ID == agent.OfficeID {
			hasAccess = true
			break
		}
	}
	if !hasAccess {
		return nil, domain.ErrForbidden
	}

	return s.feedbackRepo.GetAgentMemories(ctx, agentID, memoryType, limit)
}
