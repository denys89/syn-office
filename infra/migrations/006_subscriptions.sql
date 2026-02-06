-- Phase 3: Subscription Tier System
-- Adds subscription management and credit allocations

-- Subscription status enum
CREATE TYPE subscription_status AS ENUM (
    'active',
    'cancelled',
    'past_due',
    'trialing',
    'paused',
    'unpaid'
);

-- Billing interval
CREATE TYPE billing_interval AS ENUM (
    'monthly',
    'yearly'
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES offices(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL DEFAULT 'solo',
    status subscription_status NOT NULL DEFAULT 'active',
    billing_interval billing_interval NOT NULL DEFAULT 'monthly',
    
    -- Stripe integration
    stripe_customer_id VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    stripe_price_id VARCHAR(100),
    
    -- Billing period
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 month',
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at TIMESTAMPTZ,
    
    -- Trial
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_office_subscription UNIQUE (office_id)
);

-- Credit allocations per billing period
CREATE TABLE credit_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    wallet_id UUID NOT NULL REFERENCES credit_wallets(id) ON DELETE CASCADE,
    
    -- Period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Credits
    credits_allocated BIGINT NOT NULL,
    credits_consumed BIGINT NOT NULL DEFAULT 0,
    rollover_credits BIGINT NOT NULL DEFAULT 0,  -- Carry from previous period
    
    -- Source
    source VARCHAR(20) NOT NULL DEFAULT 'subscription',  -- 'subscription', 'purchase', 'bonus'
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_subscription_period UNIQUE (subscription_id, period_start)
);

-- Indexes
CREATE INDEX idx_subscriptions_office ON subscriptions(office_id);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_credit_allocations_sub ON credit_allocations(subscription_id);
CREATE INDEX idx_credit_allocations_wallet ON credit_allocations(wallet_id);
CREATE INDEX idx_credit_allocations_period ON credit_allocations(period_start, period_end);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_subscription_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_subscription_timestamp();

-- Function to create default subscription for new office
CREATE OR REPLACE FUNCTION create_default_subscription()
RETURNS TRIGGER AS $$
DECLARE
    sub_id UUID;
    wallet_id UUID;
BEGIN
    -- Create subscription
    INSERT INTO subscriptions (office_id, tier, status, current_period_end)
    VALUES (
        NEW.id, 
        'solo', 
        'active',
        NOW() + INTERVAL '1 month'
    )
    RETURNING id INTO sub_id;
    
    -- Get wallet (should be auto-created by credit wallet trigger)
    SELECT id INTO wallet_id FROM credit_wallets WHERE office_id = NEW.id;
    
    -- Create initial credit allocation (1000 credits for solo)
    IF wallet_id IS NOT NULL THEN
        INSERT INTO credit_allocations (
            subscription_id, wallet_id, period_start, period_end, 
            credits_allocated, source
        ) VALUES (
            sub_id, wallet_id, NOW(), NOW() + INTERVAL '1 month',
            1000, 'subscription'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on offices table
CREATE TRIGGER auto_create_subscription
    AFTER INSERT ON offices
    FOR EACH ROW
    EXECUTE FUNCTION create_default_subscription();

-- Function to allocate credits for new billing period
CREATE OR REPLACE FUNCTION allocate_subscription_credits(
    p_subscription_id UUID,
    p_credits BIGINT,
    p_period_start TIMESTAMPTZ,
    p_period_end TIMESTAMPTZ
) RETURNS UUID AS $$
DECLARE
    v_wallet_id UUID;
    v_allocation_id UUID;
    v_office_id UUID;
BEGIN
    -- Get office and wallet
    SELECT s.office_id INTO v_office_id
    FROM subscriptions s
    WHERE s.id = p_subscription_id;
    
    SELECT id INTO v_wallet_id
    FROM credit_wallets
    WHERE office_id = v_office_id;
    
    IF v_wallet_id IS NULL THEN
        RAISE EXCEPTION 'No wallet found for subscription';
    END IF;
    
    -- Create allocation
    INSERT INTO credit_allocations (
        subscription_id, wallet_id, period_start, period_end,
        credits_allocated, source
    ) VALUES (
        p_subscription_id, v_wallet_id, p_period_start, p_period_end,
        p_credits, 'subscription'
    )
    RETURNING id INTO v_allocation_id;
    
    -- Add credits to wallet
    UPDATE credit_wallets
    SET balance = balance + p_credits,
        total_bonus = total_bonus + p_credits,  -- Track as allocation
        updated_at = NOW()
    WHERE id = v_wallet_id;
    
    RETURN v_allocation_id;
END;
$$ LANGUAGE plpgsql;

-- View for subscription summary
CREATE OR REPLACE VIEW subscription_summary AS
SELECT 
    s.id,
    s.office_id,
    s.tier,
    s.status,
    s.billing_interval,
    s.current_period_start,
    s.current_period_end,
    s.cancel_at_period_end,
    cw.balance as current_balance,
    COALESCE(ca.credits_allocated, 0) as period_credits_allocated,
    COALESCE(ca.credits_consumed, 0) as period_credits_consumed,
    s.created_at
FROM subscriptions s
LEFT JOIN credit_wallets cw ON cw.office_id = s.office_id
LEFT JOIN credit_allocations ca ON ca.subscription_id = s.id 
    AND NOW() BETWEEN ca.period_start AND ca.period_end;
