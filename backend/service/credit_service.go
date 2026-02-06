package service

import (
	"context"
	"fmt"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
)

// CreditService handles credit-related business logic
type CreditService struct {
	creditRepo domain.CreditRepository
	officeRepo domain.OfficeRepository
}

// NewCreditService creates a new CreditService instance
func NewCreditService(creditRepo domain.CreditRepository, officeRepo domain.OfficeRepository) *CreditService {
	return &CreditService{
		creditRepo: creditRepo,
		officeRepo: officeRepo,
	}
}

// GetWallet returns the credit wallet for an office
func (s *CreditService) GetWallet(ctx context.Context, officeID uuid.UUID) (*domain.CreditWallet, error) {
	return s.creditRepo.GetWalletByOfficeID(ctx, officeID)
}

// GetBalance returns the current credit balance for an office
func (s *CreditService) GetBalance(ctx context.Context, officeID uuid.UUID) (int64, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return 0, err
	}
	return wallet.Balance, nil
}

// EnsureWallet ensures an office has a credit wallet, creating one if needed
func (s *CreditService) EnsureWallet(ctx context.Context, officeID uuid.UUID) (*domain.CreditWallet, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err == nil {
		return wallet, nil
	}
	if err == domain.ErrNotFound {
		// Create new wallet with initial free credits
		return s.creditRepo.CreateWallet(ctx, officeID, 1000)
	}
	return nil, err
}

// AddCredits adds credits to an office's wallet
func (s *CreditService) AddCredits(
	ctx context.Context,
	officeID uuid.UUID,
	amount int64,
	txType domain.TransactionType,
	description string,
) (*domain.CreditTransaction, error) {
	wallet, err := s.EnsureWallet(ctx, officeID)
	if err != nil {
		return nil, err
	}
	return s.creditRepo.AddCredits(ctx, wallet.ID, amount, txType, description, "", nil)
}

// ConsumeCreditsForTask deducts credits from an office's wallet for task execution
func (s *CreditService) ConsumeCreditsForTask(
	ctx context.Context,
	officeID uuid.UUID,
	taskID uuid.UUID,
	credits int64,
	description string,
) (*domain.CreditTransaction, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return nil, fmt.Errorf("failed to get wallet: %w", err)
	}

	// Check if sufficient balance
	hasSufficient, currentBalance, err := s.creditRepo.HasSufficientBalance(ctx, wallet.ID, credits)
	if err != nil {
		return nil, fmt.Errorf("failed to check balance: %w", err)
	}
	if !hasSufficient {
		return nil, fmt.Errorf("insufficient credits: has %d, needs %d", currentBalance, credits)
	}

	return s.creditRepo.ConsumeCredits(ctx, wallet.ID, credits, taskID, description)
}

// CheckSufficientCredits checks if an office has enough credits for a task
func (s *CreditService) CheckSufficientCredits(
	ctx context.Context,
	officeID uuid.UUID,
	requiredCredits int64,
) (bool, int64, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return false, 0, err
	}
	return s.creditRepo.HasSufficientBalance(ctx, wallet.ID, requiredCredits)
}

// GetTransactionHistory returns transaction history for an office
func (s *CreditService) GetTransactionHistory(
	ctx context.Context,
	officeID uuid.UUID,
	limit int,
	offset int,
) ([]*domain.CreditTransaction, error) {
	if limit <= 0 {
		limit = 50
	}
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}
	return s.creditRepo.GetTransactions(ctx, wallet.ID, limit, offset)
}

// RefundCredits refunds credits for a failed task
func (s *CreditService) RefundCredits(
	ctx context.Context,
	officeID uuid.UUID,
	taskID uuid.UUID,
	credits int64,
	reason string,
) (*domain.CreditTransaction, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}
	return s.creditRepo.AddCredits(
		ctx,
		wallet.ID,
		credits, // Positive = credit (refund)
		domain.TransactionTypeRefund,
		fmt.Sprintf("Refund: %s", reason),
		"task",
		&taskID,
	)
}

// WalletSummary contains wallet summary information
type WalletSummary struct {
	Balance        int64 `json:"balance"`
	TotalPurchased int64 `json:"total_purchased"`
	TotalBonus     int64 `json:"total_bonus"`
	TotalConsumed  int64 `json:"total_consumed"`
}

// GetWalletSummary returns a summary of the wallet for display
func (s *CreditService) GetWalletSummary(ctx context.Context, officeID uuid.UUID) (*WalletSummary, error) {
	wallet, err := s.creditRepo.GetWalletByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}
	return &WalletSummary{
		Balance:        wallet.Balance,
		TotalPurchased: wallet.TotalPurchased,
		TotalBonus:     wallet.TotalBonus,
		TotalConsumed:  wallet.TotalConsumed,
	}, nil
}
