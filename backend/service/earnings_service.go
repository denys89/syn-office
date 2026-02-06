package service

import (
	"context"
	"errors"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/denys89/syn-office/backend/repository"
	"github.com/google/uuid"
)

// EarningsService handles marketplace earnings business logic
type EarningsService struct {
	earningsRepo    *repository.EarningsRepository
	marketplaceRepo *repository.MarketplaceRepository
}

// NewEarningsService creates a new earnings service
func NewEarningsService(
	earningsRepo *repository.EarningsRepository,
	marketplaceRepo *repository.MarketplaceRepository,
) *EarningsService {
	return &EarningsService{
		earningsRepo:    earningsRepo,
		marketplaceRepo: marketplaceRepo,
	}
}

// Commission rates
const (
	PlatformCommissionRate = 0.20 // 20%
	AuthorRate             = 0.80 // 80%
	MinPriceCents          = 199  // $1.99
	MinPayoutCents         = 1000 // $10.00
)

// PurchaseTemplate processes a marketplace template purchase
func (s *EarningsService) PurchaseTemplate(
	ctx context.Context,
	templateID uuid.UUID,
	purchaserID uuid.UUID,
	purchaserOfficeID uuid.UUID,
	stripePaymentIntentID string,
) (uuid.UUID, error) {
	// Get template details
	template, err := s.marketplaceRepo.GetTemplateByID(ctx, templateID)
	if err != nil {
		return uuid.Nil, errors.New("template not found")
	}

	// Validate author exists
	if template.AuthorID == nil {
		return uuid.Nil, errors.New("template has no author")
	}

	// Validate price
	if template.PriceCents < MinPriceCents {
		return uuid.Nil, errors.New("template price below minimum")
	}

	// Record the sale
	earningID, err := s.earningsRepo.RecordSale(
		ctx,
		*template.AuthorID,
		templateID,
		purchaserID,
		purchaserOfficeID,
		template.PriceCents,
		stripePaymentIntentID,
	)
	if err != nil {
		return uuid.Nil, err
	}

	// Increment download (purchase) count
	_ = s.marketplaceRepo.IncrementDownload(ctx, templateID)

	return earningID, nil
}

// GetAuthorEarnings retrieves earnings for an author
func (s *EarningsService) GetAuthorEarnings(
	ctx context.Context,
	authorID uuid.UUID,
	limit, offset int,
) ([]domain.AuthorEarning, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.earningsRepo.GetAuthorEarnings(ctx, authorID, limit, offset)
}

// GetAuthorBalance retrieves the author's balance
func (s *EarningsService) GetAuthorBalance(
	ctx context.Context,
	authorID uuid.UUID,
) (*domain.AuthorBalance, error) {
	return s.earningsRepo.GetAuthorBalance(ctx, authorID)
}

// GetEarningsSummary retrieves earnings summary for an author
func (s *EarningsService) GetEarningsSummary(
	ctx context.Context,
	authorID uuid.UUID,
) (*domain.EarningsSummary, error) {
	return s.earningsRepo.GetEarningsSummary(ctx, authorID)
}

// RequestPayout creates a payout request for an author
func (s *EarningsService) RequestPayout(
	ctx context.Context,
	authorID uuid.UUID,
	amountCents int,
) (uuid.UUID, error) {
	// Validate minimum payout
	if amountCents < MinPayoutCents {
		return uuid.Nil, errors.New("minimum payout is $10.00")
	}

	// Check available balance
	balance, err := s.earningsRepo.GetAuthorBalance(ctx, authorID)
	if err != nil {
		return uuid.Nil, err
	}

	if balance.AvailableBalanceCents < int64(amountCents) {
		return uuid.Nil, errors.New("insufficient balance for payout")
	}

	// Create payout request
	return s.earningsRepo.RequestPayout(ctx, authorID, amountCents)
}

// GetPayoutRequests retrieves payout requests for an author
func (s *EarningsService) GetPayoutRequests(
	ctx context.Context,
	authorID uuid.UUID,
	limit, offset int,
) ([]domain.PayoutRequest, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.earningsRepo.GetPayoutRequests(ctx, authorID, limit, offset)
}

// CompletePayout marks a payout as completed (admin/system use)
func (s *EarningsService) CompletePayout(
	ctx context.Context,
	payoutID uuid.UUID,
	stripeTransferID string,
) error {
	return s.earningsRepo.CompletePayout(ctx, payoutID, stripeTransferID)
}

// CalculateCommission calculates platform commission and author earnings
func (s *EarningsService) CalculateCommission(saleAmountCents int) (commission, authorEarning int) {
	commission = int(float64(saleAmountCents) * PlatformCommissionRate)
	authorEarning = saleAmountCents - commission
	return
}
