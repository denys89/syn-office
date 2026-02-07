package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/denys89/syn-office/backend/config"
	_ "github.com/jackc/pgx/v5/stdlib"
)

func main() {
	// Load configuration
	cfg := config.MustLoad()

	// Connect to database
	// We use pgx driver via database/sql for simplicity in migration script
	db, err := sql.Open("pgx", cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Connected to database")

	// 1. Create migration table
	if err := createMigrationTable(db); err != nil {
		log.Fatalf("Failed to create migration table: %v", err)
	}

	// Check if users table exists (heuristic for initial schema)
	usersExists, err := tableExists(db, "users")
	if err != nil {
		log.Fatalf("Failed to check if users table exists: %v", err)
	}

	// 2. Get applied migrations
	applied, err := getAppliedMigrations(db)
	if err != nil {
		log.Fatalf("Failed to get applied migrations: %v", err)
	}

	// Special case: if users table exists but 001 is not marked as applied, mark it.
	// This handles the case where DB was initialized via Docker volume but not tracked.
	initialMigration := "001_initial_schema.sql"
	if usersExists && !applied[initialMigration] {
		log.Printf("Detected existing 'users' table. Marking %s as applied.", initialMigration)
		if err := markMigrationApplied(db, initialMigration); err != nil {
			log.Fatalf("Failed to mark initial migration as applied: %v", err)
		}
		applied[initialMigration] = true
	}

	// 3. Read migration files
	// Assuming running from backend root or having correct path
	// We try to find the infra/migrations directory
	migrationDir := "../infra/migrations"
	if _, err := os.Stat(migrationDir); os.IsNotExist(err) {
		// Try absolute path or relative to current wd
		log.Printf("Migration dir %s not found, checking current dir...", migrationDir)
		migrationDir = "migrations" // Fallback if running from infra?
	}

	files, err := os.ReadDir(migrationDir)
	if err != nil {
		// Try to look up one level if we are in cmd/migrate
		migrationDir = "../../infra/migrations"
		files, err = os.ReadDir(migrationDir)
		if err != nil {
			log.Fatalf("Failed to read migration directory: %v", err)
		}
	}
	log.Printf("Found migration directory: %s", migrationDir)

	var migrationFiles []string
	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".sql") {
			migrationFiles = append(migrationFiles, f.Name())
		}
	}
	sort.Strings(migrationFiles)

	// 4. Apply new migrations
	for _, file := range migrationFiles {
		if applied[file] {
			continue
		}

		log.Printf("Applying migration: %s", file)
		content, err := os.ReadFile(filepath.Join(migrationDir, file))
		if err != nil {
			log.Fatalf("Failed to read file %s: %v", file, err)
		}

		if err := applyMigration(db, file, string(content)); err != nil {
			log.Fatalf("Failed to apply migration %s: %v", file, err)
		}
		log.Printf("Successfully applied: %s", file)
	}

	log.Println("All migrations applied successfully!")
}

func createMigrationTable(db *sql.DB) error {
	query := `
	CREATE TABLE IF NOT EXISTS schema_migrations (
		id SERIAL PRIMARY KEY,
		filename VARCHAR(255) NOT NULL UNIQUE,
		applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err := db.Exec(query)
	return err
}

func tableExists(db *sql.DB, tableName string) (bool, error) {
	var exists bool
	query := `SELECT EXISTS (
		SELECT FROM information_schema.tables 
		WHERE  table_schema = 'public'
		AND    table_name   = $1
	);`
	err := db.QueryRow(query, tableName).Scan(&exists)
	return exists, err
}

func getAppliedMigrations(db *sql.DB) (map[string]bool, error) {
	rows, err := db.Query("SELECT filename FROM schema_migrations")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	applied := make(map[string]bool)
	for rows.Next() {
		var filename string
		if err := rows.Scan(&filename); err != nil {
			return nil, err
		}
		applied[filename] = true
	}
	return applied, nil
}

func markMigrationApplied(db *sql.DB, filename string) error {
	_, err := db.Exec("INSERT INTO schema_migrations (filename) VALUES ($1)", filename)
	return err
}

func applyMigration(db *sql.DB, filename, content string) error {
	ctx := context.Background()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	// Defer rollback, but successful commit will make it distinct
	defer tx.Rollback()

	// Execute SQL
	if _, err := tx.ExecContext(ctx, content); err != nil {
		// If the error indicates that the objects already exist, we assume the migration
		// was previously applied (e.g. via Docker init) but not tracked.
		if isAlreadyExistsError(err) {
			log.Printf("Migration %s seems already applied (error: %v). Marking as applied.", filename, err)
			// We must rollback the failed transaction
			tx.Rollback()
			// Mark as applied in a separate operation
			return markMigrationApplied(db, filename)
		}
		return fmt.Errorf("executing sql: %w", err)
	}

	// Record migration
	if _, err := tx.ExecContext(ctx, "INSERT INTO schema_migrations (filename) VALUES ($1)", filename); err != nil {
		return fmt.Errorf("recording migration: %w", err)
	}

	return tx.Commit()
}

func isAlreadyExistsError(err error) bool {
	msg := err.Error()
	// Postgres error codes:
	// 42P07: duplicate_table
	// 42710: duplicate_object (triggers, indexes)
	// 42701: duplicate_column
	return strings.Contains(msg, "SQLSTATE 42P07") ||
		strings.Contains(msg, "SQLSTATE 42710") ||
		strings.Contains(msg, "SQLSTATE 42701") ||
		strings.Contains(msg, "already exists")
}
