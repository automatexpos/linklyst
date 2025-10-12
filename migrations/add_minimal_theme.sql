-- Add minimal theme to profiles table constraint
-- Migration: Add minimal theme option

-- Update the check constraint to include 'minimal'
ALTER TABLE profiles 
DROP CONSTRAINT IF EXISTS profiles_theme_check;

ALTER TABLE profiles 
ADD CONSTRAINT profiles_theme_check 
CHECK (theme in ('default', 'dark', 'light', 'colorful', 'minimal'));