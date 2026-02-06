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
