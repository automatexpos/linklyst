-- Create clicks table for tracking link clicks
CREATE TABLE clicks (
    id SERIAL PRIMARY KEY,
    link_id UUID NOT NULL,
    referrer TEXT,
    ip_address INET,
    user_agent TEXT,
    clicked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraint (assuming links table exists)
    CONSTRAINT fk_clicks_link_id 
        FOREIGN KEY (link_id) 
        REFERENCES links(id) 
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_clicks_link_id ON clicks(link_id);
CREATE INDEX idx_clicks_clicked_at ON clicks(clicked_at);

-- Optional: Create a composite index for analytics queries
CREATE INDEX idx_clicks_link_date ON clicks(link_id, clicked_at);

-- Enable Row Level Security (RLS) if you want user-level access control
ALTER TABLE clicks ENABLE ROW LEVEL SECURITY;

-- Optional RLS policy: Users can only see clicks for their own links
-- (This assumes you have a way to join to the user through the links table)
CREATE POLICY "Users can view clicks on their own links" ON clicks
    FOR SELECT
    USING (
        link_id IN (
            SELECT id FROM links WHERE user_id = auth.uid()
        )
    );

-- Policy for inserting clicks (anyone can create click records)
CREATE POLICY "Anyone can create clicks" ON clicks
    FOR INSERT
    WITH CHECK (true);