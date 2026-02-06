-- Phase 2: Cost Calculation Engine - Budget Controls
-- Adds budget limits to credit wallets for spending control

-- Add budget columns to credit_wallets
ALTER TABLE credit_wallets
    ADD COLUMN IF NOT EXISTS hourly_limit BIGINT DEFAULT NULL,      -- Max credits per hour
    ADD COLUMN IF NOT EXISTS daily_limit BIGINT DEFAULT NULL,       -- Max credits per day
    ADD COLUMN IF NOT EXISTS budget_alert_threshold INT DEFAULT 20, -- Alert at X% remaining
    ADD COLUMN IF NOT EXISTS budget_pause_enabled BOOLEAN DEFAULT FALSE; -- Pause when limit hit

-- Usage tracking for rate limiting
CREATE TABLE IF NOT EXISTS credit_usage_hourly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES credit_wallets(id),
    hour_start TIMESTAMPTZ NOT NULL,
    credits_consumed BIGINT NOT NULL DEFAULT 0,
    task_count INT NOT NULL DEFAULT 0,
    local_model_count INT NOT NULL DEFAULT 0,  -- For tracking optimization ratio
    paid_model_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_wallet_hour UNIQUE (wallet_id, hour_start)
);

-- Index for efficient hourly lookups
CREATE INDEX IF NOT EXISTS idx_credit_usage_hourly_wallet_hour 
    ON credit_usage_hourly(wallet_id, hour_start);

-- Function to get current hour usage
CREATE OR REPLACE FUNCTION get_hourly_usage(p_wallet_id UUID)
RETURNS TABLE (
    credits_consumed BIGINT,
    task_count INT,
    local_ratio FLOAT
) AS $$
DECLARE
    current_hour TIMESTAMPTZ;
BEGIN
    current_hour := date_trunc('hour', NOW());
    
    RETURN QUERY
    SELECT 
        COALESCE(cuh.credits_consumed, 0)::BIGINT,
        COALESCE(cuh.task_count, 0)::INT,
        CASE 
            WHEN COALESCE(cuh.task_count, 0) = 0 THEN 0.0
            ELSE cuh.local_model_count::FLOAT / cuh.task_count::FLOAT
        END AS local_ratio
    FROM credit_usage_hourly cuh
    WHERE cuh.wallet_id = p_wallet_id 
      AND cuh.hour_start = current_hour;
    
    -- If no row exists yet, return zeros
    IF NOT FOUND THEN
        RETURN QUERY SELECT 0::BIGINT, 0::INT, 0.0::FLOAT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to record usage with upsert
CREATE OR REPLACE FUNCTION record_usage(
    p_wallet_id UUID,
    p_credits INT,
    p_is_local_model BOOLEAN
) RETURNS VOID AS $$
DECLARE
    current_hour TIMESTAMPTZ;
BEGIN
    current_hour := date_trunc('hour', NOW());
    
    INSERT INTO credit_usage_hourly (
        wallet_id, 
        hour_start, 
        credits_consumed, 
        task_count,
        local_model_count,
        paid_model_count
    ) VALUES (
        p_wallet_id, 
        current_hour, 
        p_credits, 
        1,
        CASE WHEN p_is_local_model THEN 1 ELSE 0 END,
        CASE WHEN p_is_local_model THEN 0 ELSE 1 END
    )
    ON CONFLICT (wallet_id, hour_start)
    DO UPDATE SET
        credits_consumed = credit_usage_hourly.credits_consumed + EXCLUDED.credits_consumed,
        task_count = credit_usage_hourly.task_count + 1,
        local_model_count = credit_usage_hourly.local_model_count + 
            CASE WHEN p_is_local_model THEN 1 ELSE 0 END,
        paid_model_count = credit_usage_hourly.paid_model_count + 
            CASE WHEN p_is_local_model THEN 0 ELSE 1 END;
END;
$$ LANGUAGE plpgsql;

-- Function to check budget limits
CREATE OR REPLACE FUNCTION check_budget_limit(
    p_wallet_id UUID,
    p_estimated_credits INT
) RETURNS TABLE (
    allowed BOOLEAN,
    reason TEXT,
    hourly_remaining BIGINT,
    daily_remaining BIGINT
) AS $$
DECLARE
    wallet_rec RECORD;
    hourly_used BIGINT;
    daily_used BIGINT;
    current_hour TIMESTAMPTZ;
    current_day TIMESTAMPTZ;
BEGIN
    current_hour := date_trunc('hour', NOW());
    current_day := date_trunc('day', NOW());
    
    -- Get wallet limits
    SELECT hourly_limit, daily_limit, budget_pause_enabled
    INTO wallet_rec
    FROM credit_wallets
    WHERE id = p_wallet_id;
    
    IF NOT FOUND THEN
        RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::BIGINT, NULL::BIGINT;
        RETURN;
    END IF;
    
    -- Check hourly limit
    IF wallet_rec.hourly_limit IS NOT NULL THEN
        SELECT COALESCE(SUM(credits_consumed), 0)
        INTO hourly_used
        FROM credit_usage_hourly
        WHERE wallet_id = p_wallet_id AND hour_start = current_hour;
        
        IF hourly_used + p_estimated_credits > wallet_rec.hourly_limit THEN
            IF wallet_rec.budget_pause_enabled THEN
                RETURN QUERY SELECT 
                    FALSE, 
                    'Hourly budget limit exceeded'::TEXT, 
                    (wallet_rec.hourly_limit - hourly_used)::BIGINT,
                    NULL::BIGINT;
                RETURN;
            END IF;
        END IF;
    END IF;
    
    -- Check daily limit
    IF wallet_rec.daily_limit IS NOT NULL THEN
        SELECT COALESCE(SUM(credits_consumed), 0)
        INTO daily_used
        FROM credit_usage_hourly
        WHERE wallet_id = p_wallet_id 
          AND hour_start >= current_day;
        
        IF daily_used + p_estimated_credits > wallet_rec.daily_limit THEN
            IF wallet_rec.budget_pause_enabled THEN
                RETURN QUERY SELECT 
                    FALSE, 
                    'Daily budget limit exceeded'::TEXT,
                    NULL::BIGINT,
                    (wallet_rec.daily_limit - daily_used)::BIGINT;
                RETURN;
            END IF;
        END IF;
    END IF;
    
    -- All checks passed
    RETURN QUERY SELECT 
        TRUE, 
        NULL::TEXT,
        CASE 
            WHEN wallet_rec.hourly_limit IS NULL THEN NULL
            ELSE wallet_rec.hourly_limit - hourly_used
        END,
        CASE 
            WHEN wallet_rec.daily_limit IS NULL THEN NULL
            ELSE wallet_rec.daily_limit - daily_used
        END;
END;
$$ LANGUAGE plpgsql;
