package repository

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

// SubscriptionRepository implements domain.SubscriptionRepository
type SubscriptionRepository struct {
	db *pgxpool.Pool
}

// NewSubscriptionRepository creates a new subscription repository
func NewSubscriptionRepository(db *pgxpool.Pool) *SubscriptionRepository {
	return &SubscriptionRepository{db: db}
}

// Create creates a new subscription
func (r *SubscriptionRepository) Create(ctx context.Context, sub *domain.Subscription) error {
	query := `
		INSERT INTO subscriptions (
			id, office_id, tier, status, billing_interval,
			stripe_customer_id, stripe_subscription_id, stripe_price_id,
			current_period_start, current_period_end, cancel_at_period_end,
			metadata, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
		)
	`

	if sub.ID == uuid.Nil {
		sub.ID = uuid.New()
	}
	now := time.Now()
	sub.CreatedAt = now
	sub.UpdatedAt = now

	_, err := r.db.Exec(ctx, query,
		sub.ID, sub.OfficeID, sub.Tier, sub.Status, sub.BillingInterval,
		sub.StripeCustomerID, sub.StripeSubscriptionID, sub.StripePriceID,
		sub.CurrentPeriodStart, sub.CurrentPeriodEnd, sub.CancelAtPeriodEnd,
		sub.Metadata, sub.CreatedAt, sub.UpdatedAt,
	)
	return err
}

// GetByID retrieves a subscription by ID
func (r *SubscriptionRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Subscription, error) {
	query := `
		SELECT id, office_id, tier, status, billing_interval,
		       stripe_customer_id, stripe_subscription_id, stripe_price_id,
		       current_period_start, current_period_end, cancel_at_period_end,
		       cancelled_at, trial_start, trial_end, metadata, created_at, updated_at
		FROM subscriptions
		WHERE id = $1
	`

	var sub domain.Subscription
	var stripeCustomerID, stripeSubscriptionID, stripePriceID *string
	err := r.db.QueryRow(ctx, query, id).Scan(
		&sub.ID, &sub.OfficeID, &sub.Tier, &sub.Status, &sub.BillingInterval,
		&stripeCustomerID, &stripeSubscriptionID, &stripePriceID,
		&sub.CurrentPeriodStart, &sub.CurrentPeriodEnd, &sub.CancelAtPeriodEnd,
		&sub.CancelledAt, &sub.TrialStart, &sub.TrialEnd, &sub.Metadata,
		&sub.CreatedAt, &sub.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}

	// Convert nullable strings
	if stripeCustomerID != nil {
		sub.StripeCustomerID = *stripeCustomerID
	}
	if stripeSubscriptionID != nil {
		sub.StripeSubscriptionID = *stripeSubscriptionID
	}
	if stripePriceID != nil {
		sub.StripePriceID = *stripePriceID
	}

	return &sub, nil
}

// GetByOfficeID retrieves a subscription by office ID
func (r *SubscriptionRepository) GetByOfficeID(ctx context.Context, officeID uuid.UUID) (*domain.Subscription, error) {
	query := `
		SELECT id, office_id, tier, status, billing_interval,
		       stripe_customer_id, stripe_subscription_id, stripe_price_id,
		       current_period_start, current_period_end, cancel_at_period_end,
		       cancelled_at, trial_start, trial_end, metadata, created_at, updated_at
		FROM subscriptions
		WHERE office_id = $1
	`

	var sub domain.Subscription
	var stripeCustomerID, stripeSubscriptionID, stripePriceID *string
	err := r.db.QueryRow(ctx, query, officeID).Scan(
		&sub.ID, &sub.OfficeID, &sub.Tier, &sub.Status, &sub.BillingInterval,
		&stripeCustomerID, &stripeSubscriptionID, &stripePriceID,
		&sub.CurrentPeriodStart, &sub.CurrentPeriodEnd, &sub.CancelAtPeriodEnd,
		&sub.CancelledAt, &sub.TrialStart, &sub.TrialEnd, &sub.Metadata,
		&sub.CreatedAt, &sub.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}

	// Convert nullable strings
	if stripeCustomerID != nil {
		sub.StripeCustomerID = *stripeCustomerID
	}
	if stripeSubscriptionID != nil {
		sub.StripeSubscriptionID = *stripeSubscriptionID
	}
	if stripePriceID != nil {
		sub.StripePriceID = *stripePriceID
	}

	return &sub, nil
}

// GetByStripeID retrieves a subscription by Stripe subscription ID
func (r *SubscriptionRepository) GetByStripeID(ctx context.Context, stripeID string) (*domain.Subscription, error) {
	query := `
		SELECT id, office_id, tier, status, billing_interval,
		       stripe_customer_id, stripe_subscription_id, stripe_price_id,
		       current_period_start, current_period_end, cancel_at_period_end,
		       cancelled_at, trial_start, trial_end, metadata, created_at, updated_at
		FROM subscriptions
		WHERE stripe_subscription_id = $1
	`

	var sub domain.Subscription
	var stripeCustomerID, stripeSubscriptionID, stripePriceID *string
	err := r.db.QueryRow(ctx, query, stripeID).Scan(
		&sub.ID, &sub.OfficeID, &sub.Tier, &sub.Status, &sub.BillingInterval,
		&stripeCustomerID, &stripeSubscriptionID, &stripePriceID,
		&sub.CurrentPeriodStart, &sub.CurrentPeriodEnd, &sub.CancelAtPeriodEnd,
		&sub.CancelledAt, &sub.TrialStart, &sub.TrialEnd, &sub.Metadata,
		&sub.CreatedAt, &sub.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}

	// Convert nullable strings
	if stripeCustomerID != nil {
		sub.StripeCustomerID = *stripeCustomerID
	}
	if stripeSubscriptionID != nil {
		sub.StripeSubscriptionID = *stripeSubscriptionID
	}
	if stripePriceID != nil {
		sub.StripePriceID = *stripePriceID
	}

	return &sub, nil
}

// Update updates a subscription
func (r *SubscriptionRepository) Update(ctx context.Context, sub *domain.Subscription) error {
	query := `
		UPDATE subscriptions SET
			tier = $2, status = $3, billing_interval = $4,
			stripe_customer_id = $5, stripe_subscription_id = $6, stripe_price_id = $7,
			current_period_start = $8, current_period_end = $9, cancel_at_period_end = $10,
			cancelled_at = $11, metadata = $12, updated_at = NOW()
		WHERE id = $1
	`

	_, err := r.db.Exec(ctx, query,
		sub.ID, sub.Tier, sub.Status, sub.BillingInterval,
		sub.StripeCustomerID, sub.StripeSubscriptionID, sub.StripePriceID,
		sub.CurrentPeriodStart, sub.CurrentPeriodEnd, sub.CancelAtPeriodEnd,
		sub.CancelledAt, sub.Metadata,
	)
	return err
}

// UpdateStatus updates only the subscription status
func (r *SubscriptionRepository) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.SubscriptionStatus) error {
	query := `UPDATE subscriptions SET status = $2, updated_at = NOW() WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id, status)
	return err
}

// UpdateTier updates only the subscription tier
func (r *SubscriptionRepository) UpdateTier(ctx context.Context, id uuid.UUID, tier domain.SubscriptionTier) error {
	query := `UPDATE subscriptions SET tier = $2, updated_at = NOW() WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id, tier)
	return err
}

// CreateAllocation creates a new credit allocation
func (r *SubscriptionRepository) CreateAllocation(ctx context.Context, alloc *domain.CreditAllocation) error {
	query := `
		INSERT INTO credit_allocations (
			id, subscription_id, wallet_id, period_start, period_end,
			credits_allocated, credits_consumed, rollover_credits, source, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`

	if alloc.ID == uuid.Nil {
		alloc.ID = uuid.New()
	}
	alloc.CreatedAt = time.Now()

	_, err := r.db.Exec(ctx, query,
		alloc.ID, alloc.SubscriptionID, alloc.WalletID,
		alloc.PeriodStart, alloc.PeriodEnd,
		alloc.CreditsAllocated, alloc.CreditsConsumed, alloc.RolloverCredits,
		alloc.Source, alloc.CreatedAt,
	)
	return err
}

// GetCurrentAllocation gets the current period's allocation for a subscription
func (r *SubscriptionRepository) GetCurrentAllocation(ctx context.Context, subID uuid.UUID) (*domain.CreditAllocation, error) {
	query := `
		SELECT id, subscription_id, wallet_id, period_start, period_end,
		       credits_allocated, credits_consumed, rollover_credits, source, created_at
		FROM credit_allocations
		WHERE subscription_id = $1 AND NOW() BETWEEN period_start AND period_end
		ORDER BY period_start DESC
		LIMIT 1
	`

	var alloc domain.CreditAllocation
	err := r.db.QueryRow(ctx, query, subID).Scan(
		&alloc.ID, &alloc.SubscriptionID, &alloc.WalletID,
		&alloc.PeriodStart, &alloc.PeriodEnd,
		&alloc.CreditsAllocated, &alloc.CreditsConsumed, &alloc.RolloverCredits,
		&alloc.Source, &alloc.CreatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &alloc, nil
}

// GetAllocationsBySubscription gets allocations for a subscription
func (r *SubscriptionRepository) GetAllocationsBySubscription(ctx context.Context, subID uuid.UUID, limit int) ([]*domain.CreditAllocation, error) {
	query := `
		SELECT id, subscription_id, wallet_id, period_start, period_end,
		       credits_allocated, credits_consumed, rollover_credits, source, created_at
		FROM credit_allocations
		WHERE subscription_id = $1
		ORDER BY period_start DESC
		LIMIT $2
	`

	rows, err := r.db.Query(ctx, query, subID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var allocations []*domain.CreditAllocation
	for rows.Next() {
		var alloc domain.CreditAllocation
		if err := rows.Scan(
			&alloc.ID, &alloc.SubscriptionID, &alloc.WalletID,
			&alloc.PeriodStart, &alloc.PeriodEnd,
			&alloc.CreditsAllocated, &alloc.CreditsConsumed, &alloc.RolloverCredits,
			&alloc.Source, &alloc.CreatedAt,
		); err != nil {
			return nil, err
		}
		allocations = append(allocations, &alloc)
	}
	return allocations, rows.Err()
}

// UpdateAllocationConsumed updates the consumed credits for an allocation
func (r *SubscriptionRepository) UpdateAllocationConsumed(ctx context.Context, allocID uuid.UUID, consumed int64) error {
	query := `UPDATE credit_allocations SET credits_consumed = $2 WHERE id = $1`
	_, err := r.db.Exec(ctx, query, allocID, consumed)
	return err
}
