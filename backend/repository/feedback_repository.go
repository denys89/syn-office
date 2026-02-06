package repository

import (
	"context"
	"errors"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// FeedbackRepository handles feedback data operations
type FeedbackRepository struct {
	db *pgxpool.Pool
}

// NewFeedbackRepository creates a new FeedbackRepository
func NewFeedbackRepository(db *pgxpool.Pool) *FeedbackRepository {
	return &FeedbackRepository{db: db}
}

// CreateFeedback creates a new feedback record
func (r *FeedbackRepository) CreateFeedback(ctx context.Context, feedback *domain.AgentFeedback) error {
	query := `
		INSERT INTO agent_feedback (id, office_id, agent_id, message_id, task_id, feedback_type, rating, comment, original_content, correction_content, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
	`
	_, err := r.db.Exec(ctx, query,
		feedback.ID,
		feedback.OfficeID,
		feedback.AgentID,
		feedback.MessageID,
		feedback.TaskID,
		feedback.FeedbackType,
		nullableInt(feedback.Rating),
		nullableString(feedback.Comment),
		nullableString(feedback.OriginalContent),
		nullableString(feedback.CorrectionContent),
		feedback.CreatedAt,
	)
	return err
}

// GetFeedbackByAgentID returns all feedback for an agent
func (r *FeedbackRepository) GetFeedbackByAgentID(ctx context.Context, agentID uuid.UUID, limit int) ([]*domain.AgentFeedback, error) {
	query := `
		SELECT id, office_id, agent_id, message_id, task_id, feedback_type, rating, comment, original_content, correction_content, created_at
		FROM agent_feedback
		WHERE agent_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`
	rows, err := r.db.Query(ctx, query, agentID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var feedbacks []*domain.AgentFeedback
	for rows.Next() {
		f, err := r.scanFeedback(rows)
		if err != nil {
			return nil, err
		}
		feedbacks = append(feedbacks, f)
	}
	return feedbacks, rows.Err()
}

// GetFeedbackSummary returns aggregated feedback stats for an agent
func (r *FeedbackRepository) GetFeedbackSummary(ctx context.Context, agentID uuid.UUID) (positive, negative, correction int, avgRating float64, err error) {
	query := `
		SELECT 
			COALESCE(SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END), 0) as positive_count,
			COALESCE(SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END), 0) as negative_count,
			COALESCE(SUM(CASE WHEN feedback_type = 'correction' THEN 1 ELSE 0 END), 0) as correction_count,
			COALESCE(AVG(rating)::DECIMAL(3,2), 0) as avg_rating
		FROM agent_feedback
		WHERE agent_id = $1
	`
	err = r.db.QueryRow(ctx, query, agentID).Scan(&positive, &negative, &correction, &avgRating)
	return
}

// GetMessageByID returns a message by ID
func (r *FeedbackRepository) GetMessageByID(ctx context.Context, messageID uuid.UUID) (*domain.Message, error) {
	query := `
		SELECT id, office_id, conversation_id, sender_type, sender_id, content, created_at
		FROM messages
		WHERE id = $1
	`
	var msg domain.Message
	err := r.db.QueryRow(ctx, query, messageID).Scan(
		&msg.ID, &msg.OfficeID, &msg.ConversationID, &msg.SenderType, &msg.SenderID, &msg.Content, &msg.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &msg, nil
}

// GetAgentMemories returns memories for an agent with optional type filter
func (r *FeedbackRepository) GetAgentMemories(ctx context.Context, agentID uuid.UUID, memoryType string, limit int) ([]*domain.AgentMemory, error) {
	query := `
		SELECT id, office_id, agent_id, key, value, COALESCE(vector_id, '') as vector_id, 
		       COALESCE(memory_type, 'fact') as memory_type, COALESCE(importance_score, 0.5) as importance_score,
			   created_at, updated_at
		FROM agent_memories
		WHERE agent_id = $1
	`
	args := []interface{}{agentID}
	argNum := 2

	if memoryType != "" {
		query += ` AND memory_type = $` + string(rune('0'+argNum))
		args = append(args, memoryType)
		argNum++
	}

	query += ` ORDER BY importance_score DESC, updated_at DESC LIMIT $` + string(rune('0'+argNum))
	args = append(args, limit)

	rows, err := r.db.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var memories []*domain.AgentMemory
	for rows.Next() {
		var m domain.AgentMemory
		if err := rows.Scan(&m.ID, &m.OfficeID, &m.AgentID, &m.Key, &m.Value, &m.VectorID, &m.MemoryType, &m.ImportanceScore, &m.CreatedAt, &m.UpdatedAt); err != nil {
			return nil, err
		}
		memories = append(memories, &m)
	}
	return memories, rows.Err()
}

// GetAgentMemoryCount returns the count of memories for an agent
func (r *FeedbackRepository) GetAgentMemoryCount(ctx context.Context, agentID uuid.UUID) (int, error) {
	query := `SELECT COUNT(*) FROM agent_memories WHERE agent_id = $1`
	var count int
	err := r.db.QueryRow(ctx, query, agentID).Scan(&count)
	return count, err
}

// GetAgentInteractionCount returns total interactions (tasks) for an agent
func (r *FeedbackRepository) GetAgentInteractionCount(ctx context.Context, agentID uuid.UUID) (int, error) {
	query := `SELECT COUNT(*) FROM tasks WHERE agent_id = $1 AND status = 'done'`
	var count int
	err := r.db.QueryRow(ctx, query, agentID).Scan(&count)
	return count, err
}

func (r *FeedbackRepository) scanFeedback(rows pgx.Rows) (*domain.AgentFeedback, error) {
	var f domain.AgentFeedback
	var rating *int
	var comment, originalContent, correctionContent *string

	err := rows.Scan(
		&f.ID, &f.OfficeID, &f.AgentID, &f.MessageID, &f.TaskID,
		&f.FeedbackType, &rating, &comment, &originalContent, &correctionContent, &f.CreatedAt,
	)
	if err != nil {
		return nil, err
	}

	if rating != nil {
		f.Rating = *rating
	}
	if comment != nil {
		f.Comment = *comment
	}
	if originalContent != nil {
		f.OriginalContent = *originalContent
	}
	if correctionContent != nil {
		f.CorrectionContent = *correctionContent
	}

	return &f, nil
}

func nullableInt(i int) *int {
	if i == 0 {
		return nil
	}
	return &i
}
