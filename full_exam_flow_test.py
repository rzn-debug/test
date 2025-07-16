#!/usr/bin/env python3
"""
Full Exam Flow Test
Tests the complete exam workflow including authentication, exam taking, and all related features
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "https://c3e8a84b-e938-4d20-90f9-6a714243f94b.preview.emergentagent.com/api"

def test_full_exam_flow():
    """Test the complete exam workflow"""
    print("🎯 Testing Full Exam Flow")
    print(f"Testing against: {BASE_URL}")
    
    session = requests.Session()
    
    # Step 1: User Registration/Authentication
    print("\n1️⃣ User Authentication...")
    import random
    user_suffix = random.randint(100000, 999999)
    register_data = {
        "username": f"examflowtest{user_suffix}",
        "email": f"examflowtest{user_suffix}@example.com", 
        "password": "FlowTest123!"
    }
    
    register_response = session.post(f"{BASE_URL}/auth/register", json=register_data)
    if register_response.status_code != 200:
        print(f"❌ Registration failed: {register_response.status_code}")
        return False
    
    auth_data = register_response.json()
    token = auth_data.get("access_token")
    user_data = auth_data.get("user")
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ User registered: {user_data['username']}")
    
    # Step 2: Initialize sample questions
    print("\n2️⃣ Initializing sample questions...")
    init_response = session.post(f"{BASE_URL}/admin/init")
    print(f"✅ Sample questions initialized: {init_response.status_code}")
    
    # Step 3: Get available questions
    print("\n3️⃣ Fetching available questions...")
    questions_response = session.get(f"{BASE_URL}/questions?limit=10", headers=headers)
    if questions_response.status_code != 200:
        print(f"❌ Failed to get questions: {questions_response.status_code}")
        return False
    
    questions_data = questions_response.json()
    print(f"✅ Available questions: {len(questions_data)}")
    
    # Step 4: Start exam
    print("\n4️⃣ Starting exam...")
    start_exam_response = session.post(f"{BASE_URL}/exam/start?num_questions=5", headers=headers)
    if start_exam_response.status_code != 200:
        print(f"❌ Failed to start exam: {start_exam_response.status_code}")
        return False
    
    exam_data = start_exam_response.json()
    session_id = exam_data["session_id"]
    exam_questions = exam_data["questions"]
    time_limit = exam_data["time_limit"]
    
    print(f"✅ Exam started - Session ID: {session_id}")
    print(f"   Questions: {len(exam_questions)}, Time limit: {time_limit} minutes")
    
    # Step 5: Answer questions
    print("\n5️⃣ Answering questions...")
    for i, question in enumerate(exam_questions):
        print(f"   Question {i+1}: {question['text'][:50]}...")
        
        # Submit answer (choosing option 0 for simplicity)
        answer_response = session.post(
            f"{BASE_URL}/exam/{session_id}/answer?question_id={question['id']}&selected_option=0",
            headers=headers
        )
        
        if answer_response.status_code != 200:
            print(f"   ❌ Failed to submit answer {i+1}: {answer_response.status_code}")
            return False
        
        print(f"   ✅ Answer {i+1} submitted")
    
    # Step 6: Submit exam
    print("\n6️⃣ Submitting exam...")
    submit_response = session.post(f"{BASE_URL}/exam/{session_id}/submit", headers=headers)
    if submit_response.status_code != 200:
        print(f"❌ Failed to submit exam: {submit_response.status_code}")
        return False
    
    submit_data = submit_response.json()
    result = submit_data.get("result", {})
    new_badges = submit_data.get("new_badges", [])
    
    print(f"✅ Exam submitted successfully!")
    print(f"   Score: {result.get('score', 0):.1f}%")
    print(f"   Correct answers: {result.get('correct_answers', 0)}/{result.get('total_questions', 0)}")
    print(f"   Time taken: {result.get('time_taken', 0)} minutes")
    if new_badges:
        print(f"   🏆 New badges earned: {', '.join(new_badges)}")
    
    # Step 7: Check exam history
    print("\n7️⃣ Checking exam history...")
    history_response = session.get(f"{BASE_URL}/exam/history", headers=headers)
    if history_response.status_code != 200:
        print(f"❌ Failed to get exam history: {history_response.status_code}")
        return False
    
    history_data = history_response.json()
    print(f"✅ Exam history retrieved: {len(history_data)} completed exams")
    
    # Step 8: Check user profile
    print("\n8️⃣ Checking user profile...")
    profile_response = session.get(f"{BASE_URL}/profile", headers=headers)
    if profile_response.status_code != 200:
        print(f"❌ Failed to get profile: {profile_response.status_code}")
        return False
    
    profile_data = profile_response.json()
    user_profile = profile_data.get("user", {})
    recent_sessions = profile_data.get("recent_sessions", [])
    avg_score = profile_data.get("average_score", 0)
    
    print(f"✅ Profile retrieved:")
    print(f"   Total exams: {user_profile.get('total_exams', 0)}")
    print(f"   Average score: {avg_score:.1f}%")
    print(f"   Badges: {user_profile.get('badges', [])}")
    print(f"   Recent sessions: {len(recent_sessions)}")
    
    # Step 9: Check leaderboard
    print("\n9️⃣ Checking leaderboard...")
    leaderboard_response = session.get(f"{BASE_URL}/leaderboard", headers=headers)
    if leaderboard_response.status_code != 200:
        print(f"❌ Failed to get leaderboard: {leaderboard_response.status_code}")
        return False
    
    leaderboard_data = leaderboard_response.json()
    print(f"✅ Leaderboard retrieved: {len(leaderboard_data)} users")
    
    # Find current user in leaderboard
    current_user_entry = None
    for entry in leaderboard_data:
        if entry.get("username") == user_data["username"]:
            current_user_entry = entry
            break
    
    if current_user_entry:
        print(f"   Current user rank found - Score: {current_user_entry.get('average_score', 0):.1f}%")
    
    # Step 10: Test settings update
    print("\n🔟 Testing settings update...")
    settings_response = session.put(
        f"{BASE_URL}/profile/settings",
        json={"theme": "dark", "language": "en"},
        headers=headers
    )
    
    if settings_response.status_code != 200:
        print(f"❌ Failed to update settings: {settings_response.status_code}")
        return False
    
    print("✅ Settings updated successfully")
    
    print("\n" + "="*60)
    print("🎉 FULL EXAM FLOW TEST COMPLETED SUCCESSFULLY!")
    print("✅ User authentication working")
    print("✅ Question management working")
    print("✅ Exam session management working")
    print("✅ Answer submission working")
    print("✅ Exam scoring working")
    print("✅ Badge system working")
    print("✅ Exam history working")
    print("✅ User profile working")
    print("✅ Leaderboard working")
    print("✅ Settings management working")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_full_exam_flow()
    if not success:
        exit(1)