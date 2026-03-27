# test_admin.py
import requests
import json

BASE_URL = "http://localhost:5000"

def test_admin_creation():
    print("=" * 50)
    print("Testing River Rose API Admin Setup")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("   ✅ Health check passed")
    else:
        print(f"   ❌ Health check failed: {response.status_code}")
        return
    
    # Test admin login
    print("\n2. Testing admin login...")
    login_data = {
        "email": "admin@riverrose.com",
        "password": "Admin@123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get("access_token")
        print(f"   ✅ Login successful")
        print(f"   Token: {token[:50]}...")
    else:
        print(f"   ❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Test get current user
    print("\n3. Testing get current user...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    if response.status_code == 200:
        user = response.json()
        print(f"   ✅ User retrieved successfully")
        print(f"   Name: {user.get('name')}")
        print(f"   Email: {user.get('email')}")
        print(f"   Is Admin: {user.get('is_admin')}")
    else:
        print(f"   ❌ Failed to get user: {response.status_code}")
    
    # Test admin check endpoint
    print("\n4. Testing admin check endpoint...")
    response = requests.get(f"{BASE_URL}/api/admin/check", headers=headers)
    
    if response.status_code == 200:
        admin_check = response.json()
        print(f"   ✅ Admin check passed")
        print(f"   Is Admin: {admin_check.get('isAdmin')}")
    else:
        print(f"   ❌ Admin check failed: {response.status_code}")
    
    # Test dashboard stats (admin only)
    print("\n5. Testing dashboard stats (admin only)...")
    response = requests.get(f"{BASE_URL}/api/admin/dashboard-stats", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ Dashboard stats retrieved")
        print(f"   Total Users: {stats.get('total_users')}")
        print(f"   Total Products: {stats.get('total_products')}")
        print(f"   Total Orders: {stats.get('total_orders')}")
        print(f"   Pending Orders: {stats.get('pending_orders')}")
        print(f"   Total Revenue: {stats.get('total_revenue')}")
    else:
        print(f"   ❌ Failed to get dashboard stats: {response.status_code}")
    
    # Test get all users (admin only)
    print("\n6. Testing get all users (admin only)...")
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    
    if response.status_code == 200:
        users = response.json()
        print(f"   ✅ Retrieved {len(users)} users")
        for user in users[:3]:  # Show first 3 users
            print(f"      - {user.get('name')} ({user.get('email')}) - Admin: {user.get('is_admin')}")
    else:
        print(f"   ❌ Failed to get users: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("✅ Admin setup test complete!")
    print("=" * 50)

if __name__ == "__main__":
    test_admin_creation()