package domain

import (
	"time"

	"github.com/google/uuid"
)

// User represents the Boss (human user) of an office
type User struct {
	ID           uuid.UUID `json:"id"`
	Email        string    `json:"email"`
	PasswordHash string    `json:"-"` // Never expose password hash
	Name         string    `json:"name"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

// Office represents a virtual workspace owned by a user
type Office struct {
	ID        uuid.UUID `json:"id"`
	UserID    uuid.UUID `json:"user_id"`
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// AgentTemplate represents a predefined agent type (extended for marketplace)
type AgentTemplate struct {
	ID           uuid.UUID `json:"id"`
	Name         string    `json:"name"`
	Role         string    `json:"role"`
	SystemPrompt string    `json:"system_prompt"`
	AvatarURL    string    `json:"avatar_url"`
	SkillTags    []string  `json:"skill_tags"`
	// Marketplace fields
	AuthorID      *uuid.UUID `json:"author_id,omitempty"`
	AuthorName    string     `json:"author_name"`
	Category      string     `json:"category"`
	Description   string     `json:"description"`
	IsFeatured    bool       `json:"is_featured"`
	IsPublic      bool       `json:"is_public"`
	IsPremium     bool       `json:"is_premium"`
	PriceCents    int        `json:"price_cents"`
	DownloadCount int        `json:"download_count"`
	RatingAverage float64    `json:"rating_average"`
	RatingCount   int        `json:"rating_count"`
	Version       string     `json:"version"`
	Status        string     `json:"status"` // pending, approved, rejected
	CreatedAt     time.Time  `json:"created_at"`
	UpdatedAt     time.Time  `json:"updated_at"`
}

// AgentCategory represents a marketplace category
type AgentCategory struct {
	ID           uuid.UUID `json:"id"`
	Name         string    `json:"name"`
	Slug         string    `json:"slug"`
	Description  string    `json:"description"`
	Icon         string    `json:"icon"`
	DisplayOrder int       `json:"display_order"`
	CreatedAt    time.Time `json:"created_at"`
}

// AgentReview represents a user review of an agent template
type AgentReview struct {
	ID         uuid.UUID `json:"id"`
	TemplateID uuid.UUID `json:"template_id"`
	UserID     uuid.UUID `json:"user_id"`
	Rating     int       `json:"rating"`
	Title      string    `json:"title,omitempty"`
	ReviewText string    `json:"review_text"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

// Agent represents an AI agent selected for an office
type Agent struct {
	ID                 uuid.UUID      `json:"id"`
	OfficeID           uuid.UUID      `json:"office_id"`
	TemplateID         uuid.UUID      `json:"template_id"`
	Template           *AgentTemplate `json:"template,omitempty"`
	CustomName         string         `json:"custom_name,omitempty"`
	CustomSystemPrompt string         `json:"custom_system_prompt,omitempty"`
	IsActive           bool           `json:"is_active"`
	CreatedAt          time.Time      `json:"created_at"`
	UpdatedAt          time.Time      `json:"updated_at"`
}

// GetName returns the agent's display name (custom or template name)
func (a *Agent) GetName() string {
	if a.CustomName != "" {
		return a.CustomName
	}
	if a.Template != nil {
		return a.Template.Name
	}
	return ""
}

// GetSystemPrompt returns the agent's system prompt (custom or template prompt)
func (a *Agent) GetSystemPrompt() string {
	if a.CustomSystemPrompt != "" {
		return a.CustomSystemPrompt
	}
	if a.Template != nil {
		return a.Template.SystemPrompt
	}
	return ""
}

// ConversationType defines the type of conversation
type ConversationType string

const (
	ConversationTypeDirect ConversationType = "direct"
	ConversationTypeGroup  ConversationType = "group"
)

// Conversation represents a chat thread
type Conversation struct {
	ID           uuid.UUID        `json:"id"`
	OfficeID     uuid.UUID        `json:"office_id"`
	Type         ConversationType `json:"type"`
	Name         string           `json:"name,omitempty"`
	Participants []*Agent         `json:"participants,omitempty"`
	CreatedAt    time.Time        `json:"created_at"`
	UpdatedAt    time.Time        `json:"updated_at"`
}

// SenderType defines who sent a message
type SenderType string

const (
	SenderTypeUser  SenderType = "user"
	SenderTypeAgent SenderType = "agent"
)

// Message represents a chat message
type Message struct {
	ID             uuid.UUID      `json:"id"`
	OfficeID       uuid.UUID      `json:"office_id"`
	ConversationID uuid.UUID      `json:"conversation_id"`
	SenderType     SenderType     `json:"sender_type"`
	SenderID       uuid.UUID      `json:"sender_id"`
	Content        string         `json:"content"`
	Metadata       map[string]any `json:"metadata,omitempty"`
	CreatedAt      time.Time      `json:"created_at"`
}

// TaskStatus defines the current status of a task
type TaskStatus string

const (
	TaskStatusPending  TaskStatus = "pending"
	TaskStatusThinking TaskStatus = "thinking"
	TaskStatusWorking  TaskStatus = "working"
	TaskStatusDone     TaskStatus = "done"
	TaskStatusFailed   TaskStatus = "failed"
)

// Task represents a task assigned to an agent
type Task struct {
	ID             uuid.UUID      `json:"id"`
	OfficeID       uuid.UUID      `json:"office_id"`
	ConversationID uuid.UUID      `json:"conversation_id,omitempty"`
	MessageID      uuid.UUID      `json:"message_id,omitempty"`
	AgentID        uuid.UUID      `json:"agent_id"`
	Agent          *Agent         `json:"agent,omitempty"`
	Status         TaskStatus     `json:"status"`
	Input          string         `json:"input"`
	Output         string         `json:"output,omitempty"`
	Error          string         `json:"error,omitempty"`
	TokenUsage     map[string]int `json:"token_usage,omitempty"`
	StartedAt      *time.Time     `json:"started_at,omitempty"`
	CompletedAt    *time.Time     `json:"completed_at,omitempty"`
	CreatedAt      time.Time      `json:"created_at"`
}

// AgentMemory represents long-term memory for an agent
type AgentMemory struct {
	ID              uuid.UUID      `json:"id"`
	OfficeID        uuid.UUID      `json:"office_id"`
	AgentID         uuid.UUID      `json:"agent_id"`
	Key             string         `json:"key"`
	Value           string         `json:"value"`
	VectorID        string         `json:"vector_id,omitempty"`
	MemoryType      string         `json:"memory_type"` // fact, preference, correction, insight
	ImportanceScore float64        `json:"importance_score"`
	Source          string         `json:"source"` // system, conversation, feedback, extraction
	SourceID        *uuid.UUID     `json:"source_id,omitempty"`
	Metadata        map[string]any `json:"metadata,omitempty"`
	CreatedAt       time.Time      `json:"created_at"`
	UpdatedAt       time.Time      `json:"updated_at"`
}

// FeedbackType defines the type of user feedback
type FeedbackType string

const (
	FeedbackTypePositive   FeedbackType = "positive"
	FeedbackTypeNegative   FeedbackType = "negative"
	FeedbackTypeCorrection FeedbackType = "correction"
)

// AgentFeedback represents user feedback on agent responses
type AgentFeedback struct {
	ID                uuid.UUID    `json:"id"`
	OfficeID          uuid.UUID    `json:"office_id"`
	AgentID           uuid.UUID    `json:"agent_id"`
	MessageID         *uuid.UUID   `json:"message_id,omitempty"`
	TaskID            *uuid.UUID   `json:"task_id,omitempty"`
	FeedbackType      FeedbackType `json:"feedback_type"`
	Rating            int          `json:"rating,omitempty"` // 1-5 scale
	Comment           string       `json:"comment,omitempty"`
	OriginalContent   string       `json:"original_content,omitempty"`
	CorrectionContent string       `json:"correction_content,omitempty"`
	CreatedAt         time.Time    `json:"created_at"`
}

// AgentLearningStats represents learning metrics for an agent
type AgentLearningStats struct {
	ID                    uuid.UUID `json:"id"`
	AgentID               uuid.UUID `json:"agent_id"`
	FactCount             int       `json:"fact_count"`
	PreferenceCount       int       `json:"preference_count"`
	CorrectionCount       int       `json:"correction_count"`
	InsightCount          int       `json:"insight_count"`
	PositiveFeedbackCount int       `json:"positive_feedback_count"`
	NegativeFeedbackCount int       `json:"negative_feedback_count"`
	AverageRating         float64   `json:"average_rating"`
	TotalInteractions     int       `json:"total_interactions"`
	CreatedAt             time.Time `json:"created_at"`
	UpdatedAt             time.Time `json:"updated_at"`
}

// =============================================================================
// Credit System Entities (Monetization)
// =============================================================================

// CreditWallet represents the credit balance for an office
type CreditWallet struct {
	ID             uuid.UUID `json:"id"`
	OfficeID       uuid.UUID `json:"office_id"`
	Balance        int64     `json:"balance"`         // Current credit balance
	TotalPurchased int64     `json:"total_purchased"` // Lifetime purchased credits
	TotalBonus     int64     `json:"total_bonus"`     // Lifetime bonus credits
	TotalConsumed  int64     `json:"total_consumed"`  // Lifetime consumed credits
	// Budget controls (Phase 2)
	HourlyLimit          *int64    `json:"hourly_limit,omitempty"` // Max credits per hour
	DailyLimit           *int64    `json:"daily_limit,omitempty"`  // Max credits per day
	BudgetAlertThreshold int       `json:"budget_alert_threshold"` // Alert at X% remaining
	BudgetPauseEnabled   bool      `json:"budget_pause_enabled"`   // Pause when limit hit
	CreatedAt            time.Time `json:"created_at"`
	UpdatedAt            time.Time `json:"updated_at"`
}

// CreditUsageHourly tracks hourly credit consumption for rate limiting
type CreditUsageHourly struct {
	ID              uuid.UUID `json:"id"`
	WalletID        uuid.UUID `json:"wallet_id"`
	HourStart       time.Time `json:"hour_start"`
	CreditsConsumed int64     `json:"credits_consumed"`
	TaskCount       int       `json:"task_count"`
	LocalModelCount int       `json:"local_model_count"` // For optimization ratio
	PaidModelCount  int       `json:"paid_model_count"`
	CreatedAt       time.Time `json:"created_at"`
}

// BudgetCheckResult represents the result of a budget limit check
type BudgetCheckResult struct {
	Allowed         bool   `json:"allowed"`
	Reason          string `json:"reason,omitempty"`
	HourlyRemaining *int64 `json:"hourly_remaining,omitempty"`
	DailyRemaining  *int64 `json:"daily_remaining,omitempty"`
}

// TransactionType defines the type of credit transaction
type TransactionType string

const (
	TransactionTypeSubscription TransactionType = "subscription" // Monthly allocation
	TransactionTypePurchase     TransactionType = "purchase"     // Add-on purchase
	TransactionTypeBonus        TransactionType = "bonus"        // Promotional credits
	TransactionTypeConsumption  TransactionType = "consumption"  // Task execution deduction
	TransactionTypeRefund       TransactionType = "refund"       // Credit reversal
	TransactionTypeAdjustment   TransactionType = "adjustment"   // Admin adjustment
)

// CreditTransaction represents a credit ledger entry (immutable audit trail)
type CreditTransaction struct {
	ID            uuid.UUID       `json:"id"`
	WalletID      uuid.UUID       `json:"wallet_id"`
	Type          TransactionType `json:"transaction_type"`
	Amount        int64           `json:"amount"`                   // Positive=credit, Negative=debit
	BalanceAfter  int64           `json:"balance_after"`            // Snapshot for audit
	ReferenceType string          `json:"reference_type,omitempty"` // 'task', 'subscription', 'purchase'
	ReferenceID   *uuid.UUID      `json:"reference_id,omitempty"`   // Link to source entity
	Description   string          `json:"description,omitempty"`
	Metadata      map[string]any  `json:"metadata,omitempty"`
	CreatedAt     time.Time       `json:"created_at"`
}

// =============================================================================
// Subscription System Entities (Phase 3)
// =============================================================================

// SubscriptionStatus represents the state of a subscription
type SubscriptionStatus string

const (
	SubscriptionStatusActive    SubscriptionStatus = "active"
	SubscriptionStatusCancelled SubscriptionStatus = "cancelled"
	SubscriptionStatusPastDue   SubscriptionStatus = "past_due"
	SubscriptionStatusTrialing  SubscriptionStatus = "trialing"
	SubscriptionStatusPaused    SubscriptionStatus = "paused"
	SubscriptionStatusUnpaid    SubscriptionStatus = "unpaid"
)

// BillingInterval represents the billing cycle
type BillingInterval string

const (
	BillingIntervalMonthly BillingInterval = "monthly"
	BillingIntervalYearly  BillingInterval = "yearly"
)

// SubscriptionTier represents the tier name
type SubscriptionTier string

const (
	TierSolo         SubscriptionTier = "solo"
	TierProfessional SubscriptionTier = "professional"
	TierBusiness     SubscriptionTier = "business"
	TierEnterprise   SubscriptionTier = "enterprise"
)

// Subscription represents an office's subscription
type Subscription struct {
	ID                   uuid.UUID          `json:"id"`
	OfficeID             uuid.UUID          `json:"office_id"`
	Tier                 SubscriptionTier   `json:"tier"`
	Status               SubscriptionStatus `json:"status"`
	BillingInterval      BillingInterval    `json:"billing_interval"`
	StripeCustomerID     string             `json:"stripe_customer_id,omitempty"`
	StripeSubscriptionID string             `json:"stripe_subscription_id,omitempty"`
	StripePriceID        string             `json:"stripe_price_id,omitempty"`
	CurrentPeriodStart   time.Time          `json:"current_period_start"`
	CurrentPeriodEnd     time.Time          `json:"current_period_end"`
	CancelAtPeriodEnd    bool               `json:"cancel_at_period_end"`
	CancelledAt          *time.Time         `json:"cancelled_at,omitempty"`
	TrialStart           *time.Time         `json:"trial_start,omitempty"`
	TrialEnd             *time.Time         `json:"trial_end,omitempty"`
	Metadata             map[string]any     `json:"metadata,omitempty"`
	CreatedAt            time.Time          `json:"created_at"`
	UpdatedAt            time.Time          `json:"updated_at"`
}

// CreditAllocation represents credits allocated per billing period
type CreditAllocation struct {
	ID               uuid.UUID `json:"id"`
	SubscriptionID   uuid.UUID `json:"subscription_id"`
	WalletID         uuid.UUID `json:"wallet_id"`
	PeriodStart      time.Time `json:"period_start"`
	PeriodEnd        time.Time `json:"period_end"`
	CreditsAllocated int64     `json:"credits_allocated"`
	CreditsConsumed  int64     `json:"credits_consumed"`
	RolloverCredits  int64     `json:"rollover_credits"`
	Source           string    `json:"source"` // 'subscription', 'purchase', 'bonus'
	CreatedAt        time.Time `json:"created_at"`
}

// TierFeatures defines the capabilities of a subscription tier
type TierFeatures struct {
	MaxAgents             int      `json:"max_agents" yaml:"max_agents"`
	MonthlyCredits        int64    `json:"monthly_credits" yaml:"monthly_credits"`
	MaxSeats              int      `json:"max_seats" yaml:"max_seats"`
	ModelAccess           []string `json:"model_access" yaml:"model_access"`
	Priority              string   `json:"priority" yaml:"priority"`
	RetentionDays         int      `json:"retention_days" yaml:"retention_days"`
	WebResearch           bool     `json:"web_research" yaml:"web_research"`
	AdvancedOrchestration bool     `json:"advanced_orchestration" yaml:"advanced_orchestration"`
	Analytics             bool     `json:"analytics" yaml:"analytics"`
	APIAccess             bool     `json:"api_access" yaml:"api_access"`
	SLA                   bool     `json:"sla,omitempty" yaml:"sla"`
	DedicatedSupport      bool     `json:"dedicated_support,omitempty" yaml:"dedicated_support"`
	OnPremiseOption       bool     `json:"on_premise_option,omitempty" yaml:"on_premise_option"`
}

// TierDefinition defines a subscription tier's config
type TierDefinition struct {
	Name                 string       `json:"name" yaml:"name"`
	Description          string       `json:"description" yaml:"description"`
	PriceMonthlyUSD      *float64     `json:"price_monthly_usd" yaml:"price_monthly_usd"`
	PriceYearlyUSD       *float64     `json:"price_yearly_usd" yaml:"price_yearly_usd"`
	StripePriceIDMonthly string       `json:"stripe_price_id_monthly" yaml:"stripe_price_id_monthly"`
	StripePriceIDYearly  string       `json:"stripe_price_id_yearly" yaml:"stripe_price_id_yearly"`
	Features             TierFeatures `json:"features" yaml:"features"`
}

// SubscriptionSummary combines subscription with current usage
type SubscriptionSummary struct {
	Subscription           *Subscription   `json:"subscription"`
	Tier                   *TierDefinition `json:"tier_definition"`
	CurrentBalance         int64           `json:"current_balance"`
	PeriodCreditsAllocated int64           `json:"period_credits_allocated"`
	PeriodCreditsConsumed  int64           `json:"period_credits_consumed"`
	DaysRemaining          int             `json:"days_remaining"`
}

// =============================================================================
// Analytics & Usage Entities (Phase 4)
// =============================================================================

// UsageDaily represents daily usage aggregation
type UsageDaily struct {
	ID              uuid.UUID `json:"id"`
	OfficeID        uuid.UUID `json:"office_id"`
	Date            string    `json:"date"` // YYYY-MM-DD format
	CreditsConsumed int64     `json:"credits_consumed"`
	TasksExecuted   int       `json:"tasks_executed"`
	TasksSucceeded  int       `json:"tasks_succeeded"`
	TasksFailed     int       `json:"tasks_failed"`
	InputTokens     int64     `json:"input_tokens"`
	OutputTokens    int64     `json:"output_tokens"`
	TotalTokens     int64     `json:"total_tokens"`
	LocalModelTasks int       `json:"local_model_tasks"`
	PaidModelTasks  int       `json:"paid_model_tasks"`
	EstimatedUSD    float64   `json:"estimated_usd"`
}

// UsageByModel represents usage aggregated by model
type UsageByModel struct {
	ID              uuid.UUID `json:"id"`
	OfficeID        uuid.UUID `json:"office_id"`
	Date            string    `json:"date"`
	ModelName       string    `json:"model_name"`
	Provider        string    `json:"provider"`
	TaskCount       int       `json:"task_count"`
	CreditsConsumed int64     `json:"credits_consumed"`
	InputTokens     int64     `json:"input_tokens"`
	OutputTokens    int64     `json:"output_tokens"`
	EstimatedUSD    float64   `json:"estimated_usd"`
	AvgLatencyMs    int       `json:"avg_latency_ms"`
}

// UsageByAgent represents usage aggregated by agent
type UsageByAgent struct {
	ID              uuid.UUID `json:"id"`
	OfficeID        uuid.UUID `json:"office_id"`
	Date            string    `json:"date"`
	AgentID         uuid.UUID `json:"agent_id"`
	AgentRole       string    `json:"agent_role"`
	TaskCount       int       `json:"task_count"`
	CreditsConsumed int64     `json:"credits_consumed"`
	InputTokens     int64     `json:"input_tokens"`
	OutputTokens    int64     `json:"output_tokens"`
	AvgScore        *float64  `json:"avg_score,omitempty"`
}

// UsageSummary represents a summary of usage for an office
type UsageSummary struct {
	Period           string  `json:"period"` // "30d", "7d", "today"
	CreditsUsed      int64   `json:"credits_used"`
	CreditsRemaining int64   `json:"credits_remaining"`
	TasksExecuted    int     `json:"tasks_executed"`
	TasksSucceeded   int     `json:"tasks_succeeded"`
	TasksFailed      int     `json:"tasks_failed"`
	TokensProcessed  int64   `json:"tokens_processed"`
	EstimatedCostUSD float64 `json:"estimated_cost_usd"`
	LocalModelRatio  float64 `json:"local_model_ratio"` // % of tasks using free local models
}

// UsageBreakdown represents detailed usage breakdown
type UsageBreakdown struct {
	ByModel []UsageByModel `json:"by_model"`
	ByAgent []UsageByAgent `json:"by_agent"`
	ByDay   []UsageDaily   `json:"by_day"`
}

// AgentUsageStats represents usage stats for a single agent
type AgentUsageStats struct {
	AgentID        uuid.UUID `json:"agent_id"`
	AgentName      string    `json:"agent_name"`
	AgentRole      string    `json:"agent_role"`
	TotalTasks     int       `json:"total_tasks"`
	TotalCredits   int64     `json:"total_credits"`
	TotalTokens    int64     `json:"total_tokens"`
	PercentOfUsage float64   `json:"percent_of_usage"`
}

// ModelUsageStats represents usage stats for a single model
type ModelUsageStats struct {
	ModelName      string  `json:"model_name"`
	Provider       string  `json:"provider"`
	TotalTasks     int     `json:"total_tasks"`
	TotalCredits   int64   `json:"total_credits"`
	TotalTokens    int64   `json:"total_tokens"`
	EstimatedUSD   float64 `json:"estimated_usd"`
	PercentOfUsage float64 `json:"percent_of_usage"`
}

// =============================================================================
// Marketplace Revenue Entities (Phase 6)
// =============================================================================

// PayoutStatus represents the status of a payout request
type PayoutStatus string

const (
	PayoutStatusPending    PayoutStatus = "pending"
	PayoutStatusProcessing PayoutStatus = "processing"
	PayoutStatusCompleted  PayoutStatus = "completed"
	PayoutStatusFailed     PayoutStatus = "failed"
)

// AuthorEarning represents a single sale earning for an author
type AuthorEarning struct {
	ID                    uuid.UUID `json:"id"`
	AuthorID              uuid.UUID `json:"author_id"`
	TemplateID            uuid.UUID `json:"template_id"`
	PurchaserID           uuid.UUID `json:"purchaser_id"`
	PurchaserOfficeID     uuid.UUID `json:"purchaser_office_id"`
	SaleAmountCents       int       `json:"sale_amount_cents"`
	CommissionCents       int       `json:"commission_cents"`
	AuthorEarningCents    int       `json:"author_earning_cents"`
	StripePaymentIntentID string    `json:"stripe_payment_intent_id,omitempty"`
	Status                string    `json:"status"`
	CreatedAt             time.Time `json:"created_at"`
}

// PayoutRequest represents an author's payout request
type PayoutRequest struct {
	ID               uuid.UUID    `json:"id"`
	AuthorID         uuid.UUID    `json:"author_id"`
	AmountCents      int          `json:"amount_cents"`
	Status           PayoutStatus `json:"status"`
	StripeTransferID string       `json:"stripe_transfer_id,omitempty"`
	FailureReason    string       `json:"failure_reason,omitempty"`
	CreatedAt        time.Time    `json:"created_at"`
	ProcessedAt      *time.Time   `json:"processed_at,omitempty"`
}

// AuthorBalance represents an author's earnings balance
type AuthorBalance struct {
	AuthorID              uuid.UUID `json:"author_id"`
	TotalEarnedCents      int64     `json:"total_earned_cents"`
	TotalPaidOutCents     int64     `json:"total_paid_out_cents"`
	PendingPayoutCents    int64     `json:"pending_payout_cents"`
	AvailableBalanceCents int64     `json:"available_balance_cents"`
	UpdatedAt             time.Time `json:"updated_at"`
}

// EarningsSummary represents a summary of author earnings
type EarningsSummary struct {
	TotalSales       int   `json:"total_sales"`
	TotalRevenue     int64 `json:"total_revenue_cents"`
	TotalCommission  int64 `json:"total_commission_cents"`
	TotalEarnings    int64 `json:"total_earnings_cents"`
	AvailableBalance int64 `json:"available_balance_cents"`
	PendingPayout    int64 `json:"pending_payout_cents"`
}

// PurchaseRequest represents a marketplace purchase request
type PurchaseRequest struct {
	TemplateID uuid.UUID `json:"template_id"`
	OfficeID   uuid.UUID `json:"office_id"`
	UserID     uuid.UUID `json:"user_id"`
}
