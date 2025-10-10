from app import supabase

print("=== LinkLyst User Check ===")

# Get all users
try:
    users = supabase.table('users').select('id, email, username').execute()
    print(f"Found {len(users.data)} users:")
    
    for i, user in enumerate(users.data, 1):
        print(f"{i}. Email: {user['email']}")
        print(f"   Username: {user['username']}")
        print(f"   ID: {user['id']}")
        print()
        
    # Check admin emails
    admin_emails = ['admin@linklyst.space', 'support@automatexpo.com']
    print("Admin emails configured:")
    for email in admin_emails:
        is_admin = any(user['email'] == email for user in users.data)
        status = "✅ EXISTS" if is_admin else "❌ NOT FOUND"
        print(f"  {email} - {status}")
        
    if not any(user['email'] in admin_emails for user in users.data):
        print("\n⚠️  NO ADMIN USERS FOUND!")
        print("To fix this, either:")
        print("1. Create a new user with admin email")
        print("2. Update existing user email to admin email")
        
        if users.data:
            print(f"\nTo make user '{users.data[0]['username']}' an admin:")
            print(f"Run this command:")
            print(f"UPDATE users SET email = 'admin@linklyst.space' WHERE id = {users.data[0]['id']};")

except Exception as e:
    print(f"Error: {e}")