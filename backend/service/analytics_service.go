package service

import (
	"context"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/repository"
	"github.com/google/uuid"
)

// AnalyticsService handles usage analytics business logic
type AnalyticsService struct {
	analyticsRepo *repository.AnalyticsRepository
	creditRepo    domain.CreditRepository
}

// NewAnalyticsService creates a new analytics service
func NewAnalyticsService(
	analyticsRepo *repository.AnalyticsRepository,
	creditRepo domain.CreditRepository,
) *AnalyticsService {
	return &AnalyticsService{
		analyticsRepo: analyticsRepo,
		creditRepo:    creditRepo,
	}
}

// GetUsageSummary retrieves usage summary for an office
func (s *AnalyticsService) GetUsageSummary(
	ctx context.Context,
	officeID uuid.UUID,
	period string, // "today", "7d", "30d"
) (*domain.UsageSummary, error) {
	days := 30
	switch period {
	case "today":
		days = 1
	case "7d":
		days = 7
	case "30d":
		days = 30
	}

	summary, err := s.analyticsRepo.GetUsageSummary(ctx, officeID, days)
	if err != nil {
		return nil, err
	}

	// Get current balance
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err == nil {
		summary.CreditsRemaining = wallet.Balance
	}

	return summary, nil
}

// GetUsageBreakdown retrieves detailed usage breakdown
func (s *AnalyticsService) GetUsageBreakdown(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) (*domain.UsageBreakdown, error) {
	if days <= 0 {
		days = 30
	}

	byModel, err := s.analyticsRepo.GetUsageByModel(ctx, officeID, days)
	if err != nil {
		return nil, err
	}

	byAgent, err := s.analyticsRepo.GetUsageByAgent(ctx, officeID, days)
	if err != nil {
		return nil, err
	}

	byDay, err := s.analyticsRepo.GetDailyUsage(ctx, officeID, days)
	if err != nil {
		return nil, err
	}

	return &domain.UsageBreakdown{
		ByModel: byModel,
		ByAgent: byAgent,
		ByDay:   byDay,
	}, nil
}

// GetDailyUsage retrieves daily usage trends
func (s *AnalyticsService) GetDailyUsage(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageDaily, error) {
	if days <= 0 {
		days = 30
	}
	return s.analyticsRepo.GetDailyUsage(ctx, officeID, days)
}

// GetModelUsage retrieves usage breakdown by model
func (s *AnalyticsService) GetModelUsage(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageByModel, error) {
	if days <= 0 {
		days = 30
	}
	return s.analyticsRepo.GetUsageByModel(ctx, officeID, days)
}

// GetAgentUsage retrieves usage breakdown by agent
func (s *AnalyticsService) GetAgentUsage(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageByAgent, error) {
	if days <= 0 {
		days = 30
	}
	return s.analyticsRepo.GetUsageByAgent(ctx, officeID, days)
}

// RecordTaskUsage records usage metrics for a completed task
func (s *AnalyticsService) RecordTaskUsage(
	ctx context.Context,
	officeID uuid.UUID,
	agentID uuid.UUID,
	agentRole string,
	modelName string,
	provider string,
	credits int,
	inputTokens int,
	outputTokens int,
	isLocalModel bool,
	usdCost float64,
	success bool,
) error {
	return s.analyticsRepo.RecordTaskUsage(
		ctx, officeID, agentID, agentRole, modelName, provider,
		credits, inputTokens, outputTokens, isLocalModel, usdCost, success,
	)
}
