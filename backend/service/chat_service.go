package service

import (
	"context"
	"strings"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
)

// ChatService handles chat-related operations
type ChatService struct {
	conversationRepo domain.ConversationRepository
	messageRepo      domain.MessageRepository
	agentRepo        domain.AgentRepository
	taskService      *TaskService
}

// NewChatService creates a new ChatService instance
func NewChatService(
	conversationRepo domain.ConversationRepository,
	messageRepo domain.MessageRepository,
	agentRepo domain.AgentRepository,
	taskService *TaskService,
) *ChatService {
	return &ChatService{
		conversationRepo: conversationRepo,
		messageRepo:      messageRepo,
		agentRepo:        agentRepo,
		taskService:      taskService,
	}
}

// CreateConversationInput contains input for creating a conversation
type CreateConversationInput struct {
	OfficeID uuid.UUID
	Type     domain.ConversationType
	Name     string
	AgentIDs []uuid.UUID
}

// CreateConversation creates a new conversation
func (s *ChatService) CreateConversation(ctx context.Context, input CreateConversationInput) (*domain.Conversation, error) {
	conversation := &domain.Conversation{
		ID:        uuid.New(),
		OfficeID:  input.OfficeID,
		Type:      input.Type,
		Name:      input.Name,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := s.conversationRepo.Create(ctx, conversation); err != nil {
		return nil, err
	}

	// Add participants
	for _, agentID := range input.AgentIDs {
		if err := s.conversationRepo.AddParticipant(ctx, conversation.ID, agentID); err != nil {
			return nil, err
		}
	}

	// Load participants
	participants, err := s.conversationRepo.GetParticipants(ctx, conversation.ID)
	if err != nil {
		return nil, err
	}
	conversation.Participants = participants

	return conversation, nil
}

// GetConversations returns all conversations for an office
func (s *ChatService) GetConversations(ctx context.Context, officeID uuid.UUID) ([]*domain.Conversation, error) {
	conversations, err := s.conversationRepo.GetByOfficeID(ctx, officeID)
	if err != nil {
		return nil, err
	}

	// Load participants for each conversation
	for _, conv := range conversations {
		participants, err := s.conversationRepo.GetParticipants(ctx, conv.ID)
		if err != nil {
			return nil, err
		}
		conv.Participants = participants
	}

	return conversations, nil
}

// GetConversation returns a conversation by ID
func (s *ChatService) GetConversation(ctx context.Context, conversationID uuid.UUID) (*domain.Conversation, error) {
	conversation, err := s.conversationRepo.GetByID(ctx, conversationID)
	if err != nil {
		return nil, err
	}

	participants, err := s.conversationRepo.GetParticipants(ctx, conversation.ID)
	if err != nil {
		return nil, err
	}
	conversation.Participants = participants

	return conversation, nil
}

// SendMessageInput contains input for sending a message
type SendMessageInput struct {
	OfficeID       uuid.UUID
	ConversationID uuid.UUID
	SenderType     domain.SenderType
	SenderID       uuid.UUID
	Content        string
}

// SendMessage sends a message in a conversation
func (s *ChatService) SendMessage(ctx context.Context, input SendMessageInput) (*domain.Message, error) {
	message := &domain.Message{
		ID:             uuid.New(),
		OfficeID:       input.OfficeID,
		ConversationID: input.ConversationID,
		SenderType:     input.SenderType,
		SenderID:       input.SenderID,
		Content:        input.Content,
		Metadata:       make(map[string]any),
		CreatedAt:      time.Now(),
	}

	if err := s.messageRepo.Create(ctx, message); err != nil {
		return nil, err
	}

	// If message is from user, trigger agent processing
	if input.SenderType == domain.SenderTypeUser {
		go s.processUserMessage(context.Background(), message)
	}

	return message, nil
}

// GetMessages returns messages for a conversation
func (s *ChatService) GetMessages(ctx context.Context, conversationID uuid.UUID, limit, offset int) ([]*domain.Message, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.messageRepo.GetByConversationID(ctx, conversationID, limit, offset)
}

// processUserMessage handles agent response generation (runs async)
func (s *ChatService) processUserMessage(ctx context.Context, message *domain.Message) {
	// Get conversation participants
	participants, err := s.conversationRepo.GetParticipants(ctx, message.ConversationID)
	if err != nil {
		return
	}

	// Determine which agents should respond
	respondingAgents := s.determineRespondingAgents(message.Content, participants)

	// Create tasks for responding agents
	for _, agent := range respondingAgents {
		_, err := s.taskService.CreateTask(ctx, CreateTaskInput{
			OfficeID:       message.OfficeID,
			ConversationID: message.ConversationID,
			MessageID:      message.ID,
			AgentID:        agent.ID,
			Input:          message.Content,
		})
		if err != nil {
			// Log error but continue
			continue
		}
	}
}

// determineRespondingAgents determines which agents should respond to a message
func (s *ChatService) determineRespondingAgents(content string, participants []*domain.Agent) []*domain.Agent {
	var respondingAgents []*domain.Agent

	// Check for @mentions
	for _, agent := range participants {
		agentName := agent.GetName()
		if strings.Contains(strings.ToLower(content), "@"+strings.ToLower(agentName)) {
			respondingAgents = append(respondingAgents, agent)
		}
	}

	// If no mentions and direct conversation, first agent responds
	if len(respondingAgents) == 0 && len(participants) == 1 {
		respondingAgents = participants
	}

	return respondingAgents
}
