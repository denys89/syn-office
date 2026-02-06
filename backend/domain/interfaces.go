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

// CreditRepository defines database operations for credit wallets and transactions
type CreditRepository interface {
	// Wallet operations
	CreateWallet(ctx context.Context, officeID uuid.UUID, initialBalance int64) (*CreditWallet, error)
	GetWalletByID(ctx context.Context, id uuid.UUID) (*CreditWallet, error)
	GetWalletByOfficeID(ctx context.Context, officeID uuid.UUID) (*CreditWallet, error)
	GetBalance(ctx context.Context, walletID uuid.UUID) (int64, error)
	HasSufficientBalance(ctx context.Context, walletID uuid.UUID, requiredCredits int64) (bool, int64, error)

	// Transaction operations
	AddCredits(ctx context.Context, walletID uuid.UUID, amount int64, txType TransactionType, description string, refType string, refID *uuid.UUID) (*CreditTransaction, error)
	ConsumeCredits(ctx context.Context, walletID uuid.UUID, amount int64, taskID uuid.UUID, description string) (*CreditTransaction, error)
	GetTransactions(ctx context.Context, walletID uuid.UUID, limit int, offset int) ([]*CreditTransaction, error)
	GetTransactionsByType(ctx context.Context, walletID uuid.UUID, txType TransactionType, limit int) ([]*CreditTransaction, error)
}

// SubscriptionRepository defines database operations for subscriptions
type SubscriptionRepository interface {
	// Subscription operations
	Create(ctx context.Context, subscription *Subscription) error
	GetByID(ctx context.Context, id uuid.UUID) (*Subscription, error)
	GetByOfficeID(ctx context.Context, officeID uuid.UUID) (*Subscription, error)
	GetByStripeID(ctx context.Context, stripeSubscriptionID string) (*Subscription, error)
	Update(ctx context.Context, subscription *Subscription) error
	UpdateStatus(ctx context.Context, id uuid.UUID, status SubscriptionStatus) error
	UpdateTier(ctx context.Context, id uuid.UUID, tier SubscriptionTier) error

	// Credit allocation operations
	CreateAllocation(ctx context.Context, allocation *CreditAllocation) error
	GetCurrentAllocation(ctx context.Context, subscriptionID uuid.UUID) (*CreditAllocation, error)
	GetAllocationsBySubscription(ctx context.Context, subscriptionID uuid.UUID, limit int) ([]*CreditAllocation, error)
	UpdateAllocationConsumed(ctx context.Context, allocationID uuid.UUID, consumed int64) error
}
