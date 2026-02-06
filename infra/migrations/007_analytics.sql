-- Phase 4: Usage Dashboard & Analytics
-- Adds analytics views and aggregation tables

-- Usage summary materialized view for fast dashboard access
CREATE TABLE usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES offices(id),
    date DATE NOT NULL,
    
    -- Credit metrics
    credits_consumed BIGINT NOT NULL DEFAULT 0,
    credits_allocated BIGINT NOT NULL DEFAULT 0,
    
    -- Task metrics
    tasks_executed INT NOT NULL DEFAULT 0,
    tasks_succeeded INT NOT NULL DEFAULT 0,
    tasks_failed INT NOT NULL DEFAULT 0,
    
    -- Token metrics
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    
    -- Model metrics
    local_model_tasks INT NOT NULL DEFAULT 0,
    paid_model_tasks INT NOT NULL DEFAULT 0,
    
    -- Cost metrics
    estimated_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_office_date UNIQUE (office_id, date)
);

-- Usage by model
CREATE TABLE usage_by_model (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES offices(id),
    date DATE NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    
    -- Metrics
    task_count INT NOT NULL DEFAULT 0,
    credits_consumed BIGINT NOT NULL DEFAULT 0,
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    estimated_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,
    avg_latency_ms INT NOT NULL DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_office_date_model UNIQUE (office_id, date, model_name)
);

-- Usage by agent
CREATE TABLE usage_by_agent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES offices(id),
    date DATE NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(id),
    agent_role VARCHAR(100) NOT NULL,
    
    -- Metrics
    task_count INT NOT NULL DEFAULT 0,
    credits_consumed BIGINT NOT NULL DEFAULT 0,
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    avg_score DECIMAL(5, 2) DEFAULT NULL,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_office_date_agent UNIQUE (office_id, date, agent_id)
);

-- Indexes for efficient querying
CREATE INDEX idx_usage_daily_office_date ON usage_daily(office_id, date DESC);
CREATE INDEX idx_usage_by_model_office_date ON usage_by_model(office_id, date DESC);
CREATE INDEX idx_usage_by_agent_office_date ON usage_by_agent(office_id, date DESC);

-- Function to record task usage (called after task completion)
CREATE OR REPLACE FUNCTION record_task_usage(
    p_office_id UUID,
    p_agent_id UUID,
    p_agent_role VARCHAR,
    p_model_name VARCHAR,
    p_provider VARCHAR,
    p_credits INT,
    p_input_tokens INT,
    p_output_tokens INT,
    p_is_local_model BOOLEAN,
    p_usd_cost DECIMAL,
    p_success BOOLEAN
) RETURNS VOID AS $$
DECLARE
    v_date DATE := CURRENT_DATE;
BEGIN
    -- Update daily usage
    INSERT INTO usage_daily (
        office_id, date, credits_consumed, tasks_executed, 
        tasks_succeeded, tasks_failed,
        input_tokens, output_tokens, total_tokens,
        local_model_tasks, paid_model_tasks, estimated_usd
    ) VALUES (
        p_office_id, v_date, p_credits, 1,
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        p_input_tokens, p_output_tokens, p_input_tokens + p_output_tokens,
        CASE WHEN p_is_local_model THEN 1 ELSE 0 END,
        CASE WHEN p_is_local_model THEN 0 ELSE 1 END,
        p_usd_cost
    )
    ON CONFLICT (office_id, date) DO UPDATE SET
        credits_consumed = usage_daily.credits_consumed + EXCLUDED.credits_consumed,
        tasks_executed = usage_daily.tasks_executed + 1,
        tasks_succeeded = usage_daily.tasks_succeeded + EXCLUDED.tasks_succeeded,
        tasks_failed = usage_daily.tasks_failed + EXCLUDED.tasks_failed,
        input_tokens = usage_daily.input_tokens + EXCLUDED.input_tokens,
        output_tokens = usage_daily.output_tokens + EXCLUDED.output_tokens,
        total_tokens = usage_daily.total_tokens + EXCLUDED.total_tokens,
        local_model_tasks = usage_daily.local_model_tasks + EXCLUDED.local_model_tasks,
        paid_model_tasks = usage_daily.paid_model_tasks + EXCLUDED.paid_model_tasks,
        estimated_usd = usage_daily.estimated_usd + EXCLUDED.estimated_usd,
        updated_at = NOW();

    -- Update model usage
    INSERT INTO usage_by_model (
        office_id, date, model_name, provider,
        task_count, credits_consumed, input_tokens, output_tokens, estimated_usd
    ) VALUES (
        p_office_id, v_date, p_model_name, p_provider,
        1, p_credits, p_input_tokens, p_output_tokens, p_usd_cost
    )
    ON CONFLICT (office_id, date, model_name) DO UPDATE SET
        task_count = usage_by_model.task_count + 1,
        credits_consumed = usage_by_model.credits_consumed + EXCLUDED.credits_consumed,
        input_tokens = usage_by_model.input_tokens + EXCLUDED.input_tokens,
        output_tokens = usage_by_model.output_tokens + EXCLUDED.output_tokens,
        estimated_usd = usage_by_model.estimated_usd + EXCLUDED.estimated_usd;

    -- Update agent usage
    INSERT INTO usage_by_agent (
        office_id, date, agent_id, agent_role,
        task_count, credits_consumed, input_tokens, output_tokens
    ) VALUES (
        p_office_id, v_date, p_agent_id, p_agent_role,
        1, p_credits, p_input_tokens, p_output_tokens
    )
    ON CONFLICT (office_id, date, agent_id) DO UPDATE SET
        task_count = usage_by_agent.task_count + 1,
        credits_consumed = usage_by_agent.credits_consumed + EXCLUDED.credits_consumed,
        input_tokens = usage_by_agent.input_tokens + EXCLUDED.input_tokens,
        output_tokens = usage_by_agent.output_tokens + EXCLUDED.output_tokens;
END;
$$ LANGUAGE plpgsql;

-- View for usage summary
CREATE OR REPLACE VIEW usage_summary AS
SELECT 
    ud.office_id,
    SUM(ud.credits_consumed) as total_credits_consumed,
    SUM(ud.tasks_executed) as total_tasks_executed,
    SUM(ud.tasks_succeeded) as total_tasks_succeeded,
    SUM(ud.tasks_failed) as total_tasks_failed,
    SUM(ud.total_tokens) as total_tokens_processed,
    SUM(ud.estimated_usd) as total_estimated_usd,
    CASE 
        WHEN SUM(ud.tasks_executed) = 0 THEN 0
        ELSE ROUND(SUM(ud.local_model_tasks)::DECIMAL / SUM(ud.tasks_executed) * 100, 2)
    END as local_model_ratio,
    cw.balance as credits_remaining
FROM usage_daily ud
JOIN credit_wallets cw ON cw.office_id = ud.office_id
WHERE ud.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ud.office_id, cw.balance;
