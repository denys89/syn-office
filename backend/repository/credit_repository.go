package repository

import (
	"context"
	"errors"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// CreditRepository implements credit wallet and transaction operations
type CreditRepository struct {
	db *pgxpool.Pool
}

// NewCreditRepository creates a new CreditRepository
func NewCreditRepository(db *pgxpool.Pool) *CreditRepository {
	return &CreditRepository{db: db}
}

// CreateWallet creates a new credit wallet for an office
func (r *CreditRepository) CreateWallet(ctx context.Context, officeID uuid.UUID, initialBalance int64) (*domain.CreditWallet, error) {
	wallet := &domain.CreditWallet{
		ID:             uuid.New(),
		OfficeID:       officeID,
		Balance:        initialBalance,
		TotalPurchased: 0,
		TotalBonus:     initialBalance, // Initial balance is a bonus
		TotalConsumed:  0,
		CreatedAt:      time.Now(),
		UpdatedAt:      time.Now(),
	}

	query := `
		INSERT INTO credit_wallets (id, office_id, balance, total_purchased, total_bonus, total_consumed, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		ON CONFLICT (office_id) DO NOTHING
		RETURNING id, office_id, balance, total_purchased, total_bonus, total_consumed, created_at, updated_at
	`

	err := r.db.QueryRow(ctx, query,
		wallet.ID, wallet.OfficeID, wallet.Balance,
		wallet.TotalPurchased, wallet.TotalBonus, wallet.TotalConsumed,
		wallet.CreatedAt, wallet.UpdatedAt,
	).Scan(
		&wallet.ID, &wallet.OfficeID, &wallet.Balance,
		&wallet.TotalPurchased, &wallet.TotalBonus, &wallet.TotalConsumed,
		&wallet.CreatedAt, &wallet.UpdatedAt,
	)

	if err != nil {
		// If conflict, return existing wallet
		if errors.Is(err, pgx.ErrNoRows) {
			return r.GetWalletByOfficeID(ctx, officeID)
		}
		return nil, err
	}

	return wallet, nil
}

// GetWalletByID retrieves a credit wallet by ID
func (r *CreditRepository) GetWalletByID(ctx context.Context, id uuid.UUID) (*domain.CreditWallet, error) {
	query := `
		SELECT id, office_id, balance, total_purchased, total_bonus, total_consumed, created_at, updated_at
		FROM credit_wallets WHERE id = $1
	`

	var wallet domain.CreditWallet
	err := r.db.QueryRow(ctx, query, id).Scan(
		&wallet.ID, &wallet.OfficeID, &wallet.Balance,
		&wallet.TotalPurchased, &wallet.TotalBonus, &wallet.TotalConsumed,
		&wallet.CreatedAt, &wallet.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &wallet, nil
}

// GetWalletByOfficeID retrieves a credit wallet by office ID
func (r *CreditRepository) GetWalletByOfficeID(ctx context.Context, officeID uuid.UUID) (*domain.CreditWallet, error) {
	query := `
		SELECT id, office_id, balance, total_purchased, total_bonus, total_consumed, created_at, updated_at
		FROM credit_wallets WHERE office_id = $1
	`

	var wallet domain.CreditWallet
	err := r.db.QueryRow(ctx, query, officeID).Scan(
		&wallet.ID, &wallet.OfficeID, &wallet.Balance,
		&wallet.TotalPurchased, &wallet.TotalBonus, &wallet.TotalConsumed,
		&wallet.CreatedAt, &wallet.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &wallet, nil
}

// AddCredits adds credits to a wallet (uses DB function for atomicity)
func (r *CreditRepository) AddCredits(
	ctx context.Context,
	walletID uuid.UUID,
	amount int64,
	txType domain.TransactionType,
	description string,
	refType string,
	refID *uuid.UUID,
) (*domain.CreditTransaction, error) {
	query := `
		SELECT * FROM update_wallet_balance($1, $2, $3, $4, $5, $6, NULL)
	`

	var tx domain.CreditTransaction
	err := r.db.QueryRow(ctx, query, walletID, amount, string(txType), refType, refID, description).Scan(
		&tx.ID, &tx.WalletID, &tx.Type, &tx.Amount, &tx.BalanceAfter,
		&tx.ReferenceType, &tx.ReferenceID, &tx.Description, &tx.Metadata, &tx.CreatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &tx, nil
}

// ConsumeCredits deducts credits from a wallet for task execution
func (r *CreditRepository) ConsumeCredits(
	ctx context.Context,
	walletID uuid.UUID,
	amount int64,
	taskID uuid.UUID,
	description string,
) (*domain.CreditTransaction, error) {
	// Amount should be positive, but we need to negate it for consumption
	if amount > 0 {
		amount = -amount
	}
	return r.AddCredits(ctx, walletID, amount, domain.TransactionTypeConsumption, description, "task", &taskID)
}

// GetBalance returns the current balance of a wallet
func (r *CreditRepository) GetBalance(ctx context.Context, walletID uuid.UUID) (int64, error) {
	query := `SELECT balance FROM credit_wallets WHERE id = $1`
	var balance int64
	err := r.db.QueryRow(ctx, query, walletID).Scan(&balance)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, domain.ErrNotFound
	}
	return balance, err
}

// GetTransactions retrieves transaction history for a wallet
func (r *CreditRepository) GetTransactions(
	ctx context.Context,
	walletID uuid.UUID,
	limit int,
	offset int,
) ([]*domain.CreditTransaction, error) {
	query := `
		SELECT id, wallet_id, transaction_type, amount, balance_after, 
		       reference_type, reference_id, description, metadata, created_at
		FROM credit_transactions
		WHERE wallet_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, walletID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var transactions []*domain.CreditTransaction
	for rows.Next() {
		var tx domain.CreditTransaction
		if err := rows.Scan(
			&tx.ID, &tx.WalletID, &tx.Type, &tx.Amount, &tx.BalanceAfter,
			&tx.ReferenceType, &tx.ReferenceID, &tx.Description, &tx.Metadata, &tx.CreatedAt,
		); err != nil {
			return nil, err
		}
		transactions = append(transactions, &tx)
	}

	return transactions, rows.Err()
}

// GetTransactionsByType retrieves transactions of a specific type
func (r *CreditRepository) GetTransactionsByType(
	ctx context.Context,
	walletID uuid.UUID,
	txType domain.TransactionType,
	limit int,
) ([]*domain.CreditTransaction, error) {
	query := `
		SELECT id, wallet_id, transaction_type, amount, balance_after, 
		       reference_type, reference_id, description, metadata, created_at
		FROM credit_transactions
		WHERE wallet_id = $1 AND transaction_type = $2
		ORDER BY created_at DESC
		LIMIT $3
	`

	rows, err := r.db.Query(ctx, query, walletID, string(txType), limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var transactions []*domain.CreditTransaction
	for rows.Next() {
		var tx domain.CreditTransaction
		if err := rows.Scan(
			&tx.ID, &tx.WalletID, &tx.Type, &tx.Amount, &tx.BalanceAfter,
			&tx.ReferenceType, &tx.ReferenceID, &tx.Description, &tx.Metadata, &tx.CreatedAt,
		); err != nil {
			return nil, err
		}
		transactions = append(transactions, &tx)
	}

	return transactions, rows.Err()
}

// HasSufficientBalance checks if wallet has enough credits for a task
func (r *CreditRepository) HasSufficientBalance(ctx context.Context, walletID uuid.UUID, requiredCredits int64) (bool, int64, error) {
	balance, err := r.GetBalance(ctx, walletID)
	if err != nil {
		return false, 0, err
	}
	return balance >= requiredCredits, balance, nil
}
