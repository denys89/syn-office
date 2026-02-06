package repository

import (
	"context"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

// AnalyticsRepository implements analytics data access
type AnalyticsRepository struct {
	db *pgxpool.Pool
}

// NewAnalyticsRepository creates a new analytics repository
func NewAnalyticsRepository(db *pgxpool.Pool) *AnalyticsRepository {
	return &AnalyticsRepository{db: db}
}

// GetDailyUsage retrieves daily usage for an office within a date range
func (r *AnalyticsRepository) GetDailyUsage(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageDaily, error) {
	query := `
		SELECT id, office_id, date, credits_consumed, tasks_executed, 
		       tasks_succeeded, tasks_failed, input_tokens, output_tokens, 
		       total_tokens, local_model_tasks, paid_model_tasks, estimated_usd
		FROM usage_daily
		WHERE office_id = $1 AND date >= CURRENT_DATE - $2 * INTERVAL '1 day'
		ORDER BY date DESC
	`

	rows, err := r.db.Query(ctx, query, officeID, days)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []domain.UsageDaily
	for rows.Next() {
		var u domain.UsageDaily
		var date time.Time
		if err := rows.Scan(
			&u.ID, &u.OfficeID, &date, &u.CreditsConsumed,
			&u.TasksExecuted, &u.TasksSucceeded, &u.TasksFailed,
			&u.InputTokens, &u.OutputTokens, &u.TotalTokens,
			&u.LocalModelTasks, &u.PaidModelTasks, &u.EstimatedUSD,
		); err != nil {
			return nil, err
		}
		u.Date = date.Format("2006-01-02")
		results = append(results, u)
	}
	return results, rows.Err()
}

// GetUsageByModel retrieves model usage breakdown for an office
func (r *AnalyticsRepository) GetUsageByModel(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageByModel, error) {
	query := `
		SELECT model_name, provider, 
		       SUM(task_count) as task_count,
		       SUM(credits_consumed) as credits_consumed,
		       SUM(input_tokens) as input_tokens,
		       SUM(output_tokens) as output_tokens,
		       SUM(estimated_usd) as estimated_usd,
		       AVG(avg_latency_ms) as avg_latency_ms
		FROM usage_by_model
		WHERE office_id = $1 AND date >= CURRENT_DATE - $2 * INTERVAL '1 day'
		GROUP BY model_name, provider
		ORDER BY credits_consumed DESC
	`

	rows, err := r.db.Query(ctx, query, officeID, days)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []domain.UsageByModel
	for rows.Next() {
		var u domain.UsageByModel
		u.OfficeID = officeID
		if err := rows.Scan(
			&u.ModelName, &u.Provider, &u.TaskCount,
			&u.CreditsConsumed, &u.InputTokens, &u.OutputTokens,
			&u.EstimatedUSD, &u.AvgLatencyMs,
		); err != nil {
			return nil, err
		}
		results = append(results, u)
	}
	return results, rows.Err()
}

// GetUsageByAgent retrieves agent usage breakdown for an office
func (r *AnalyticsRepository) GetUsageByAgent(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) ([]domain.UsageByAgent, error) {
	query := `
		SELECT agent_id, agent_role,
		       SUM(task_count) as task_count,
		       SUM(credits_consumed) as credits_consumed,
		       SUM(input_tokens) as input_tokens,
		       SUM(output_tokens) as output_tokens,
		       AVG(avg_score) as avg_score
		FROM usage_by_agent
		WHERE office_id = $1 AND date >= CURRENT_DATE - $2 * INTERVAL '1 day'
		GROUP BY agent_id, agent_role
		ORDER BY credits_consumed DESC
	`

	rows, err := r.db.Query(ctx, query, officeID, days)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []domain.UsageByAgent
	for rows.Next() {
		var u domain.UsageByAgent
		u.OfficeID = officeID
		if err := rows.Scan(
			&u.AgentID, &u.AgentRole, &u.TaskCount,
			&u.CreditsConsumed, &u.InputTokens, &u.OutputTokens,
			&u.AvgScore,
		); err != nil {
			return nil, err
		}
		results = append(results, u)
	}
	return results, rows.Err()
}

// GetUsageSummary retrieves aggregated usage summary
func (r *AnalyticsRepository) GetUsageSummary(
	ctx context.Context,
	officeID uuid.UUID,
	days int,
) (*domain.UsageSummary, error) {
	query := `
		SELECT 
		    COALESCE(SUM(credits_consumed), 0),
		    COALESCE(SUM(tasks_executed), 0),
		    COALESCE(SUM(tasks_succeeded), 0),
		    COALESCE(SUM(tasks_failed), 0),
		    COALESCE(SUM(total_tokens), 0),
		    COALESCE(SUM(estimated_usd), 0),
		    COALESCE(SUM(local_model_tasks), 0),
		    COALESCE(SUM(paid_model_tasks), 0)
		FROM usage_daily
		WHERE office_id = $1 AND date >= CURRENT_DATE - $2 * INTERVAL '1 day'
	`

	var summary domain.UsageSummary
	var localTasks, paidTasks int

	err := r.db.QueryRow(ctx, query, officeID, days).Scan(
		&summary.CreditsUsed, &summary.TasksExecuted,
		&summary.TasksSucceeded, &summary.TasksFailed,
		&summary.TokensProcessed, &summary.EstimatedCostUSD,
		&localTasks, &paidTasks,
	)
	if err != nil {
		return nil, err
	}

	// Calculate local model ratio
	totalTasks := localTasks + paidTasks
	if totalTasks > 0 {
		summary.LocalModelRatio = float64(localTasks) / float64(totalTasks) * 100
	}

	// Set period label
	switch days {
	case 1:
		summary.Period = "today"
	case 7:
		summary.Period = "7d"
	case 30:
		summary.Period = "30d"
	default:
		summary.Period = "custom"
	}

	return &summary, nil
}

// RecordTaskUsage records usage for a completed task
func (r *AnalyticsRepository) RecordTaskUsage(
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
	query := `SELECT record_task_usage($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`

	_, err := r.db.Exec(ctx, query,
		officeID, agentID, agentRole, modelName, provider,
		credits, inputTokens, outputTokens, isLocalModel, usdCost, success,
	)
	return err
}
