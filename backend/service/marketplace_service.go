package service

import (
	"context"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/repository"
	"github.com/google/uuid"
)

type MarketplaceService struct {
	marketplaceRepo *repository.MarketplaceRepository
}

func NewMarketplaceService(marketplaceRepo *repository.MarketplaceRepository) *MarketplaceService {
	return &MarketplaceService{marketplaceRepo: marketplaceRepo}
}

// ListAgents returns agents with marketplace filtering
func (s *MarketplaceService) ListAgents(ctx context.Context, filter repository.MarketplaceFilter) ([]domain.AgentTemplate, int, error) {
	// Set defaults
	if filter.Limit <= 0 {
		filter.Limit = 20
	}
	if filter.Limit > 100 {
		filter.Limit = 100
	}
	return s.marketplaceRepo.ListTemplates(ctx, filter)
}

// GetAgentDetails returns a single agent template by ID
func (s *MarketplaceService) GetAgentDetails(ctx context.Context, id uuid.UUID) (*domain.AgentTemplate, error) {
	return s.marketplaceRepo.GetTemplateByID(ctx, id)
}

// GetFeaturedAgents returns featured agents
func (s *MarketplaceService) GetFeaturedAgents(ctx context.Context) ([]domain.AgentTemplate, error) {
	featured := true
	templates, _, err := s.marketplaceRepo.ListTemplates(ctx, repository.MarketplaceFilter{
		IsFeatured: &featured,
		Limit:      10,
	})
	return templates, err
}

// GetCategories returns all categories
func (s *MarketplaceService) GetCategories(ctx context.Context) ([]domain.AgentCategory, error) {
	return s.marketplaceRepo.GetCategories(ctx)
}

// SearchAgents searches agents by query
func (s *MarketplaceService) SearchAgents(ctx context.Context, query string, limit int) ([]domain.AgentTemplate, error) {
	if limit <= 0 {
		limit = 20
	}
	templates, _, err := s.marketplaceRepo.ListTemplates(ctx, repository.MarketplaceFilter{
		Search: query,
		Limit:  limit,
	})
	return templates, err
}

// AddReview adds a review for a template
func (s *MarketplaceService) AddReview(ctx context.Context, userID, templateID uuid.UUID, rating int, title, text string) error {
	// Validate rating
	if rating < 1 || rating > 5 {
		return domain.ErrInvalidInput
	}

	// Check if template exists
	_, err := s.marketplaceRepo.GetTemplateByID(ctx, templateID)
	if err != nil {
		return err
	}

	review := &domain.AgentReview{
		TemplateID: templateID,
		UserID:     userID,
		Rating:     rating,
		Title:      title,
		ReviewText: text,
	}
	return s.marketplaceRepo.CreateReview(ctx, review)
}

// GetReviews returns reviews for a template
func (s *MarketplaceService) GetReviews(ctx context.Context, templateID uuid.UUID, limit, offset int) ([]domain.AgentReview, error) {
	if limit <= 0 {
		limit = 20
	}
	return s.marketplaceRepo.GetReviews(ctx, templateID, limit, offset)
}

// IncrementDownload increments download count when agent is added to office
func (s *MarketplaceService) IncrementDownload(ctx context.Context, templateID uuid.UUID) error {
	return s.marketplaceRepo.IncrementDownload(ctx, templateID)
}
