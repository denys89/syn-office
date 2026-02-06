package domain

import (
	"context"

	"github.com/google/uuid"
)

// UserRepository defines database operations for users
type UserRepository interface {
	Create(ctx context.Context, user *User) error
	GetByID(ctx context.Context, id uuid.UUID) (*User, error)
	GetByEmail(ctx context.Context, email string) (*User, error)
	Update(ctx context.Context, user *User) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// OfficeRepository defines database operations for offices
type OfficeRepository interface {
	Create(ctx context.Context, office *Office) error
	GetByID(ctx context.Context, id uuid.UUID) (*Office, error)
	GetByUserID(ctx context.Context, userID uuid.UUID) ([]*Office, error)
	Update(ctx context.Context, office *Office) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// AgentTemplateRepository defines database operations for agent templates
type AgentTemplateRepository interface {
	GetAll(ctx context.Context) ([]*AgentTemplate, error)
	GetByID(ctx context.Context, id uuid.UUID) (*AgentTemplate, error)
	GetByRole(ctx context.Context, role string) (*AgentTemplate, error)
}

// AgentRepository defines database operations for agents
type AgentRepository interface {
	Create(ctx context.Context, agent *Agent) error
	GetByID(ctx context.Context, id uuid.UUID) (*Agent, error)
	GetByOfficeID(ctx context.Context, officeID uuid.UUID) ([]*Agent, error)
	Update(ctx context.Context, agent *Agent) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// ConversationRepository defines database operations for conversations
type ConversationRepository interface {
	Create(ctx context.Context, conversation *Conversation) error
	GetByID(ctx context.Context, id uuid.UUID) (*Conversation, error)
	GetByOfficeID(ctx context.Context, officeID uuid.UUID) ([]*Conversation, error)
	AddParticipant(ctx context.Context, conversationID, agentID uuid.UUID) error
	RemoveParticipant(ctx context.Context, conversationID, agentID uuid.UUID) error
	GetParticipants(ctx context.Context, conversationID uuid.UUID) ([]*Agent, error)
	Update(ctx context.Context, conversation *Conversation) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// MessageRepository defines database operations for messages
type MessageRepository interface {
	Create(ctx context.Context, message *Message) error
	GetByID(ctx context.Context, id uuid.UUID) (*Message, error)
	GetByConversationID(ctx context.Context, conversationID uuid.UUID, limit, offset int) ([]*Message, error)
	Delete(ctx context.Context, id uuid.UUID) error
}

// TaskRepository defines database operations for tasks
type TaskRepository interface {
	Create(ctx context.Context, task *Task) error
	GetByID(ctx context.Context, id uuid.UUID) (*Task, error)
	GetByAgentID(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*Task, error)
	GetByOfficeID(ctx context.Context, officeID uuid.UUID, limit, offset int) ([]*Task, error)
	GetPending(ctx context.Context, limit int) ([]*Task, error)
	UpdateStatus(ctx context.Context, id uuid.UUID, status TaskStatus, output, errMsg string) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// AgentMemoryRepository defines database operations for agent memories
type AgentMemoryRepository interface {
	Create(ctx context.Context, memory *AgentMemory) error
	GetByAgentID(ctx context.Context, agentID uuid.UUID) ([]*AgentMemory, error)
	GetByKey(ctx context.Context, agentID uuid.UUID, key string) (*AgentMemory, error)
	Upsert(ctx context.Context, memory *AgentMemory) error
	Delete(ctx context.Context, id uuid.UUID) error
}
