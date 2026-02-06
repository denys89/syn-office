package repository

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

// EarningsRepository implements earnings data access
type EarningsRepository struct {
	db *pgxpool.Pool
}

// NewEarningsRepository creates a new earnings repository
func NewEarningsRepository(db *pgxpool.Pool) *EarningsRepository {
	return &EarningsRepository{db: db}
}

// RecordSale records a marketplace sale using the database function
func (r *EarningsRepository) RecordSale(
	ctx context.Context,
	authorID uuid.UUID,
	templateID uuid.UUID,
	purchaserID uuid.UUID,
	purchaserOfficeID uuid.UUID,
	saleAmountCents int,
	stripePaymentIntentID string,
) (uuid.UUID, error) {
	var earningID uuid.UUID
	query := `SELECT record_marketplace_sale($1, $2, $3, $4, $5, $6)`

	err := r.db.QueryRow(ctx, query,
		authorID, templateID, purchaserID, purchaserOfficeID,
		saleAmountCents, stripePaymentIntentID,
	).Scan(&earningID)

	return earningID, err
}

// GetAuthorEarnings retrieves earnings for an author
func (r *EarningsRepository) GetAuthorEarnings(
	ctx context.Context,
	authorID uuid.UUID,
	limit, offset int,
) ([]domain.AuthorEarning, error) {
	query := `
		SELECT id, author_id, template_id, purchaser_id, purchaser_office_id,
		       sale_amount_cents, commission_cents, author_earning_cents,
		       stripe_payment_intent_id, status, created_at
		FROM author_earnings
		WHERE author_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, authorID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var earnings []domain.AuthorEarning
	for rows.Next() {
		var e domain.AuthorEarning
		var stripeID *string
		if err := rows.Scan(
			&e.ID, &e.AuthorID, &e.TemplateID, &e.PurchaserID, &e.PurchaserOfficeID,
			&e.SaleAmountCents, &e.CommissionCents, &e.AuthorEarningCents,
			&stripeID, &e.Status, &e.CreatedAt,
		); err != nil {
			return nil, err
		}
		if stripeID != nil {
			e.StripePaymentIntentID = *stripeID
		}
		earnings = append(earnings, e)
	}
	return earnings, rows.Err()
}

// GetAuthorBalance retrieves the author's current balance
func (r *EarningsRepository) GetAuthorBalance(
	ctx context.Context,
	authorID uuid.UUID,
) (*domain.AuthorBalance, error) {
	query := `
		SELECT author_id, total_earned_cents, total_paid_out_cents,
		       pending_payout_cents, available_balance_cents, updated_at
		FROM author_balances
		WHERE author_id = $1
	`

	var b domain.AuthorBalance
	err := r.db.QueryRow(ctx, query, authorID).Scan(
		&b.AuthorID, &b.TotalEarnedCents, &b.TotalPaidOutCents,
		&b.PendingPayoutCents, &b.AvailableBalanceCents, &b.UpdatedAt,
	)
	if err != nil {
		// Return zero balance if not found
		return &domain.AuthorBalance{AuthorID: authorID}, nil
	}
	return &b, nil
}

// RequestPayout creates a payout request
func (r *EarningsRepository) RequestPayout(
	ctx context.Context,
	authorID uuid.UUID,
	amountCents int,
) (uuid.UUID, error) {
	var payoutID uuid.UUID
	query := `SELECT request_author_payout($1, $2)`

	err := r.db.QueryRow(ctx, query, authorID, amountCents).Scan(&payoutID)
	return payoutID, err
}

// GetPayoutRequests retrieves payout requests for an author
func (r *EarningsRepository) GetPayoutRequests(
	ctx context.Context,
	authorID uuid.UUID,
	limit, offset int,
) ([]domain.PayoutRequest, error) {
	query := `
		SELECT id, author_id, amount_cents, status, 
		       stripe_transfer_id, failure_reason, created_at, processed_at
		FROM payout_requests
		WHERE author_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, authorID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var payouts []domain.PayoutRequest
	for rows.Next() {
		var p domain.PayoutRequest
		var stripeID, failureReason *string
		var processedAt *time.Time
		if err := rows.Scan(
			&p.ID, &p.AuthorID, &p.AmountCents, &p.Status,
			&stripeID, &failureReason, &p.CreatedAt, &processedAt,
		); err != nil {
			return nil, err
		}
		if stripeID != nil {
			p.StripeTransferID = *stripeID
		}
		if failureReason != nil {
			p.FailureReason = *failureReason
		}
		p.ProcessedAt = processedAt
		payouts = append(payouts, p)
	}
	return payouts, rows.Err()
}

// CompletePayout marks a payout as completed
func (r *EarningsRepository) CompletePayout(
	ctx context.Context,
	payoutID uuid.UUID,
	stripeTransferID string,
) error {
	query := `SELECT complete_payout($1, $2)`
	_, err := r.db.Exec(ctx, query, payoutID, stripeTransferID)
	return err
}

// GetEarningsSummary retrieves earnings summary for an author
func (r *EarningsRepository) GetEarningsSummary(
	ctx context.Context,
	authorID uuid.UUID,
) (*domain.EarningsSummary, error) {
	// Get earnings stats
	earningsQuery := `
		SELECT COUNT(*), COALESCE(SUM(sale_amount_cents), 0),
		       COALESCE(SUM(commission_cents), 0), COALESCE(SUM(author_earning_cents), 0)
		FROM author_earnings
		WHERE author_id = $1 AND status = 'completed'
	`

	var summary domain.EarningsSummary
	err := r.db.QueryRow(ctx, earningsQuery, authorID).Scan(
		&summary.TotalSales, &summary.TotalRevenue,
		&summary.TotalCommission, &summary.TotalEarnings,
	)
	if err != nil {
		return nil, err
	}

	// Get balance info
	balance, err := r.GetAuthorBalance(ctx, authorID)
	if err != nil {
		return nil, err
	}
	summary.AvailableBalance = balance.AvailableBalanceCents
	summary.PendingPayout = balance.PendingPayoutCents

	return &summary, nil
}
