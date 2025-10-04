-- Minimal clicks table (only what your current code uses)
CREATE TABLE clicks (
    id SERIAL PRIMARY KEY,
    link_id UUID NOT NULL,
    referrer TEXT,
    clicked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraint
    CONSTRAINT fk_clicks_link_id 
        FOREIGN KEY (link_id) 
        REFERENCES links(id) 
        ON DELETE CASCADE
);

-- Index for performance
CREATE INDEX idx_clicks_link_id ON clicks(link_id);