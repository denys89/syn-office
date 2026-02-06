-- Advanced Agent Learning - Enhanced Memory Schema
-- Migration: 003_advanced_memory.sql
-- Adds vector memory support and feedback collection

-- Add vector reference to agent_memories
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS vector_id VARCHAR(100);

-- Add memory type classification
-- Types: fact, preference, correction, insight, task_result
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS memory_type VARCHAR(50) DEFAULT 'fact';

-- Add importance scoring (0.0 - 1.0)
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS importance_score DECIMAL(3,2) DEFAULT 0.50;

-- Add source tracking (conversation, feedback, system, extraction)
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'system';

-- Add source reference (conversation_id, message_id, etc.)
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS source_id UUID;

-- Create index for memory type queries
CREATE INDEX IF NOT EXISTS idx_agent_memories_type ON agent_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memories_importance ON agent_memories(importance_score);

-- User feedback table for explicit learning signals
CREATE TABLE IF NOT EXISTS agent_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    office_id UUID NOT NULL REFERENCES offices(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    -- Feedback type: positive, negative, correction
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'correction')),
    
    -- Optional rating 1-5
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    
    -- Optional correction text or comment
    comment TEXT,
    
    -- The original content being rated
    original_content TEXT,
    
    -- For corrections: the preferred response
    correction_content TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_agent_id ON agent_feedback(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_office_id ON agent_feedback(office_id);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_type ON agent_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_created ON agent_feedback(created_at);

-- Agent learning statistics table
CREATE TABLE IF NOT EXISTS agent_learning_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE UNIQUE,
    
    -- Memory counts by type
    fact_count INTEGER DEFAULT 0,
    preference_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,
    insight_count INTEGER DEFAULT 0,
    
    -- Feedback counts
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    
    -- Performance metrics
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    total_interactions INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_learning_stats_agent ON agent_learning_stats(agent_id);

-- Trigger to update learning stats updated_at
CREATE TRIGGER update_agent_learning_stats_updated_at BEFORE UPDATE ON agent_learning_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
