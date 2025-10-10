#!/usr/bin/env python3
"""
Database migration script for Google OAuth support
Run this script to add the google_id column to your users table
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔄 Running Google OAuth migration...")

try:
    # Add google_id column
    print("Adding google_id column...")
    result = supabase.rpc('sql', {
        'query': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;'
    }).execute()
    print("✅ google_id column added")
    
    # Allow password_hash to be NULL
    print("Allowing password_hash to be NULL...")
    result = supabase.rpc('sql', {
        'query': 'ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;'
    }).execute()
    print("✅ password_hash can now be NULL")
    
    # Create index
    print("Creating index on google_id...")
    result = supabase.rpc('sql', {
        'query': 'CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);'
    }).execute()
    print("✅ Index created")
    
    print("\n🎉 Migration completed successfully!")
    print("You can now use Google OAuth signup/login.")
    
except Exception as e:
    print(f"❌ Migration failed: {str(e)}")
    print("\n📝 Please run the SQL manually in Supabase Dashboard:")
    print("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;
    ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
    """)