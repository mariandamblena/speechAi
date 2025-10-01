#!/usr/bin/env python3
"""
Test script to verify account and batch updates after call completion
"""

import os
import sys
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

load_dotenv()

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "speechai_db")
MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "jobs")

# Test account and job
TEST_ACCOUNT_ID = "test_account_update"
TEST_BATCH_ID = "test_batch_update"
TEST_JOB_ID = "test_job_update_account_001"

def setup_test_data():
    """Create test account, batch, and job"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print("🔧 Setting up test data...")
    
    # 1. Create/update test account with some minutes
    account_data = {
        "account_id": TEST_ACCOUNT_ID,
        "account_name": "Test Account for Usage Updates",
        "plan_type": "minutes_based",
        "status": "active",
        "minutes_purchased": 10.0,
        "minutes_used": 0.0,  # Should be updated after call
        "minutes_reserved": 0.0,
        "credit_balance": 0.0,
        "credit_used": 0.0,
        "credit_reserved": 0.0,
        "cost_per_minute": 0.15,
        "cost_per_call_setup": 0.02,
        "cost_failed_call": 0.01,
        "max_concurrent_calls": 3,
        "daily_call_limit": 1000,
        "calls_today": 0,  # Should be incremented after call
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = db.accounts.update_one(
        {"account_id": TEST_ACCOUNT_ID},
        {"$set": account_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Test account created: {TEST_ACCOUNT_ID}")
    else:
        print(f"✅ Test account updated: {TEST_ACCOUNT_ID}")
    
    # 2. Create/update test batch
    batch_data = {
        "batch_id": TEST_BATCH_ID,
        "account_id": TEST_ACCOUNT_ID,
        "name": "Test Batch for Usage Updates",
        "description": "Testing account usage tracking",
        "status": "active",
        "total_jobs": 1,
        "pending_jobs": 0,
        "completed_jobs": 0,  # Should be updated after call
        "failed_jobs": 0,
        "suspended_jobs": 0,
        "total_cost": 0.0,  # Should be updated after call
        "total_minutes": 0.0,  # Should be updated after call
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = db.batches.update_one(
        {"batch_id": TEST_BATCH_ID},
        {"$set": batch_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Test batch created: {TEST_BATCH_ID}")
    else:
        print(f"✅ Test batch updated: {TEST_BATCH_ID}")
    
    # 3. Create test job that simulates a completed call
    job_data = {
        "_id": TEST_JOB_ID,
        "account_id": TEST_ACCOUNT_ID,
        "batch_id": TEST_BATCH_ID,
        "status": "done",
        "rut": "11111111-1",
        "nombre": "Test User for Account Updates",
        "to_number": "+56912345678",
        "contacto": {
            "phones": ["+56912345678"],
            "next_phone_index": 0
        },
        "deuda": 100000,
        "created_at": datetime.now(timezone.utc),
        "finished_at": datetime.now(timezone.utc),
        "call_duration_seconds": 180,  # 3 minutes call
        "call_result": {
            "success": True,
            "status": "completed",
            "summary": {
                "call_status": "completed",
                "duration_ms": 180000,  # 3 minutes in milliseconds
                "call_cost": {
                    "combined_cost": 0.47  # Example cost
                }
            },
            "timestamp": datetime.now(timezone.utc)
        }
    }
    
    result = db[MONGO_COLL_JOBS].update_one(
        {"_id": TEST_JOB_ID},
        {"$set": job_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Test job created: {TEST_JOB_ID}")
    else:
        print(f"✅ Test job updated: {TEST_JOB_ID}")
    
    client.close()

def check_initial_state():
    """Check account and batch state before test"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print("\n📊 Initial state:")
    
    # Check account
    account = db.accounts.find_one({"account_id": TEST_ACCOUNT_ID})
    if account:
        print(f"Account {TEST_ACCOUNT_ID}:")
        print(f"  - Minutes purchased: {account.get('minutes_purchased', 0)}")
        print(f"  - Minutes used: {account.get('minutes_used', 0)}")
        print(f"  - Calls today: {account.get('calls_today', 0)}")
    else:
        print(f"❌ Account {TEST_ACCOUNT_ID} not found")
    
    # Check batch
    batch = db.batches.find_one({"batch_id": TEST_BATCH_ID})
    if batch:
        print(f"Batch {TEST_BATCH_ID}:")
        print(f"  - Total cost: {batch.get('total_cost', 0)}")
        print(f"  - Total minutes: {batch.get('total_minutes', 0)}")
        print(f"  - Completed jobs: {batch.get('completed_jobs', 0)}")
    else:
        print(f"❌ Batch {TEST_BATCH_ID} not found")
    
    client.close()

def test_account_update():
    """Test the account update functionality"""
    print("\n🧪 Testing account update functionality...")
    
    try:
        # Import and test the update function
        from app.call_worker import JobStore
        
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        coll_jobs = db[MONGO_COLL_JOBS]
        
        # Create JobStore with db
        job_store = JobStore(coll_jobs, db)
        
        # Simulate call result
        mock_call_result = {
            "call_status": "completed",
            "duration_ms": 180000,  # 3 minutes
            "call_cost": {
                "combined_cost": 0.47
            }
        }
        
        # Test the update function
        if job_store.db is not None:
            print("✅ Database access available")
            job_store._update_account_and_batch_usage_sync(
                TEST_JOB_ID, 
                180,  # 3 minutes in seconds
                mock_call_result
            )
            print("✅ Account update function executed")
        else:
            print("❌ Database access not available")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error testing account update: {e}")
        import traceback
        traceback.print_exc()

def check_final_state():
    """Check account and batch state after test"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print("\n📊 Final state:")
    
    # Check account
    account = db.accounts.find_one({"account_id": TEST_ACCOUNT_ID})
    if account:
        print(f"Account {TEST_ACCOUNT_ID}:")
        print(f"  - Minutes purchased: {account.get('minutes_purchased', 0)}")
        print(f"  - Minutes used: {account.get('minutes_used', 0)} (should have increased)")
        print(f"  - Calls today: {account.get('calls_today', 0)} (should have increased)")
        
        # Calculate expected changes
        if account.get('minutes_used', 0) > 0:
            print("  ✅ Minutes used was updated!")
        else:
            print("  ❌ Minutes used was NOT updated")
            
        if account.get('calls_today', 0) > 0:
            print("  ✅ Calls today was updated!")
        else:
            print("  ❌ Calls today was NOT updated")
    else:
        print(f"❌ Account {TEST_ACCOUNT_ID} not found")
    
    # Check batch
    batch = db.batches.find_one({"batch_id": TEST_BATCH_ID})
    if batch:
        print(f"Batch {TEST_BATCH_ID}:")
        print(f"  - Total cost: {batch.get('total_cost', 0)} (should have increased)")
        print(f"  - Total minutes: {batch.get('total_minutes', 0)} (should have increased)")
        print(f"  - Completed jobs: {batch.get('completed_jobs', 0)} (should have increased)")
        
        if batch.get('total_cost', 0) > 0:
            print("  ✅ Total cost was updated!")
        else:
            print("  ❌ Total cost was NOT updated")
    else:
        print(f"❌ Batch {TEST_BATCH_ID} not found")
    
    client.close()

def main():
    print("🚀 Testing Account and Batch Updates After Call Completion")
    print("=" * 60)
    
    # Setup test data
    setup_test_data()
    
    # Check initial state
    check_initial_state()
    
    # Test account update
    test_account_update()
    
    # Check final state
    check_final_state()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main()