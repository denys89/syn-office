package repository

import (
	"context"
	"errors"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ConversationRepository implements domain.ConversationRepository
type ConversationRepository struct {
	db        *pgxpool.Pool
	agentRepo *AgentRepository
}

// NewConversationRepository creates a new ConversationRepository
func NewConversationRepository(db *pgxpool.Pool, agentRepo *AgentRepository) *ConversationRepository {
	return &ConversationRepository{db: db, agentRepo: agentRepo}
}

// Create creates a new conversation
func (r *ConversationRepository) Create(ctx context.Context, conversation *domain.Conversation) error {
	query := `
		INSERT INTO conversations (id, office_id, type, name, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6)
	`
	_, err := r.db.Exec(ctx, query,
		conversation.ID, conversation.OfficeID, conversation.Type,
		nullableString(conversation.Name), conversation.CreatedAt, conversation.UpdatedAt,
	)
	return err
}

// GetByID returns a conversation by ID
func (r *ConversationRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Conversation, error) {
	query := `SELECT id, office_id, type, name, created_at, updated_at FROM conversations WHERE id = $1`

	var conversation domain.Conversation
	var name *string

	err := r.db.QueryRow(ctx, query, id).Scan(
		&conversation.ID, &conversation.OfficeID, &conversation.Type,
		&name, &conversation.CreatedAt, &conversation.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if name != nil {
		conversation.Name = *name
	}

	return &conversation, nil
}

// GetByOfficeID returns all conversations for an office
func (r *ConversationRepository) GetByOfficeID(ctx context.Context, officeID uuid.UUID) ([]*domain.Conversation, error) {
	query := `SELECT id, office_id, type, name, created_at, updated_at FROM conversations WHERE office_id = $1 ORDER BY updated_at DESC`

	rows, err := r.db.Query(ctx, query, officeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var conversations []*domain.Conversation
	for rows.Next() {
		var conversation domain.Conversation
		var name *string

		if err := rows.Scan(
			&conversation.ID, &conversation.OfficeID, &conversation.Type,
			&name, &conversation.CreatedAt, &conversation.UpdatedAt,
		); err != nil {
			return nil, err
		}

		if name != nil {
			conversation.Name = *name
		}

		conversations = append(conversations, &conversation)
	}
	return conversations, rows.Err()
}

// AddParticipant adds an agent to a conversation
func (r *ConversationRepository) AddParticipant(ctx context.Context, conversationID, agentID uuid.UUID) error {
	query := `
		INSERT INTO conversation_participants (id, conversation_id, agent_id, joined_at)
		VALUES ($1, $2, $3, NOW())
		ON CONFLICT (conversation_id, agent_id) DO NOTHING
	`
	_, err := r.db.Exec(ctx, query, uuid.New(), conversationID, agentID)
	return err
}

// RemoveParticipant removes an agent from a conversation
func (r *ConversationRepository) RemoveParticipant(ctx context.Context, conversationID, agentID uuid.UUID) error {
	query := `DELETE FROM conversation_participants WHERE conversation_id = $1 AND agent_id = $2`
	_, err := r.db.Exec(ctx, query, conversationID, agentID)
	return err
}

// GetParticipants returns all agents in a conversation
func (r *ConversationRepository) GetParticipants(ctx context.Context, conversationID uuid.UUID) ([]*domain.Agent, error) {
	query := `SELECT agent_id FROM conversation_participants WHERE conversation_id = $1`

	rows, err := r.db.Query(ctx, query, conversationID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var agents []*domain.Agent
	for rows.Next() {
		var agentID uuid.UUID
		if err := rows.Scan(&agentID); err != nil {
			return nil, err
		}

		agent, err := r.agentRepo.GetByID(ctx, agentID)
		if err != nil {
			continue // Skip if agent not found
		}
		agents = append(agents, agent)
	}
	return agents, rows.Err()
}

// Update updates a conversation
func (r *ConversationRepository) Update(ctx context.Context, conversation *domain.Conversation) error {
	query := `UPDATE conversations SET name = $2, updated_at = $3 WHERE id = $1`
	_, err := r.db.Exec(ctx, query, conversation.ID, nullableString(conversation.Name), conversation.UpdatedAt)
	return err
}

// Delete deletes a conversation
func (r *ConversationRepository) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM conversations WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id)
	return err
}
