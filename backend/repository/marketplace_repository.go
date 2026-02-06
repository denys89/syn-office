package repository

import (
	"context"
	"encoding/json"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type MarketplaceRepository struct {
	db *pgxpool.Pool
}

func NewMarketplaceRepository(db *pgxpool.Pool) *MarketplaceRepository {
	return &MarketplaceRepository{db: db}
}

// parseSkillTags parses JSON skill tags from database
func parseSkillTags(data []byte) []string {
	var tags []string
	if err := json.Unmarshal(data, &tags); err != nil {
		return []string{}
	}
	return tags
}

// ListTemplates returns templates with marketplace filtering
func (r *MarketplaceRepository) ListTemplates(ctx context.Context, filter MarketplaceFilter) ([]domain.AgentTemplate, int, error) {
	// Build query with filters
	baseQuery := `
		SELECT id, name, role, system_prompt, avatar_url, skill_tags,
		       author_id, COALESCE(author_name, 'Synoffice Team') as author_name, 
		       COALESCE(category, 'general') as category, COALESCE(description, '') as description,
		       COALESCE(is_featured, false) as is_featured, COALESCE(is_public, true) as is_public,
		       COALESCE(is_premium, false) as is_premium, COALESCE(price_cents, 0) as price_cents,
		       COALESCE(download_count, 0) as download_count, COALESCE(rating_average, 0) as rating_average,
		       COALESCE(rating_count, 0) as rating_count, COALESCE(version, '1.0.0') as version,
		       COALESCE(status, 'approved') as status, created_at, COALESCE(updated_at, created_at) as updated_at
		FROM agent_templates
		WHERE COALESCE(is_public, true) = true AND COALESCE(status, 'approved') = 'approved'
	`
	countQuery := `SELECT COUNT(*) FROM agent_templates WHERE COALESCE(is_public, true) = true AND COALESCE(status, 'approved') = 'approved'`

	args := []interface{}{}
	argCount := 0

	// Category filter
	if filter.Category != "" {
		argCount++
		baseQuery += " AND category = $" + string(rune('0'+argCount))
		countQuery += " AND category = $" + string(rune('0'+argCount))
		args = append(args, filter.Category)
	}

	// Featured filter
	if filter.IsFeatured != nil {
		argCount++
		baseQuery += " AND is_featured = $" + string(rune('0'+argCount))
		countQuery += " AND is_featured = $" + string(rune('0'+argCount))
		args = append(args, *filter.IsFeatured)
	}

	// Premium filter
	if filter.IsPremium != nil {
		argCount++
		baseQuery += " AND is_premium = $" + string(rune('0'+argCount))
		countQuery += " AND is_premium = $" + string(rune('0'+argCount))
		args = append(args, *filter.IsPremium)
	}

	// Search filter
	if filter.Search != "" {
		argCount++
		searchArg := "%" + filter.Search + "%"
		baseQuery += " AND (name ILIKE $" + string(rune('0'+argCount)) + " OR description ILIKE $" + string(rune('0'+argCount)) + ")"
		countQuery += " AND (name ILIKE $" + string(rune('0'+argCount)) + " OR description ILIKE $" + string(rune('0'+argCount)) + ")"
		args = append(args, searchArg)
	}

	// Get total count
	var total int
	err := r.db.QueryRow(ctx, countQuery, args...).Scan(&total)
	if err != nil {
		return nil, 0, err
	}

	// Sort
	switch filter.SortBy {
	case "popular":
		baseQuery += " ORDER BY download_count DESC"
	case "rating":
		baseQuery += " ORDER BY rating_average DESC, rating_count DESC"
	case "newest":
		baseQuery += " ORDER BY created_at DESC"
	default:
		baseQuery += " ORDER BY is_featured DESC, download_count DESC"
	}

	// Pagination
	if filter.Limit > 0 {
		argCount++
		baseQuery += " LIMIT $" + string(rune('0'+argCount))
		args = append(args, filter.Limit)
	}
	if filter.Offset > 0 {
		argCount++
		baseQuery += " OFFSET $" + string(rune('0'+argCount))
		args = append(args, filter.Offset)
	}

	rows, err := r.db.Query(ctx, baseQuery, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	templates := []domain.AgentTemplate{}
	for rows.Next() {
		var t domain.AgentTemplate
		var skillTags []byte
		var avatarURL, authorName, category, description, version, status *string
		err := rows.Scan(
			&t.ID, &t.Name, &t.Role, &t.SystemPrompt, &avatarURL, &skillTags,
			&t.AuthorID, &authorName, &category, &description,
			&t.IsFeatured, &t.IsPublic, &t.IsPremium, &t.PriceCents,
			&t.DownloadCount, &t.RatingAverage, &t.RatingCount, &version,
			&status, &t.CreatedAt, &t.UpdatedAt,
		)
		if err != nil {
			return nil, 0, err
		}

		// Handle nullable fields
		if avatarURL != nil {
			t.AvatarURL = *avatarURL
		}
		if authorName != nil {
			t.AuthorName = *authorName
		} else {
			t.AuthorName = "Synoffice Team"
		}
		if category != nil {
			t.Category = *category
		} else {
			t.Category = "general"
		}
		if description != nil {
			t.Description = *description
		}
		if version != nil {
			t.Version = *version
		} else {
			t.Version = "1.0.0"
		}
		if status != nil {
			t.Status = *status
		} else {
			t.Status = "approved"
		}

		t.SkillTags = parseSkillTags(skillTags)
		templates = append(templates, t)
	}

	return templates, total, nil
}

// GetTemplateByID returns a single template by ID
func (r *MarketplaceRepository) GetTemplateByID(ctx context.Context, id uuid.UUID) (*domain.AgentTemplate, error) {
	query := `
		SELECT id, name, role, system_prompt, avatar_url, skill_tags,
		       author_id, COALESCE(author_name, 'Synoffice Team') as author_name, 
		       COALESCE(category, 'general') as category, COALESCE(description, '') as description,
		       COALESCE(is_featured, false) as is_featured, COALESCE(is_public, true) as is_public,
		       COALESCE(is_premium, false) as is_premium, COALESCE(price_cents, 0) as price_cents,
		       COALESCE(download_count, 0) as download_count, COALESCE(rating_average, 0) as rating_average,
		       COALESCE(rating_count, 0) as rating_count, COALESCE(version, '1.0.0') as version,
		       COALESCE(status, 'approved') as status, created_at, COALESCE(updated_at, created_at) as updated_at
		FROM agent_templates WHERE id = $1
	`

	var t domain.AgentTemplate
	var skillTags []byte
	var avatarURL, authorName, category, description, version, status *string
	err := r.db.QueryRow(ctx, query, id).Scan(
		&t.ID, &t.Name, &t.Role, &t.SystemPrompt, &avatarURL, &skillTags,
		&t.AuthorID, &authorName, &category, &description,
		&t.IsFeatured, &t.IsPublic, &t.IsPremium, &t.PriceCents,
		&t.DownloadCount, &t.RatingAverage, &t.RatingCount, &version,
		&status, &t.CreatedAt, &t.UpdatedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}

	// Handle nullable fields
	if avatarURL != nil {
		t.AvatarURL = *avatarURL
	}
	if authorName != nil {
		t.AuthorName = *authorName
	} else {
		t.AuthorName = "Synoffice Team"
	}
	if category != nil {
		t.Category = *category
	} else {
		t.Category = "general"
	}
	if description != nil {
		t.Description = *description
	}
	if version != nil {
		t.Version = *version
	} else {
		t.Version = "1.0.0"
	}
	if status != nil {
		t.Status = *status
	} else {
		t.Status = "approved"
	}

	t.SkillTags = parseSkillTags(skillTags)
	return &t, nil
}

// GetCategories returns all categories
func (r *MarketplaceRepository) GetCategories(ctx context.Context) ([]domain.AgentCategory, error) {
	query := `SELECT id, name, slug, COALESCE(description, '') as description, COALESCE(icon, '') as icon, display_order, created_at
	          FROM agent_categories ORDER BY display_order`

	rows, err := r.db.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	categories := []domain.AgentCategory{}
	for rows.Next() {
		var c domain.AgentCategory
		err := rows.Scan(&c.ID, &c.Name, &c.Slug, &c.Description, &c.Icon, &c.DisplayOrder, &c.CreatedAt)
		if err != nil {
			return nil, err
		}
		categories = append(categories, c)
	}
	return categories, nil
}

// IncrementDownload increments the download count for a template
func (r *MarketplaceRepository) IncrementDownload(ctx context.Context, templateID uuid.UUID) error {
	_, err := r.db.Exec(ctx, `UPDATE agent_templates SET download_count = COALESCE(download_count, 0) + 1 WHERE id = $1`, templateID)
	return err
}

// CreateReview creates a new review
func (r *MarketplaceRepository) CreateReview(ctx context.Context, review *domain.AgentReview) error {
	query := `INSERT INTO agent_reviews (template_id, user_id, rating, title, review_text)
	          VALUES ($1, $2, $3, $4, $5) RETURNING id, created_at, updated_at`
	return r.db.QueryRow(ctx, query, review.TemplateID, review.UserID, review.Rating, review.Title, review.ReviewText).
		Scan(&review.ID, &review.CreatedAt, &review.UpdatedAt)
}

// GetReviews returns reviews for a template
func (r *MarketplaceRepository) GetReviews(ctx context.Context, templateID uuid.UUID, limit, offset int) ([]domain.AgentReview, error) {
	query := `SELECT id, template_id, user_id, rating, COALESCE(title, '') as title, review_text, created_at, updated_at
	          FROM agent_reviews WHERE template_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`

	rows, err := r.db.Query(ctx, query, templateID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	reviews := []domain.AgentReview{}
	for rows.Next() {
		var rev domain.AgentReview
		err := rows.Scan(&rev.ID, &rev.TemplateID, &rev.UserID, &rev.Rating, &rev.Title, &rev.ReviewText, &rev.CreatedAt, &rev.UpdatedAt)
		if err != nil {
			return nil, err
		}
		reviews = append(reviews, rev)
	}
	return reviews, nil
}

// MarketplaceFilter defines filtering options for marketplace queries
type MarketplaceFilter struct {
	Category   string
	Search     string
	IsFeatured *bool
	IsPremium  *bool
	SortBy     string // "popular", "rating", "newest"
	Limit      int
	Offset     int
}
