-- Phase 6: Marketplace Revenue
-- Implements author earnings, commission tracking, and payout system

-- Commission configuration
-- Platform: 20%, Author: 80%
-- Minimum price: $1.99 (199 cents)

-- Author earnings table (one record per sale)
CREATE TABLE author_earnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    template_id UUID NOT NULL REFERENCES agent_templates(id),
    purchaser_id UUID NOT NULL REFERENCES users(id),
    purchaser_office_id UUID NOT NULL REFERENCES offices(id),
    
    -- Amounts in cents (avoid floating point issues)
    sale_amount_cents INT NOT NULL CHECK (sale_amount_cents >= 199), -- Min $1.99
    commission_cents INT NOT NULL,  -- Platform's 20%
    author_earning_cents INT NOT NULL,  -- Author's 80%
    
    -- Tracking
    stripe_payment_intent_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'completed',  -- completed, refunded
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Author payout requests
CREATE TABLE payout_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    
    -- Amount requested (in cents)
    amount_cents INT NOT NULL CHECK (amount_cents >= 1000),  -- Min $10 payout
    
    -- Processing
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    stripe_transfer_id VARCHAR(100),
    failure_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Author balance view (available for payout)
CREATE TABLE author_balances (
    author_id UUID PRIMARY KEY REFERENCES users(id),
    total_earned_cents BIGINT NOT NULL DEFAULT 0,
    total_paid_out_cents BIGINT NOT NULL DEFAULT 0,
    pending_payout_cents BIGINT NOT NULL DEFAULT 0,
    available_balance_cents BIGINT GENERATED ALWAYS AS (total_earned_cents - total_paid_out_cents - pending_payout_cents) STORED,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_author_earnings_author ON author_earnings(author_id);
CREATE INDEX idx_author_earnings_template ON author_earnings(template_id);
CREATE INDEX idx_author_earnings_created ON author_earnings(created_at DESC);
CREATE INDEX idx_payout_requests_author ON payout_requests(author_id);
CREATE INDEX idx_payout_requests_status ON payout_requests(status);

-- Function to record a sale
CREATE OR REPLACE FUNCTION record_marketplace_sale(
    p_author_id UUID,
    p_template_id UUID,
    p_purchaser_id UUID,
    p_purchaser_office_id UUID,
    p_sale_amount_cents INT,
    p_stripe_payment_intent_id VARCHAR DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_commission_cents INT;
    v_author_earning_cents INT;
    v_earning_id UUID;
BEGIN
    -- Validate minimum price
    IF p_sale_amount_cents < 199 THEN
        RAISE EXCEPTION 'Sale amount below minimum ($1.99)';
    END IF;
    
    -- Calculate commission (20% platform, 80% author)
    v_commission_cents := FLOOR(p_sale_amount_cents * 0.20);
    v_author_earning_cents := p_sale_amount_cents - v_commission_cents;
    
    -- Insert earning record
    INSERT INTO author_earnings (
        author_id, template_id, purchaser_id, purchaser_office_id,
        sale_amount_cents, commission_cents, author_earning_cents,
        stripe_payment_intent_id
    ) VALUES (
        p_author_id, p_template_id, p_purchaser_id, p_purchaser_office_id,
        p_sale_amount_cents, v_commission_cents, v_author_earning_cents,
        p_stripe_payment_intent_id
    ) RETURNING id INTO v_earning_id;
    
    -- Update author balance
    INSERT INTO author_balances (author_id, total_earned_cents, updated_at)
    VALUES (p_author_id, v_author_earning_cents, NOW())
    ON CONFLICT (author_id) DO UPDATE SET
        total_earned_cents = author_balances.total_earned_cents + v_author_earning_cents,
        updated_at = NOW();
    
    RETURN v_earning_id;
END;
$$ LANGUAGE plpgsql;

-- Function to request a payout
CREATE OR REPLACE FUNCTION request_author_payout(
    p_author_id UUID,
    p_amount_cents INT
) RETURNS UUID AS $$
DECLARE
    v_available INT;
    v_payout_id UUID;
BEGIN
    -- Check available balance
    SELECT available_balance_cents INTO v_available
    FROM author_balances
    WHERE author_id = p_author_id;
    
    IF v_available IS NULL OR v_available < p_amount_cents THEN
        RAISE EXCEPTION 'Insufficient balance for payout';
    END IF;
    
    IF p_amount_cents < 1000 THEN
        RAISE EXCEPTION 'Minimum payout is $10.00';
    END IF;
    
    -- Create payout request
    INSERT INTO payout_requests (author_id, amount_cents)
    VALUES (p_author_id, p_amount_cents)
    RETURNING id INTO v_payout_id;
    
    -- Update pending balance
    UPDATE author_balances
    SET pending_payout_cents = pending_payout_cents + p_amount_cents,
        updated_at = NOW()
    WHERE author_id = p_author_id;
    
    RETURN v_payout_id;
END;
$$ LANGUAGE plpgsql;

-- Function to complete a payout
CREATE OR REPLACE FUNCTION complete_payout(
    p_payout_id UUID,
    p_stripe_transfer_id VARCHAR
) RETURNS VOID AS $$
DECLARE
    v_author_id UUID;
    v_amount INT;
BEGIN
    -- Get payout info
    SELECT author_id, amount_cents INTO v_author_id, v_amount
    FROM payout_requests
    WHERE id = p_payout_id AND status = 'pending';
    
    IF v_author_id IS NULL THEN
        RAISE EXCEPTION 'Payout not found or not pending';
    END IF;
    
    -- Update payout status
    UPDATE payout_requests
    SET status = 'completed',
        stripe_transfer_id = p_stripe_transfer_id,
        processed_at = NOW()
    WHERE id = p_payout_id;
    
    -- Update author balance
    UPDATE author_balances
    SET pending_payout_cents = pending_payout_cents - v_amount,
        total_paid_out_cents = total_paid_out_cents + v_amount,
        updated_at = NOW()
    WHERE author_id = v_author_id;
END;
$$ LANGUAGE plpgsql;
