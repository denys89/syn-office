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

// AgentTemplateRepository implements domain.AgentTemplateRepository
type AgentTemplateRepository struct {
	db *pgxpool.Pool
}

// NewAgentTemplateRepository creates a new AgentTemplateRepository
func NewAgentTemplateRepository(db *pgxpool.Pool) *AgentTemplateRepository {
	return &AgentTemplateRepository{db: db}
}

// GetAll returns all agent templates
func (r *AgentTemplateRepository) GetAll(ctx context.Context) ([]*domain.AgentTemplate, error) {
	query := `SELECT id, name, role, system_prompt, avatar_url, skill_tags, created_at FROM agent_templates ORDER BY name`

	rows, err := r.db.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var templates []*domain.AgentTemplate
	for rows.Next() {
		var template domain.AgentTemplate
		var skillTagsJSON []byte
		var avatarURL *string

		if err := rows.Scan(&template.ID, &template.Name, &template.Role, &template.SystemPrompt, &avatarURL, &skillTagsJSON, &template.CreatedAt); err != nil {
			return nil, err
		}

		if avatarURL != nil {
			template.AvatarURL = *avatarURL
		}

		if err := json.Unmarshal(skillTagsJSON, &template.SkillTags); err != nil {
			template.SkillTags = []string{}
		}

		templates = append(templates, &template)
	}
	return templates, rows.Err()
}

// GetByID returns an agent template by ID
func (r *AgentTemplateRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.AgentTemplate, error) {
	query := `SELECT id, name, role, system_prompt, avatar_url, skill_tags, created_at FROM agent_templates WHERE id = $1`

	var template domain.AgentTemplate
	var skillTagsJSON []byte
	var avatarURL *string

	err := r.db.QueryRow(ctx, query, id).Scan(
		&template.ID, &template.Name, &template.Role, &template.SystemPrompt, &avatarURL, &skillTagsJSON, &template.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if avatarURL != nil {
		template.AvatarURL = *avatarURL
	}

	if err := json.Unmarshal(skillTagsJSON, &template.SkillTags); err != nil {
		template.SkillTags = []string{}
	}

	return &template, nil
}

// GetByRole returns an agent template by role
func (r *AgentTemplateRepository) GetByRole(ctx context.Context, role string) (*domain.AgentTemplate, error) {
	query := `SELECT id, name, role, system_prompt, avatar_url, skill_tags, created_at FROM agent_templates WHERE role = $1`

	var template domain.AgentTemplate
	var skillTagsJSON []byte
	var avatarURL *string

	err := r.db.QueryRow(ctx, query, role).Scan(
		&template.ID, &template.Name, &template.Role, &template.SystemPrompt, &avatarURL, &skillTagsJSON, &template.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if avatarURL != nil {
		template.AvatarURL = *avatarURL
	}

	if err := json.Unmarshal(skillTagsJSON, &template.SkillTags); err != nil {
		template.SkillTags = []string{}
	}

	return &template, nil
}

// AgentRepository implements domain.AgentRepository
type AgentRepository struct {
	db           *pgxpool.Pool
	templateRepo *AgentTemplateRepository
}

// NewAgentRepository creates a new AgentRepository
func NewAgentRepository(db *pgxpool.Pool, templateRepo *AgentTemplateRepository) *AgentRepository {
	return &AgentRepository{db: db, templateRepo: templateRepo}
}

// Create creates a new agent
func (r *AgentRepository) Create(ctx context.Context, agent *domain.Agent) error {
	query := `
		INSERT INTO agents (id, office_id, template_id, custom_name, custom_system_prompt, is_active, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err := r.db.Exec(ctx, query,
		agent.ID, agent.OfficeID, agent.TemplateID,
		nullableString(agent.CustomName), nullableString(agent.CustomSystemPrompt),
		agent.IsActive, agent.CreatedAt, agent.UpdatedAt,
	)
	return err
}

// GetByID returns an agent by ID with template loaded
func (r *AgentRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Agent, error) {
	query := `SELECT id, office_id, template_id, custom_name, custom_system_prompt, is_active, created_at, updated_at FROM agents WHERE id = $1`

	agent, err := r.scanAgent(ctx, r.db.QueryRow(ctx, query, id))
	if err != nil {
		return nil, err
	}

	// Load template
	template, err := r.templateRepo.GetByID(ctx, agent.TemplateID)
	if err == nil {
		agent.Template = template
	}

	return agent, nil
}

// GetByOfficeID returns all agents for an office
func (r *AgentRepository) GetByOfficeID(ctx context.Context, officeID uuid.UUID) ([]*domain.Agent, error) {
	query := `SELECT id, office_id, template_id, custom_name, custom_system_prompt, is_active, created_at, updated_at FROM agents WHERE office_id = $1 AND is_active = true ORDER BY created_at`

	rows, err := r.db.Query(ctx, query, officeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var agents []*domain.Agent
	for rows.Next() {
		agent, err := r.scanAgentFromRows(rows)
		if err != nil {
			return nil, err
		}

		// Load template
		template, err := r.templateRepo.GetByID(ctx, agent.TemplateID)
		if err == nil {
			agent.Template = template
		}

		agents = append(agents, agent)
	}
	return agents, rows.Err()
}

// Update updates an agent
func (r *AgentRepository) Update(ctx context.Context, agent *domain.Agent) error {
	query := `UPDATE agents SET custom_name = $2, custom_system_prompt = $3, is_active = $4, updated_at = $5 WHERE id = $1`
	_, err := r.db.Exec(ctx, query,
		agent.ID, nullableString(agent.CustomName), nullableString(agent.CustomSystemPrompt),
		agent.IsActive, agent.UpdatedAt,
	)
	return err
}

// Delete deletes an agent
func (r *AgentRepository) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM agents WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id)
	return err
}

func (r *AgentRepository) scanAgent(ctx context.Context, row pgx.Row) (*domain.Agent, error) {
	var agent domain.Agent
	var customName, customSystemPrompt *string

	err := row.Scan(
		&agent.ID, &agent.OfficeID, &agent.TemplateID,
		&customName, &customSystemPrompt,
		&agent.IsActive, &agent.CreatedAt, &agent.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	if customName != nil {
		agent.CustomName = *customName
	}
	if customSystemPrompt != nil {
		agent.CustomSystemPrompt = *customSystemPrompt
	}

	return &agent, nil
}

func (r *AgentRepository) scanAgentFromRows(rows pgx.Rows) (*domain.Agent, error) {
	var agent domain.Agent
	var customName, customSystemPrompt *string

	err := rows.Scan(
		&agent.ID, &agent.OfficeID, &agent.TemplateID,
		&customName, &customSystemPrompt,
		&agent.IsActive, &agent.CreatedAt, &agent.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}

	if customName != nil {
		agent.CustomName = *customName
	}
	if customSystemPrompt != nil {
		agent.CustomSystemPrompt = *customSystemPrompt
	}

	return &agent, nil
}

func nullableString(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
