package service

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
)

// TaskService handles task-related operations
type TaskService struct {
	taskRepo        domain.TaskRepository
	orchestratorURL string
	httpClient      *http.Client
}

// NewTaskService creates a new TaskService instance
func NewTaskService(taskRepo domain.TaskRepository, orchestratorURL string) *TaskService {
	return &TaskService{
		taskRepo:        taskRepo,
		orchestratorURL: orchestratorURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// CreateTaskInput contains input for creating a task
type CreateTaskInput struct {
	OfficeID       uuid.UUID
	ConversationID uuid.UUID
	MessageID      uuid.UUID
	AgentID        uuid.UUID
	Input          string
}

// CreateTask creates a new task and sends it to the orchestrator
func (s *TaskService) CreateTask(ctx context.Context, input CreateTaskInput) (*domain.Task, error) {
	task := &domain.Task{
		ID:             uuid.New(),
		OfficeID:       input.OfficeID,
		ConversationID: input.ConversationID,
		MessageID:      input.MessageID,
		AgentID:        input.AgentID,
		Status:         domain.TaskStatusPending,
		Input:          input.Input,
		TokenUsage:     make(map[string]int),
		CreatedAt:      time.Now(),
	}

	if err := s.taskRepo.Create(ctx, task); err != nil {
		return nil, err
	}

	// Send task to orchestrator asynchronously
	go s.sendToOrchestrator(context.Background(), task)

	return task, nil
}

// GetTask returns a task by ID
func (s *TaskService) GetTask(ctx context.Context, taskID uuid.UUID) (*domain.Task, error) {
	return s.taskRepo.GetByID(ctx, taskID)
}

// GetTasksByAgent returns tasks for an agent
func (s *TaskService) GetTasksByAgent(ctx context.Context, agentID uuid.UUID, limit, offset int) ([]*domain.Task, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.taskRepo.GetByAgentID(ctx, agentID, limit, offset)
}

// UpdateTaskStatus updates the status of a task
func (s *TaskService) UpdateTaskStatus(ctx context.Context, taskID uuid.UUID, status domain.TaskStatus, output, errMsg string) error {
	return s.taskRepo.UpdateStatus(ctx, taskID, status, output, errMsg)
}

// OrchestratorRequest represents a request to the agent orchestrator
type OrchestratorRequest struct {
	TaskID         string `json:"task_id"`
	AgentID        string `json:"agent_id"`
	OfficeID       string `json:"office_id"`
	ConversationID string `json:"conversation_id"`
	Input          string `json:"input"`
}

// sendToOrchestrator sends a task to the Python orchestrator
func (s *TaskService) sendToOrchestrator(ctx context.Context, task *domain.Task) {
	// Update status to thinking
	_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusThinking, "", "")

	request := OrchestratorRequest{
		TaskID:         task.ID.String(),
		AgentID:        task.AgentID.String(),
		OfficeID:       task.OfficeID.String(),
		ConversationID: task.ConversationID.String(),
		Input:          task.Input,
	}

	jsonBody, err := json.Marshal(request)
	if err != nil {
		_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusFailed, "", err.Error())
		return
	}

	req, err := http.NewRequestWithContext(ctx, "POST", s.orchestratorURL+"/execute", bytes.NewBuffer(jsonBody))
	if err != nil {
		_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusFailed, "", err.Error())
		return
	}

	req.Header.Set("Content-Type", "application/json")

	// Update status to working
	_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusWorking, "", "")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusFailed, "", err.Error())
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		_ = s.taskRepo.UpdateStatus(ctx, task.ID, domain.TaskStatusFailed, "", "orchestrator returned non-OK status")
		return
	}

	// Response will be handled by webhook callback from orchestrator
}

// HandleOrchestratorCallback handles the callback from the orchestrator
func (s *TaskService) HandleOrchestratorCallback(ctx context.Context, taskID uuid.UUID, output string, errMsg string, tokenUsage map[string]int) error {
	status := domain.TaskStatusDone
	if errMsg != "" {
		status = domain.TaskStatusFailed
	}

	return s.taskRepo.UpdateStatus(ctx, taskID, status, output, errMsg)
}
