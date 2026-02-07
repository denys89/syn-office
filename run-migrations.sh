#!/bin/bash
# Database Migration Runner for Synoffice
# This script runs all pending SQL migrations

echo "========================================"
echo "Synoffice Database Migration Runner"
echo "========================================"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    echo "Please set it to your PostgreSQL connection string"
    echo "Example: postgresql://postgres:password@localhost:5432/synoffice"
    exit 1
fi

echo "Running migrations..."
echo ""

# Run each migration file in order
for migration in infra/migrations/*.sql; do
    echo "Running migration: $migration"
    psql "$DATABASE_URL" -f "$migration"
    if [ $? -ne 0 ]; then
        echo "ERROR: Migration $migration failed"
        exit 1
    fi
    echo "✓ Completed: $migration"
    echo ""
done

echo ""
echo "========================================"
echo "All migrations completed successfully!"
echo "========================================"
