"""
LinkLyst Database Setup Instructions
====================================

The upgrade system requires the upgrade_requests table to be created in your Supabase database.

STEP 1: Go to Supabase Dashboard
--------------------------------
1. Open your Supabase project dashboard
2. Navigate to "SQL Editor" in the left sidebar

STEP 2: Run the SQL Commands
----------------------------
Copy and paste the following SQL commands into the SQL Editor and execute them:

"""

print(__doc__)

# Print the SQL commands
sql_commands = """
-- Create upgrade_requests table
CREATE TABLE IF NOT EXISTS upgrade_requests (
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
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_upgrade_requests_status ON upgrade_requests(status);
CREATE INDEX IF NOT EXISTS idx_upgrade_requests_user_id ON upgrade_requests(user_id);

-- Add RLS (Row Level Security) policies
ALTER TABLE upgrade_requests ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read their own requests
CREATE POLICY "Users can view own requests" ON upgrade_requests
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Allow authenticated users to insert their own requests
CREATE POLICY "Users can insert own requests" ON upgrade_requests
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

-- Allow service role to manage all requests (for admin functions)
CREATE POLICY "Service role can manage all requests" ON upgrade_requests
    FOR ALL USING (auth.role() = 'service_role');
"""

print(sql_commands)

print("""
STEP 3: Verify Table Creation
-----------------------------
After running the SQL commands, you can test if the table was created successfully by running:

SELECT * FROM upgrade_requests LIMIT 1;

STEP 4: Test the Application
---------------------------
Once the table is created, the upgrade request system should work properly.

TROUBLESHOOTING
--------------
If you get permission errors, make sure you're using the SQL Editor as the database owner.
If the table already exists, the commands will safely skip creation.

For support, contact: support@automatexpo.com
""")

# Test if we can connect to the database
try:
    from app import supabase
    print("\n🔍 Testing database connection...")
    
    # Test users table
    users_test = supabase.table("users").select("count", count="exact").execute()
    print(f"✅ Users table: {users_test.count} records")
    
    # Test upgrade_requests table
    try:
        requests_test = supabase.table("upgrade_requests").select("count", count="exact").execute()
        print(f"✅ Upgrade_requests table: {requests_test.count} records")
        print("🎉 Database is ready!")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("❌ Upgrade_requests table not found - please create it using the SQL above")
        else:
            print(f"❌ Upgrade_requests table error: {e}")
            
except Exception as e:
    print(f"❌ Database connection error: {e}")

input("\nPress Enter to exit...")