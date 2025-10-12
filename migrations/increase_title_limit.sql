-- Increase title length limit for links table
-- Migration: Allow longer link titles

-- Update the check constraint to allow up to 500 characters
ALTER TABLE links 
DROP CONSTRAINT IF EXISTS links_title_check;

ALTER TABLE links 
ADD CONSTRAINT links_title_check 
CHECK (length(title) <= 500);