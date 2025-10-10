#!/usr/bin/env python3
"""
Manual migration runner for trial system and upgrade requests table
"""

from app import supabase
import sys

def run_migration():
    """Run the trial system migration manually"""
    
    print("🚀 Running trial system migration...")
    
    # SQL commands to run
    sql_commands = [
        # Add trial columns to users table
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_start timestamp;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_end timestamp;", 
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_trial boolean DEFAULT true;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status varchar(20) DEFAULT 'trial';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start timestamp;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_end timestamp;",
        
        # Create upgrade_requests table
        """CREATE TABLE IF NOT EXISTS upgrade_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            username VARCHAR(255),
            email VARCHAR(255),
            business_name VARCHAR(255),
            use_case TEXT,
            additional_info TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT NOW(),
            approved_at TIMESTAMP,
            rejected_at TIMESTAMP,
            approved_by VARCHAR(255),
            rejected_by VARCHAR(255),
            rejection_reason TEXT,
            trial_end TIMESTAMP
        );""",
        
        # Create indexes
        "CREATE INDEX IF NOT EXISTS idx_users_trial_end ON users(trial_end) WHERE is_trial = true;",
        "CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);", 
        "CREATE INDEX IF NOT EXISTS idx_upgrade_requests_status ON upgrade_requests(status);",
        "CREATE INDEX IF NOT EXISTS idx_upgrade_requests_user_id ON upgrade_requests(user_id);"
    ]
    
    success_count = 0
    error_count = 0
    
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"\n{i}. Running: {sql[:60]}..." if len(sql) > 60 else f"\n{i}. Running: {sql}")
            
            # Use supabase rpc to execute raw SQL
            result = supabase.rpc('execute_sql', {'sql': sql}).execute()
            print("   ✅ Success")
            success_count += 1
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "duplicate column" in error_msg.lower():
                print("   ⚠️  Already exists (skipped)")
                success_count += 1
            else:
                print(f"   ❌ Error: {error_msg}")
                error_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    
    if error_count == 0:
        print("\n🎉 Migration completed successfully!")
    else:
        print(f"\n⚠️  Migration completed with {error_count} errors")
    
    return error_count == 0

def verify_migration():
    """Verify that the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        # Test users table has trial columns
        result = supabase.table('users').select('trial_start, is_trial, subscription_status').limit(1).execute()
        print("   ✅ Users table has trial columns")
    except Exception as e:
        print(f"   ❌ Users table missing trial columns: {e}")
        return False
    
    try:
        # Test upgrade_requests table exists
        result = supabase.table('upgrade_requests').select('*').limit(1).execute()
        print("   ✅ upgrade_requests table exists")
        print(f"   📊 Current upgrade requests: {len(result.data)}")
    except Exception as e:
        print(f"   ❌ upgrade_requests table error: {e}")
        return False
    
    print("   🎉 Migration verification successful!")
    return True

if __name__ == "__main__":
    try:
        success = run_migration()
        if success:
            verify_migration()
    except KeyboardInterrupt:
        print("\n\n⏹️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)