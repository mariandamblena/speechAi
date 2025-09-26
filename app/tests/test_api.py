"""
Script de prueba para la API REST
"""

import requests
import json
import time

# Configuración
API_BASE = "http://localhost:8000"
ACCOUNT_ID = "demo_minutes"

def test_api():
    """Ejecuta pruebas básicas de la API"""
    
    print("🧪 Testing Speech AI Call Tracking API")
    print("=" * 50)
    
    # 1. Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # 2. Check account balance
    print(f"\n2. Checking account balance for {ACCOUNT_ID}...")
    try:
        response = requests.get(f"{API_BASE}/api/v1/accounts/{ACCOUNT_ID}/balance")
        if response.status_code == 200:
            balance = response.json()
            print(f"✅ Balance: {balance}")
        else:
            print(f"❌ Balance check failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Balance check error: {e}")
    
    # 3. Create a batch
    print(f"\n3. Creating test batch...")
    try:
        batch_data = {
            "account_id": ACCOUNT_ID,
            "name": "Test Batch API",
            "description": "Batch created via API test",
            "priority": 2
        }
        
        response = requests.post(f"{API_BASE}/api/v1/batches", params=batch_data)
        if response.status_code == 200:
            result = response.json()
            batch_id = result["batch"]["batch_id"]
            print(f"✅ Created batch: {batch_id}")
            
            # 4. Get batch info
            print(f"\n4. Getting batch info...")
            response = requests.get(f"{API_BASE}/api/v1/batches/{batch_id}")
            if response.status_code == 200:
                batch_info = response.json()
                print(f"✅ Batch info: {batch_info['name']} - {batch_info['total_jobs']} jobs")
            
            return batch_id
        else:
            print(f"❌ Batch creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Batch creation error: {e}")
        return None
    
    # 5. List batches
    print(f"\n5. Listing batches for account {ACCOUNT_ID}...")
    try:
        response = requests.get(f"{API_BASE}/api/v1/batches", params={"account_id": ACCOUNT_ID})
        if response.status_code == 200:
            batches = response.json()
            print(f"✅ Found {len(batches)} batches")
            for batch in batches[:3]:  # Show first 3
                print(f"   - {batch['batch_id']}: {batch['name']}")
        else:
            print(f"❌ List batches failed: {response.status_code}")
    except Exception as e:
        print(f"❌ List batches error: {e}")
    
    # 6. Dashboard stats
    print(f"\n6. Getting dashboard stats...")
    try:
        response = requests.get(f"{API_BASE}/api/v1/dashboard/stats", params={"account_id": ACCOUNT_ID})
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Dashboard stats loaded")
            if "balance" in stats:
                print(f"   Balance: {stats['balance'].get('remaining', 'N/A')}")
            if "jobs" in stats:
                print(f"   Total jobs: {stats['jobs'].get('total_jobs', 0)}")
        else:
            print(f"❌ Dashboard stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard stats error: {e}")
    
    print("\n🎉 API test completed!")
    print("\n💡 Tips:")
    print("- Check the API docs at: http://localhost:8000/docs")
    print("- Upload CSV files using the /api/v1/batches/{batch_id}/upload endpoint")
    print("- Monitor jobs with /api/v1/jobs endpoint")

def test_account_operations():
    """Prueba operaciones de cuenta"""
    print("\n💳 Testing account operations...")
    
    # Top up account
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/accounts/{ACCOUNT_ID}/topup",
            params={"minutes": 50}
        )
        if response.status_code == 200:
            print(f"✅ Added 50 minutes to {ACCOUNT_ID}")
        else:
            print(f"❌ Top up failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Top up error: {e}")
    
    # Get account stats
    try:
        response = requests.get(f"{API_BASE}/api/v1/accounts/{ACCOUNT_ID}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Account stats: {stats.get('account_name', 'N/A')}")
            print(f"   Status: {stats.get('status', 'N/A')}")
            print(f"   Plan: {stats.get('plan_type', 'N/A')}")
        else:
            print(f"❌ Account stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Account stats error: {e}")

if __name__ == "__main__":
    # Esperar a que la API esté lista
    print("Waiting for API to be ready...")
    time.sleep(2)
    
    # Ejecutar pruebas
    test_api()
    test_account_operations()
    
    print(f"\n🔗 API Documentation: {API_BASE}/docs")
    print(f"🔗 Alternative docs: {API_BASE}/redoc")