package repository

import (
	"context"
	"encoding/json"
	"errors"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// MessageRepository implements domain.MessageRepository
type MessageRepository struct {
	db *pgxpool.Pool
}

// NewMessageRepository creates a new MessageRepository
func NewMessageRepository(db *pgxpool.Pool) *MessageRepository {
	return &MessageRepository{db: db}
}

// Create creates a new message
func (r *MessageRepository) Create(ctx context.Context, message *domain.Message) error {
	metadataJSON, err := json.Marshal(message.Metadata)
	if err != nil {
		metadataJSON = []byte("{}")
	}

	query := `
		INSERT INTO messages (id, office_id, conversation_id, sender_type, sender_id, content, metadata, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err = r.db.Exec(ctx, query,
		message.ID, message.OfficeID, message.ConversationID,
		message.SenderType, message.SenderID, message.Content,
		metadataJSON, message.CreatedAt,
	)
	return err
}

// GetByID returns a message by ID
func (r *MessageRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Message, error) {
	query := `SELECT id, office_id, conversation_id, sender_type, sender_id, content, metadata, created_at FROM messages WHERE id = $1`

	var message domain.Message
	var metadataJSON []byte

	err := r.db.QueryRow(ctx, query, id).Scan(
		&message.ID, &message.OfficeID, &message.ConversationID,
		&message.SenderType, &message.SenderID, &message.Content,
		&metadataJSON, &message.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if err := json.Unmarshal(metadataJSON, &message.Metadata); err != nil {
		message.Metadata = make(map[string]any)
	}

	return &message, nil
}

// GetByConversationID returns messages for a conversation with pagination
func (r *MessageRepository) GetByConversationID(ctx context.Context, conversationID uuid.UUID, limit, offset int) ([]*domain.Message, error) {
	query := `
		SELECT id, office_id, conversation_id, sender_type, sender_id, content, metadata, created_at 
		FROM messages 
		WHERE conversation_id = $1 
		ORDER BY created_at ASC
		LIMIT $2 OFFSET $3
	`

	rows, err := r.db.Query(ctx, query, conversationID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*domain.Message
	for rows.Next() {
		var message domain.Message
		var metadataJSON []byte

		if err := rows.Scan(
			&message.ID, &message.OfficeID, &message.ConversationID,
			&message.SenderType, &message.SenderID, &message.Content,
			&metadataJSON, &message.CreatedAt,
		); err != nil {
			return nil, err
		}

		if err := json.Unmarshal(metadataJSON, &message.Metadata); err != nil {
			message.Metadata = make(map[string]any)
		}

		messages = append(messages, &message)
	}
	return messages, rows.Err()
}

// Delete deletes a message
func (r *MessageRepository) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM messages WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id)
	return err
}
