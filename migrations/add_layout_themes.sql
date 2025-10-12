-- Add layout theme support to profiles table
-- Migration: Add layout theme field for different content display layouts

-- Add layout_theme column to profiles table
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS layout_theme text DEFAULT 'grid' 
CHECK (layout_theme IN ('grid', 'list', 'cards', 'minimal-list', 'instagram'));

-- Update existing profiles to use default grid layout
UPDATE profiles 
SET layout_theme = 'grid' 
WHERE layout_theme IS NULL;