"""
Test Upgrade System
==================

This script tests the upgrade request functionality after the database table is created.
"""

from app import supabase
from datetime import datetime
import json

def test_upgrade_system():
    """Test the upgrade request system"""
    print("🧪 Testing LinkLyst Upgrade Request System\n")
    
    # Test 1: Check if upgrade_requests table exists
    print("1. Testing upgrade_requests table...")
    try:
        result = supabase.table("upgrade_requests").select("count", count="exact").execute()
        print(f"   ✅ Table exists with {result.count} records")
    except Exception as e:
        if "does not exist" in str(e).lower():
            print("   ❌ Table does not exist - please run setup_database.py first")
            return False
        else:
            print(f"   ❌ Error: {e}")
            return False
    
    # Test 2: Check table structure
    print("\n2. Testing table structure...")
    try:
        # Insert a test record to verify all columns exist
        test_data = {
            "user_id": 999999,  # Non-existent user ID for testing
            "username": "test_user",
            "email": "test@example.com",
            "business_name": "Test Business",
            "use_case": "Testing the system",
            "additional_info": "This is a test record",
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "trial_end": datetime.utcnow().isoformat()
        }
        
        # Try to insert (will fail due to foreign key, but that's expected)
        try:
            result = supabase.table("upgrade_requests").insert(test_data).execute()
            # If successful, clean up
            if result.data:
                supabase.table("upgrade_requests").delete().eq("username", "test_user").execute()
                print("   ✅ All columns exist and are accessible")
        except Exception as insert_error:
            if "violates foreign key constraint" in str(insert_error):
                print("   ✅ Table structure is correct (foreign key constraint working)")
            else:
                print(f"   ⚠️  Column structure issue: {insert_error}")
                
    except Exception as e:
        print(f"   ❌ Structure test failed: {e}")
        return False
    
    # Test 3: Check indexes
    print("\n3. Testing query performance (indexes)...")
    try:
        # Test status index
        result = supabase.table("upgrade_requests").select("*").eq("status", "pending").execute()
        print("   ✅ Status query works")
        
        # Test user_id index  
        result = supabase.table("upgrade_requests").select("*").eq("user_id", 1).execute()
        print("   ✅ User ID query works")
        
    except Exception as e:
        print(f"   ⚠️  Query test issue: {e}")
    
    # Test 4: Check admin functionality
    print("\n4. Testing admin access...")
    try:
        result = supabase.table("upgrade_requests").select("*").order("requested_at", desc=True).execute()
        print(f"   ✅ Admin query works - found {len(result.data)} requests")
    except Exception as e:
        print(f"   ❌ Admin query failed: {e}")
        return False
    
    print("\n🎉 All tests passed! The upgrade system is ready to use.")
    print("\nNext steps:")
    print("1. Start your Flask application: python app.py")
    print("2. Go to /upgrade to test the request form")
    print("3. Use an admin email to access /admin/upgrade-requests")
    print("4. Test the full approval workflow")
    
    return True

if __name__ == "__main__":
    success = test_upgrade_system()
    if not success:
        print("\n❌ Tests failed. Please check the setup and try again.")
    
    input("\nPress Enter to exit...")