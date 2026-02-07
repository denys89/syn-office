# Database Migrations Guide

## The Error You're Seeing

The error `Request failed` when loading the office page happens because the **database migrations haven't been run yet**. The frontend is trying to fetch credit balance from `/api/v1/credits/balance`, but the `credits` table doesn't exist in the database.

## Quick Fix

### Option 1: Run All Migrations (Recommended)

**Windows:**
```bash
# Set your database URL
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/synoffice

# Run migrations
run-migrations.bat
```

**Linux/Mac:**
```bash
# Set your database URL
export DATABASE_URL=postgresql://postgres:your_password@localhost:5432/synoffice

# Make script executable
chmod +x run-migrations.sh

# Run migrations
./run-migrations.sh
```

### Option 2: Manual Migration (If psql not in PATH)

If you don't have `psql` in your PATH, run the migrations manually using your PostgreSQL client (pgAdmin, DBeaver, etc.):

1. Connect to your `synoffice` database
2. Run each migration file in order:
   - `infra/migrations/001_initial_schema.sql`
   - `infra/migrations/002_agent_marketplace.sql`
   - `infra/migrations/003_advanced_memory.sql`
   - `infra/migrations/004_credit_system.sql` ← **This creates the credits table**
   - `infra/migrations/005_budget_controls.sql`
   - `infra/migrations/006_subscriptions.sql`
   - `infra/migrations/007_analytics.sql`
   - `infra/migrations/008_marketplace_revenue.sql`

## What Each Migration Does

| Migration | Purpose |
|-----------|---------|
| 001 | Core schema (users, offices, agents, conversations) |
| 002 | Marketplace (templates, reviews, categories) |
| 003 | Advanced memory system |
| 004 | **Credit system** (wallets, transactions) |
| 005 | Budget controls and limits |
| 006 | **Subscription tiers** |
| 007 | **Usage analytics** |
| 008 | **Marketplace revenue** (author earnings, payouts) |

## After Running Migrations

1. **Restart the backend** (if running):
   ```bash
   cd backend
   go run main.go
   ```

2. **Refresh the frontend** in your browser

3. You should now see:
   - 💎 Credits badge in the sidebar
   - Working Analytics page
   - Working Billing page
   - Working Author Dashboard

## Verifying Migrations

To check if migrations ran successfully, connect to your database and run:

```sql
-- Check if credits table exists
SELECT * FROM credits LIMIT 1;

-- Check if subscriptions table exists
SELECT * FROM subscriptions LIMIT 1;

-- Check if usage_daily table exists
SELECT * FROM usage_daily LIMIT 1;
```

## Troubleshooting

### "psql is not recognized"

**Solution:** Add PostgreSQL bin directory to your PATH, or use a GUI tool like pgAdmin.

### "relation does not exist"

**Solution:** The migration for that table hasn't been run. Run all migrations in order.

### "permission denied"

**Solution:** Make sure your database user has CREATE TABLE permissions.

## Need Help?

If you're still seeing errors after running migrations, check:
1. Backend logs for SQL errors
2. Browser console for API errors
3. Database connection in `.env` files
