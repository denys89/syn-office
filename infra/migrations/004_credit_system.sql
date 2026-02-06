-- Migration: 004_credit_system.sql
-- Description: Credit wallet and transaction system for monetization
-- Phase 1 of Synoffice Monetization

-- Credit wallet per office (workspace)
CREATE TABLE IF NOT EXISTS credit_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES offices(id) ON DELETE CASCADE,
    balance BIGINT NOT NULL DEFAULT 0,
    total_purchased BIGINT NOT NULL DEFAULT 0,
    total_bonus BIGINT NOT NULL DEFAULT 0,
    total_consumed BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Each office can only have one wallet
    CONSTRAINT unique_office_wallet UNIQUE (office_id)
);

-- Transaction log (immutable audit trail)
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES credit_wallets(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Validate transaction type
    CONSTRAINT valid_transaction_type CHECK (
        transaction_type IN ('subscription', 'purchase', 'bonus', 'consumption', 'refund', 'adjustment')
    )
);

-- Indices for efficient queries
CREATE INDEX IF NOT EXISTS idx_credit_wallets_office ON credit_wallets(office_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_wallet ON credit_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_reference ON credit_transactions(reference_type, reference_id);

-- Function to update wallet balance atomically
CREATE OR REPLACE FUNCTION update_wallet_balance(
    p_wallet_id UUID,
    p_amount BIGINT,
    p_transaction_type VARCHAR(20),
    p_reference_type VARCHAR(50) DEFAULT NULL,
    p_reference_id UUID DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS credit_transactions AS $$
DECLARE
    v_wallet credit_wallets;
    v_transaction credit_transactions;
BEGIN
    -- Lock the wallet row for update
    SELECT * INTO v_wallet FROM credit_wallets WHERE id = p_wallet_id FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Wallet not found: %', p_wallet_id;
    END IF;
    
    -- Check for insufficient balance on debit
    IF p_amount < 0 AND (v_wallet.balance + p_amount) < 0 THEN
        RAISE EXCEPTION 'Insufficient balance: has %, needs %', v_wallet.balance, ABS(p_amount);
    END IF;
    
    -- Update wallet balance
    UPDATE credit_wallets SET
        balance = balance + p_amount,
        total_purchased = CASE WHEN p_transaction_type = 'purchase' THEN total_purchased + p_amount ELSE total_purchased END,
        total_bonus = CASE WHEN p_transaction_type IN ('bonus', 'subscription') THEN total_bonus + p_amount ELSE total_bonus END,
        total_consumed = CASE WHEN p_transaction_type = 'consumption' THEN total_consumed + ABS(p_amount) ELSE total_consumed END,
        updated_at = NOW()
    WHERE id = p_wallet_id
    RETURNING * INTO v_wallet;
    
    -- Create transaction record
    INSERT INTO credit_transactions (
        wallet_id, transaction_type, amount, balance_after, 
        reference_type, reference_id, description, metadata
    ) VALUES (
        p_wallet_id, p_transaction_type, p_amount, v_wallet.balance,
        p_reference_type, p_reference_id, p_description, p_metadata
    ) RETURNING * INTO v_transaction;
    
    RETURN v_transaction;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create wallet when office is created
CREATE OR REPLACE FUNCTION create_wallet_for_office()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO credit_wallets (office_id, balance)
    VALUES (NEW.id, 1000)  -- Start with 1000 free credits for new offices
    ON CONFLICT (office_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_create_wallet_for_office ON offices;
CREATE TRIGGER trigger_create_wallet_for_office
    AFTER INSERT ON offices
    FOR EACH ROW
    EXECUTE FUNCTION create_wallet_for_office();

-- Create wallets for existing offices (migration backfill)
INSERT INTO credit_wallets (office_id, balance)
SELECT id, 1000 FROM offices
ON CONFLICT (office_id) DO NOTHING;
