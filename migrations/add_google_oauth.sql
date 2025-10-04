-- Add Google OAuth support to users table
-- Run this SQL in your Supabase SQL editor

-- Add google_id column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;

-- Allow password_hash to be NULL for OAuth users
ALTER TABLE users 
ALTER COLUMN password_hash DROP NOT NULL;

-- Create index on google_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- Update existing constraint to allow either password_hash OR google_id
-- (You might need to adjust this based on your existing constraints)
ALTER TABLE users 
ADD CONSTRAINT check_auth_method 
CHECK (
    (password_hash IS NOT NULL) OR 
    (google_id IS NOT NULL)
);