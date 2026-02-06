package service

import (
	"context"
	"errors"
	"os"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
)

// SubscriptionService handles subscription business logic
type SubscriptionService struct {
	subRepo    domain.SubscriptionRepository
	creditRepo domain.CreditRepository
	tiers      map[domain.SubscriptionTier]*domain.TierDefinition
	tiersPath  string
}

// NewSubscriptionService creates a new subscription service
func NewSubscriptionService(
	subRepo domain.SubscriptionRepository,
	creditRepo domain.CreditRepository,
	tiersPath string,
) *SubscriptionService {
	svc := &SubscriptionService{
		subRepo:    subRepo,
		creditRepo: creditRepo,
		tiersPath:  tiersPath,
		tiers:      make(map[domain.SubscriptionTier]*domain.TierDefinition),
	}
	svc.loadTiers()
	return svc
}

// TierConfig represents the YAML structure
type TierConfig struct {
	Tiers map[string]domain.TierDefinition `yaml:"tiers"`
}

// loadTiers loads tier definitions from YAML
func (s *SubscriptionService) loadTiers() error {
	data, err := os.ReadFile(s.tiersPath)
	if err != nil {
		// Use defaults if file not found
		s.loadDefaultTiers()
		return nil
	}

	var config TierConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		s.loadDefaultTiers()
		return err
	}

	for tierKey, tierDef := range config.Tiers {
		tier := domain.SubscriptionTier(tierKey)
		def := tierDef // Copy to avoid pointer issues
		s.tiers[tier] = &def
	}
	return nil
}

// loadDefaultTiers sets up default tier definitions
func (s *SubscriptionService) loadDefaultTiers() {
	s.tiers[domain.TierSolo] = &domain.TierDefinition{
		Name:        "Solo Founder",
		Description: "Perfect for individual developers",
		Features: domain.TierFeatures{
			MaxAgents:      3,
			MonthlyCredits: 1000,
			MaxSeats:       1,
			ModelAccess:    []string{"ollama", "groq"},
			Priority:       "low",
			RetentionDays:  30,
		},
	}
	s.tiers[domain.TierProfessional] = &domain.TierDefinition{
		Name:        "Professional",
		Description: "For power users and small teams",
		Features: domain.TierFeatures{
			MaxAgents:      10,
			MonthlyCredits: 10000,
			MaxSeats:       5,
			ModelAccess:    []string{"ollama", "groq", "openai"},
			Priority:       "normal",
			RetentionDays:  90,
			WebResearch:    true,
			APIAccess:      true,
		},
	}
	s.tiers[domain.TierBusiness] = &domain.TierDefinition{
		Name:        "Business",
		Description: "For growing teams",
		Features: domain.TierFeatures{
			MaxAgents:             50,
			MonthlyCredits:        50000,
			MaxSeats:              20,
			ModelAccess:           []string{"ollama", "groq", "openai", "anthropic"},
			Priority:              "high",
			RetentionDays:         365,
			WebResearch:           true,
			AdvancedOrchestration: true,
			Analytics:             true,
			APIAccess:             true,
		},
	}
}

// GetTier returns the tier definition for a tier
func (s *SubscriptionService) GetTier(tier domain.SubscriptionTier) (*domain.TierDefinition, error) {
	def, ok := s.tiers[tier]
	if !ok {
		return nil, errors.New("tier not found")
	}
	return def, nil
}

// GetAllTiers returns all tier definitions
func (s *SubscriptionService) GetAllTiers() map[domain.SubscriptionTier]*domain.TierDefinition {
	return s.tiers
}

// GetSubscriptionByOffice gets subscription for an office
func (s *SubscriptionService) GetSubscriptionByOffice(ctx context.Context, officeID uuid.UUID) (*domain.Subscription, error) {
	return s.subRepo.GetByOfficeID(ctx, officeID)
}

// GetSubscriptionSummary gets subscription with usage summary
func (s *SubscriptionService) GetSubscriptionSummary(ctx context.Context, officeID uuid.UUID) (*domain.SubscriptionSummary, error) {
	sub, err := s.subRepo.GetByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}

	tierDef, _ := s.GetTier(sub.Tier)

	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}

	alloc, _ := s.subRepo.GetCurrentAllocation(ctx, sub.ID)

	daysRemaining := int(time.Until(sub.CurrentPeriodEnd).Hours() / 24)

	summary := &domain.SubscriptionSummary{
		Subscription:   sub,
		Tier:           tierDef,
		CurrentBalance: wallet.Balance,
		DaysRemaining:  daysRemaining,
	}

	if alloc != nil {
		summary.PeriodCreditsAllocated = alloc.CreditsAllocated
		summary.PeriodCreditsConsumed = alloc.CreditsConsumed
	}

	return summary, nil
}

// UpgradeTier upgrades an office's subscription tier
func (s *SubscriptionService) UpgradeTier(ctx context.Context, officeID uuid.UUID, newTier domain.SubscriptionTier) error {
	sub, err := s.subRepo.GetByOfficeID(ctx, officeID)
	if err != nil {
		return err
	}

	tierDef, err := s.GetTier(newTier)
	if err != nil {
		return err
	}

	// Update tier
	if err := s.subRepo.UpdateTier(ctx, sub.ID, newTier); err != nil {
		return err
	}

	// Allocate additional credits for the new tier (pro-rated for current period)
	oldTierDef, _ := s.GetTier(sub.Tier)
	additionalCredits := tierDef.Features.MonthlyCredits
	if oldTierDef != nil {
		additionalCredits -= oldTierDef.Features.MonthlyCredits
	}

	if additionalCredits > 0 {
		wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
		if err != nil {
			return err
		}

		_, err = s.creditRepo.AddCredits(
			ctx, wallet.ID, additionalCredits,
			domain.TransactionTypeSubscription,
			"Tier upgrade credit allocation",
			"subscription", &sub.ID,
		)
		if err != nil {
			return err
		}
	}

	return nil
}

// AllocateMonthlyCredits allocates credits for a new billing period
func (s *SubscriptionService) AllocateMonthlyCredits(ctx context.Context, subscriptionID uuid.UUID) error {
	sub, err := s.subRepo.GetByID(ctx, subscriptionID)
	if err != nil {
		return err
	}

	tierDef, err := s.GetTier(sub.Tier)
	if err != nil {
		return err
	}

	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, sub.OfficeID)
	if err != nil {
		return err
	}

	// Create allocation record
	alloc := &domain.CreditAllocation{
		SubscriptionID:   sub.ID,
		WalletID:         wallet.ID,
		PeriodStart:      sub.CurrentPeriodStart,
		PeriodEnd:        sub.CurrentPeriodEnd,
		CreditsAllocated: tierDef.Features.MonthlyCredits,
		Source:           "subscription",
	}

	if err := s.subRepo.CreateAllocation(ctx, alloc); err != nil {
		return err
	}

	// Add credits to wallet
	_, err = s.creditRepo.AddCredits(
		ctx, wallet.ID, tierDef.Features.MonthlyCredits,
		domain.TransactionTypeSubscription,
		"Monthly credit allocation",
		"subscription", &sub.ID,
	)
	return err
}

// CheckModelAccess checks if a tier has access to a specific model provider
func (s *SubscriptionService) CheckModelAccess(ctx context.Context, officeID uuid.UUID, provider string) (bool, error) {
	sub, err := s.subRepo.GetByOfficeID(ctx, officeID)
	if err != nil {
		return false, err
	}

	tierDef, err := s.GetTier(sub.Tier)
	if err != nil {
		return false, err
	}

	for _, allowed := range tierDef.Features.ModelAccess {
		if allowed == provider {
			return true, nil
		}
	}
	return false, nil
}

// CheckAgentLimit checks if office can create more agents
func (s *SubscriptionService) CheckAgentLimit(ctx context.Context, officeID uuid.UUID, currentCount int) (bool, int, error) {
	sub, err := s.subRepo.GetByOfficeID(ctx, officeID)
	if err != nil {
		return false, 0, err
	}

	tierDef, err := s.GetTier(sub.Tier)
	if err != nil {
		return false, 0, err
	}

	limit := tierDef.Features.MaxAgents
	if limit == -1 { // Unlimited
		return true, -1, nil
	}

	return currentCount < limit, limit, nil
}

// ProcessStripeWebhook handles Stripe webhook events
func (s *SubscriptionService) ProcessStripeWebhook(ctx context.Context, eventType string, data map[string]any) error {
	// Stub for Stripe webhook handling
	// Will be implemented when Stripe integration is added
	switch eventType {
	case "customer.subscription.created":
		// Handle new subscription
	case "customer.subscription.updated":
		// Handle subscription update
	case "customer.subscription.deleted":
		// Handle cancellation
	case "invoice.paid":
		// Handle successful renewal - allocate monthly credits
	case "invoice.payment_failed":
		// Handle failed payment - update status
	}
	return nil
}
