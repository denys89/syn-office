package repository

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// TaskRepository implements domain.TaskRepository
type TaskRepository struct {
	db *pgxpool.Pool
}

// NewTaskRepository creates a new TaskRepository
func NewTaskRepository(db *pgxpool.Pool) *TaskRepository {
	return &TaskRepository{db: db}
}

// Create creates a new task
func (r *TaskRepository) Create(ctx context.Context, task *domain.Task) error {
	tokenUsageJSON, err := json.Marshal(task.TokenUsage)
	if err != nil {
		tokenUsageJSON = []byte("{}")
	}

	query := `
		INSERT INTO tasks (id, office_id, conversation_id, message_id, agent_id, status, input, output, error, token_usage, started_at, completed_at, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
	`
	_, err = r.db.Exec(ctx, query,
		task.ID, task.OfficeID, nullableUUID(task.ConversationID), nullableUUID(task.MessageID),
		task.AgentID, task.Status, task.Input, nullableString(task.Output), nullableString(task.Error),
		tokenUsageJSON, task.StartedAt, task.CompletedAt, task.CreatedAt,
	)
	return err
}

// GetByID returns a task by ID
func (r *TaskRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Task, error) {
	query := `
		SELECT id, office_id, conversation_id, message_id, agent_id, status, input, output, error, token_usage, started_at, completed_at, created_at 
		FROM tasks WHERE id = $1
	`

	task, err := r.scanTask(r.db.QueryRow(ctx, query, id))
	if err != nil {
		return nil, err
	}
	return task, nil
}

// GetByAgentID returns tasks for an agent
func (r *TaskRepository) GetByAgentID(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Task, error) {
	query := `
		SELECT id, office_id, conversation_id, message_id, agent_id, status, input, output, error, token_usage, started_at, completed_at, created_at 
		FROM tasks 
		WHERE agent_id = $1 
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, agentID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	return r.scanTasks(rows)
}

// GetByOfficeID returns tasks for an office
func (r *TaskRepository) GetByOfficeID(ctx context.Context, officeID uuid.UUID, limit, offset int) ([]*domain.Task, error) {
	query := `
		SELECT id, office_id, conversation_id, message_id, agent_id, status, input, output, error, token_usage, started_at, completed_at, created_at 
		FROM tasks 
		WHERE office_id = $1 
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, officeID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	return r.scanTasks(rows)
}

// GetPending returns pending tasks
func (r *TaskRepository) GetPending(ctx context.Context, limit int) ([]*domain.Task, error) {
	query := `
		SELECT id, office_id, conversation_id, message_id, agent_id, status, input, output, error, token_usage, started_at, completed_at, created_at 
		FROM tasks 
		WHERE status = 'pending' 
		ORDER BY created_at ASC
		LIMIT $1
	`

	rows, err := r.db.Query(ctx, query, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	return r.scanTasks(rows)
}

// UpdateStatus updates the status of a task
func (r *TaskRepository) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.TaskStatus, output, errMsg string) error {
	var completedAt *time.Time
	var startedAt *time.Time
	now := time.Now()

	if status == domain.TaskStatusThinking || status == domain.TaskStatusWorking {
		startedAt = &now
	}
	if status == domain.TaskStatusDone || status == domain.TaskStatusFailed {
		completedAt = &now
	}

	query := `
		UPDATE tasks 
		SET status = $2, output = COALESCE($3, output), error = COALESCE($4, error), 
			started_at = COALESCE($5, started_at), completed_at = COALESCE($6, completed_at)
		WHERE id = $1
	`
	_, err := r.db.Exec(ctx, query, id, status, nullableString(output), nullableString(errMsg), startedAt, completedAt)
	return err
}

// Delete deletes a task
func (r *TaskRepository) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM tasks WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id)
	return err
}

func (r *TaskRepository) scanTask(row pgx.Row) (*domain.Task, error) {
	var task domain.Task
	var conversationID, messageID *uuid.UUID
	var output, errMsg *string
	var tokenUsageJSON []byte

	err := row.Scan(
		&task.ID, &task.OfficeID, &conversationID, &messageID,
		&task.AgentID, &task.Status, &task.Input, &output, &errMsg,
		&tokenUsageJSON, &task.StartedAt, &task.CompletedAt, &task.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if conversationID != nil {
		task.ConversationID = *conversationID
	}
	if messageID != nil {
		task.MessageID = *messageID
	}
	if output != nil {
		task.Output = *output
	}
	if errMsg != nil {
		task.Error = *errMsg
	}

	if err := json.Unmarshal(tokenUsageJSON, &task.TokenUsage); err != nil {
		task.TokenUsage = make(map[string]int)
	}

	return &task, nil
}

func (r *TaskRepository) scanTasks(rows pgx.Rows) ([]*domain.Task, error) {
	var tasks []*domain.Task
	for rows.Next() {
		var task domain.Task
		var conversationID, messageID *uuid.UUID
		var output, errMsg *string
		var tokenUsageJSON []byte

		err := rows.Scan(
			&task.ID, &task.OfficeID, &conversationID, &messageID,
			&task.AgentID, &task.Status, &task.Input, &output, &errMsg,
			&tokenUsageJSON, &task.StartedAt, &task.CompletedAt, &task.CreatedAt,
		)
		if err != nil {
			return nil, err
		}

		if conversationID != nil {
			task.ConversationID = *conversationID
		}
		if messageID != nil {
			task.MessageID = *messageID
		}
		if output != nil {
			task.Output = *output
		}
		if errMsg != nil {
			task.Error = *errMsg
		}

		if err := json.Unmarshal(tokenUsageJSON, &task.TokenUsage); err != nil {
			task.TokenUsage = make(map[string]int)
		}

		tasks = append(tasks, &task)
	}
	return tasks, rows.Err()
}

func nullableUUID(id uuid.UUID) *uuid.UUID {
	if id == uuid.Nil {
		return nil
	}
	return &id
}
