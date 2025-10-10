from app import app, supabase

print("🔍 Admin Panel Diagnostic")
print("=" * 40)

# Check admin user
admin_user = supabase.table('users').select('*').eq('email', 'support@automatexpo.com').execute()
if admin_user.data:
    user = admin_user.data[0]
    print(f"✅ Admin user found:")
    print(f"   Username: {user['username']}")
    print(f"   Email: {user['email']}")
    print(f"   ID: {user['id']}")
    print(f"   Active: {user.get('is_active', 'Unknown')}")
else:
    print("❌ Admin user not found!")

# Check upgrade_requests table
try:
    requests = supabase.table('upgrade_requests').select('*').execute()
    print(f"\n✅ Upgrade requests table: {len(requests.data)} records")
    for req in requests.data:
        print(f"   Request ID: {req['id']}, Status: {req['status']}, User: {req['username']}")
except Exception as e:
    print(f"\n❌ Upgrade requests table error: {e}")

# Test route access
print("\n🧪 Testing admin route...")
with app.test_client() as client:
    # Simulate login session
    with client.session_transaction() as sess:
        if admin_user.data:
            sess['user_id'] = admin_user.data[0]['id']
    
    # Test admin route
    response = client.get('/admin/upgrade-requests')
    print(f"Admin route status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Admin route works when logged in!")
    elif response.status_code == 302:
        print("⚠️  Route redirects - check login status")
    else:
        print(f"❌ Route error: {response.status_code}")

print("\n" + "=" * 40)
print("If everything shows ✅, the admin panel should work!")
print("Make sure to login as 'admin' user first.")