-- Migration: Add trial and subscription fields to users table
-- Date: October 9, 2025
-- Purpose: Implement 7-day trial system and subscription management

-- Add trial and subscription columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_start timestamp;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_end timestamp;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_trial boolean DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status varchar(20) DEFAULT 'trial';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start timestamp;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_end timestamp;

-- Update existing users to have trial status (optional - for existing users)
-- Uncomment the following lines if you want to give existing users a trial
/*
UPDATE users 
SET 
    trial_start = NOW(),
    trial_end = NOW() + INTERVAL '7 days',
    is_trial = true,
    subscription_status = 'trial',
    is_active = true
WHERE trial_start IS NULL;
*/

-- Create upgrade_requests table for admin approval system
CREATE TABLE IF NOT EXISTS upgrade_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(255),
    email VARCHAR(255),
    business_name VARCHAR(255),
    use_case TEXT,
    additional_info TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP,
    approved_at TIMESTAMP,
    rejected_at TIMESTAMP,
    approved_by VARCHAR(255),
    rejected_by VARCHAR(255),
    rejection_reason TEXT,
    trial_end TIMESTAMP
);

-- Create index for faster trial expiration queries
CREATE INDEX IF NOT EXISTS idx_users_trial_end ON users(trial_end) WHERE is_trial = true;
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_upgrade_requests_status ON upgrade_requests(status);
CREATE INDEX IF NOT EXISTS idx_upgrade_requests_user_id ON upgrade_requests(user_id);

-- Comments for reference:
-- subscription_status values:
-- 'trial' - User is on free trial
-- 'active' - User has active paid subscription
-- 'expired' - Trial expired, no active subscription
-- 'cancelled' - User cancelled subscription
-- 'paused' - Subscription temporarily paused