-- Add tags column to existing blog_posts table
-- Run this in Supabase SQL Editor if you already have the blog_posts table

ALTER TABLE blog_posts 
ADD COLUMN IF NOT EXISTS tags TEXT;