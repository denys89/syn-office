package repository

import (
	"context"
	"errors"

	"github.com/denys89/syn-office/backend/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// OfficeRepository implements domain.OfficeRepository
type OfficeRepository struct {
	db *pgxpool.Pool
}

// NewOfficeRepository creates a new OfficeRepository
func NewOfficeRepository(db *pgxpool.Pool) *OfficeRepository {
	return &OfficeRepository{db: db}
}

// Create creates a new office
func (r *OfficeRepository) Create(ctx context.Context, office *domain.Office) error {
	query := `
		INSERT INTO offices (id, user_id, name, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5)
	`
	_, err := r.db.Exec(ctx, query, office.ID, office.UserID, office.Name, office.CreatedAt, office.UpdatedAt)
	return err
}

// GetByID retrieves an office by ID
func (r *OfficeRepository) GetByID(ctx context.Context, id uuid.UUID) (*domain.Office, error) {
	query := `SELECT id, user_id, name, created_at, updated_at FROM offices WHERE id = $1`

	var office domain.Office
	err := r.db.QueryRow(ctx, query, id).Scan(
		&office.ID, &office.UserID, &office.Name, &office.CreatedAt, &office.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &office, nil
}

// GetByUserID retrieves all offices for a user
func (r *OfficeRepository) GetByUserID(ctx context.Context, userID uuid.UUID) ([]*domain.Office, error) {
	query := `SELECT id, user_id, name, created_at, updated_at FROM offices WHERE user_id = $1 ORDER BY created_at`

	rows, err := r.db.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var offices []*domain.Office
	for rows.Next() {
		var office domain.Office
		if err := rows.Scan(&office.ID, &office.UserID, &office.Name, &office.CreatedAt, &office.UpdatedAt); err != nil {
			return nil, err
		}
		offices = append(offices, &office)
	}
	return offices, rows.Err()
}

// Update updates an office
func (r *OfficeRepository) Update(ctx context.Context, office *domain.Office) error {
	query := `UPDATE offices SET name = $2, updated_at = $3 WHERE id = $1`
	_, err := r.db.Exec(ctx, query, office.ID, office.Name, office.UpdatedAt)
	return err
}

// Delete deletes an office
func (r *OfficeRepository) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM offices WHERE id = $1`
	_, err := r.db.Exec(ctx, query, id)
	return err
}
