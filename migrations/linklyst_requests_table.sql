-- Create support requests table for LinkLyst
-- Run this SQL in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS linklyst_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    request TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    assigned_to VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_linklyst_requests_user_id ON linklyst_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_linklyst_requests_status ON linklyst_requests(status);
CREATE INDEX IF NOT EXISTS idx_linklyst_requests_email ON linklyst_requests(email);
CREATE INDEX IF NOT EXISTS idx_linklyst_requests_created_at ON linklyst_requests(created_at);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_linklyst_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_linklyst_requests_updated_at ON linklyst_requests;
CREATE TRIGGER trigger_linklyst_requests_updated_at
    BEFORE UPDATE ON linklyst_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_linklyst_requests_updated_at();

-- Disable RLS since we're using Flask session-based auth, not Supabase Auth
-- ALTER TABLE linklyst_requests ENABLE ROW LEVEL SECURITY;

-- Note: RLS policies are commented out because LinkLyst uses Flask sessions
-- for authentication, not Supabase Auth. Access control is handled at the 
-- application level in the Flask routes.

-- Grant necessary permissions
GRANT SELECT, INSERT ON linklyst_requests TO authenticated;
GRANT SELECT, INSERT ON linklyst_requests TO anon;
GRANT USAGE ON SEQUENCE linklyst_requests_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE linklyst_requests_id_seq TO anon;

-- Add comments for documentation
COMMENT ON TABLE linklyst_requests IS 'Support requests submitted by LinkLyst users';
COMMENT ON COLUMN linklyst_requests.user_id IS 'Reference to users table, NULL for anonymous requests';
COMMENT ON COLUMN linklyst_requests.status IS 'Request status: open, in_progress, resolved, closed';
COMMENT ON COLUMN linklyst_requests.priority IS 'Request priority: low, normal, high, urgent';
COMMENT ON COLUMN linklyst_requests.assigned_to IS 'Support agent assigned to this request';
COMMENT ON COLUMN linklyst_requests.notes IS 'Internal notes from support team';