-- Agent Marketplace Extension
-- Migration: 002_agent_marketplace.sql
-- Adds marketplace capabilities to agent templates

-- Add new columns to agent_templates
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS author_id UUID REFERENCES users(id);
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS author_name VARCHAR(255) DEFAULT 'Synoffice Team';
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'general';
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT false;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT true;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT false;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS price_cents INTEGER DEFAULT 0;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS download_count INTEGER DEFAULT 0;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS rating_average DECIMAL(3,2) DEFAULT 0.00;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS rating_count INTEGER DEFAULT 0;
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0.0';
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected'));
ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create index for marketplace queries
CREATE INDEX IF NOT EXISTS idx_agent_templates_category ON agent_templates(category);
CREATE INDEX IF NOT EXISTS idx_agent_templates_is_featured ON agent_templates(is_featured);
CREATE INDEX IF NOT EXISTS idx_agent_templates_is_public ON agent_templates(is_public);
CREATE INDEX IF NOT EXISTS idx_agent_templates_status ON agent_templates(status);

-- Categories lookup table
CREATE TABLE IF NOT EXISTS agent_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default categories
INSERT INTO agent_categories (name, slug, description, icon, display_order) VALUES
('Development', 'development', 'Coding, debugging, and software engineering', '💻', 1),
('Writing', 'writing', 'Content creation, editing, and documentation', '✍️', 2),
('Analytics', 'analytics', 'Data analysis, reporting, and visualization', '📊', 3),
('Planning', 'planning', 'Project management and coordination', '📋', 4),
('Marketing', 'marketing', 'Marketing, SEO, and social media', '📢', 5),
('Design', 'design', 'UI/UX design and creative work', '🎨', 6),
('Research', 'research', 'Research, learning, and knowledge discovery', '🔍', 7),
('Support', 'support', 'Customer support and communication', '💬', 8)
ON CONFLICT (slug) DO NOTHING;

-- Agent reviews table with detailed text reviews
CREATE TABLE IF NOT EXISTS agent_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES agent_templates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    review_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(template_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_reviews_template_id ON agent_reviews(template_id);
CREATE INDEX IF NOT EXISTS idx_agent_reviews_user_id ON agent_reviews(user_id);

-- Trigger to update rating average when reviews change
CREATE OR REPLACE FUNCTION update_template_rating()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE agent_templates SET
            rating_average = COALESCE((SELECT AVG(rating)::DECIMAL(3,2) FROM agent_reviews WHERE template_id = OLD.template_id), 0),
            rating_count = (SELECT COUNT(*) FROM agent_reviews WHERE template_id = OLD.template_id)
        WHERE id = OLD.template_id;
        RETURN OLD;
    ELSE
        UPDATE agent_templates SET
            rating_average = COALESCE((SELECT AVG(rating)::DECIMAL(3,2) FROM agent_reviews WHERE template_id = NEW.template_id), 0),
            rating_count = (SELECT COUNT(*) FROM agent_reviews WHERE template_id = NEW.template_id)
        WHERE id = NEW.template_id;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_template_rating_on_review ON agent_reviews;
CREATE TRIGGER update_template_rating_on_review
AFTER INSERT OR UPDATE OR DELETE ON agent_reviews
FOR EACH ROW EXECUTE FUNCTION update_template_rating();

-- Update existing templates with categories and descriptions
UPDATE agent_templates SET 
    category = 'development', 
    description = 'A skilled software engineer who helps with coding tasks, debugging, architecture decisions, and technical problem-solving. Alex writes clean, maintainable code and follows best practices.',
    is_featured = true
WHERE name = 'Alex';

UPDATE agent_templates SET 
    category = 'analytics', 
    description = 'A data analyst who helps analyze data, create reports, identify trends, and provide insights. Morgan is proficient in statistics and data visualization.',
    is_featured = true
WHERE name = 'Morgan';

UPDATE agent_templates SET 
    category = 'writing', 
    description = 'A professional writer who helps with content creation, editing, copywriting, and documentation. Jordan writes clear, engaging, and well-structured content.',
    is_featured = true
WHERE name = 'Jordan';

UPDATE agent_templates SET 
    category = 'planning', 
    description = 'A project planner who helps with task management, scheduling, roadmap planning, and coordination. Sam breaks down complex projects into actionable steps.',
    is_featured = true
WHERE name = 'Sam';

-- Trigger for updated_at on agent_templates
CREATE TRIGGER update_agent_templates_updated_at BEFORE UPDATE ON agent_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for updated_at on agent_reviews
CREATE TRIGGER update_agent_reviews_updated_at BEFORE UPDATE ON agent_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
