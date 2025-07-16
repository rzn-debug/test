#!/usr/bin/env python3
"""
Detailed test for ObjectId serialization fix
Focuses on the three endpoints that were previously failing:
1. /api/exam/history
2. /api/profile  
3. /api/leaderboard
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "https://c3e8a84b-e938-4d20-90f9-6a714243f94b.preview.emergentagent.com/api"

def test_objectid_serialization():
    """Test ObjectId serialization in the three problematic endpoints"""
    print("🔍 Testing ObjectId Serialization Fix")
    print(f"Testing against: {BASE_URL}")
    
    # First, authenticate and create some test data
    session = requests.Session()
    
    # Register/login user
    import random
    user_suffix = random.randint(10000, 99999)
    register_data = {
        "username": f"objectidtest{user_suffix}",
        "email": f"objectidtest{user_suffix}@example.com", 
        "password": "TestPass123!"
    }
    
    print("\n1. Setting up test user...")
    register_response = session.post(f"{BASE_URL}/auth/register", json=register_data)
    if register_response.status_code != 200:
        # Try login if user exists
        login_response = session.post(f"{BASE_URL}/auth/login", json={
            "username": register_data["username"],
            "password": register_data["password"]
        })
        if login_response.status_code == 200:
            auth_data = login_response.json()
        else:
            print("❌ Failed to authenticate")
            return False
    else:
        auth_data = register_response.json()
    
    token = auth_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("✅ User authenticated successfully")
    
    # Initialize sample data
    print("\n2. Initializing sample data...")
    init_response = session.post(f"{BASE_URL}/admin/init")
    print(f"Sample data init: {init_response.status_code}")
    
    # Create an exam session to generate history data
    print("\n3. Creating exam session for test data...")
    start_exam_response = session.post(f"{BASE_URL}/exam/start?num_questions=3", headers=headers)
    if start_exam_response.status_code != 200:
        print(f"❌ Failed to start exam: {start_exam_response.status_code}")
        return False
    
    exam_data = start_exam_response.json()
    session_id = exam_data["session_id"]
    questions = exam_data["questions"]
    
    # Submit some answers
    for i, question in enumerate(questions[:2]):
        answer_response = session.post(
            f"{BASE_URL}/exam/{session_id}/answer?question_id={question['id']}&selected_option=0",
            headers=headers
        )
        if answer_response.status_code != 200:
            print(f"❌ Failed to submit answer {i+1}: {answer_response.status_code}")
    
    # Submit exam
    submit_response = session.post(f"{BASE_URL}/exam/{session_id}/submit", headers=headers)
    if submit_response.status_code != 200:
        print(f"❌ Failed to submit exam: {submit_response.status_code}")
        return False
    
    print("✅ Test exam completed successfully")
    
    # Now test the three problematic endpoints
    print("\n4. Testing ObjectId serialization in problematic endpoints...")
    
    # Test 1: /api/exam/history
    print("\n📋 Testing /api/exam/history endpoint...")
    history_response = session.get(f"{BASE_URL}/exam/history", headers=headers)
    print(f"Status Code: {history_response.status_code}")
    
    if history_response.status_code == 200:
        try:
            history_data = history_response.json()
            print(f"✅ Exam history endpoint working - returned {len(history_data)} sessions")
            
            # Check if data contains proper serialized fields
            if history_data and len(history_data) > 0:
                session_data = history_data[0]
                print(f"   Sample session keys: {list(session_data.keys())}")
                
                # Check for ObjectId serialization
                if '_id' in session_data:
                    if isinstance(session_data['_id'], str):
                        print("   ✅ ObjectId properly serialized to string")
                    else:
                        print(f"   ⚠️  ObjectId not properly serialized: {type(session_data['_id'])}")
                        
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error in exam history: {e}")
            print(f"Response text: {history_response.text[:200]}...")
            return False
    else:
        print(f"❌ Exam history endpoint failed: {history_response.status_code}")
        print(f"Error: {history_response.text}")
        return False
    
    # Test 2: /api/profile
    print("\n👤 Testing /api/profile endpoint...")
    profile_response = session.get(f"{BASE_URL}/profile", headers=headers)
    print(f"Status Code: {profile_response.status_code}")
    
    if profile_response.status_code == 200:
        try:
            profile_data = profile_response.json()
            print("✅ Profile endpoint working")
            print(f"   Profile keys: {list(profile_data.keys())}")
            
            # Check user data serialization
            if 'user' in profile_data:
                user_data = profile_data['user']
                if '_id' in user_data and isinstance(user_data['_id'], str):
                    print("   ✅ User ObjectId properly serialized")
                    
            # Check recent sessions serialization
            if 'recent_sessions' in profile_data:
                sessions = profile_data['recent_sessions']
                print(f"   Recent sessions count: {len(sessions)}")
                if sessions and '_id' in sessions[0] and isinstance(sessions[0]['_id'], str):
                    print("   ✅ Session ObjectIds properly serialized")
                    
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error in profile: {e}")
            print(f"Response text: {profile_response.text[:200]}...")
            return False
    else:
        print(f"❌ Profile endpoint failed: {profile_response.status_code}")
        print(f"Error: {profile_response.text}")
        return False
    
    # Test 3: /api/leaderboard
    print("\n🏆 Testing /api/leaderboard endpoint...")
    leaderboard_response = session.get(f"{BASE_URL}/leaderboard", headers=headers)
    print(f"Status Code: {leaderboard_response.status_code}")
    
    if leaderboard_response.status_code == 200:
        try:
            leaderboard_data = leaderboard_response.json()
            print(f"✅ Leaderboard endpoint working - returned {len(leaderboard_data)} users")
            
            # Check ObjectId serialization in leaderboard
            if leaderboard_data and len(leaderboard_data) > 0:
                user_entry = leaderboard_data[0]
                print(f"   Sample leaderboard entry keys: {list(user_entry.keys())}")
                
                if '_id' in user_entry and isinstance(user_entry['_id'], str):
                    print("   ✅ Leaderboard ObjectIds properly serialized")
                    
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error in leaderboard: {e}")
            print(f"Response text: {leaderboard_response.text[:200]}...")
            return False
    else:
        print(f"❌ Leaderboard endpoint failed: {leaderboard_response.status_code}")
        print(f"Error: {leaderboard_response.text}")
        return False
    
    print("\n" + "="*60)
    print("🎉 ALL OBJECTID SERIALIZATION TESTS PASSED!")
    print("✅ /api/exam/history - Working correctly")
    print("✅ /api/profile - Working correctly") 
    print("✅ /api/leaderboard - Working correctly")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_objectid_serialization()
    if not success:
        exit(1)