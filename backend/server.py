from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import jwt
import uuid
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from enum import Enum
from bson import ObjectId
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create FastAPI app
app = FastAPI(title="E-Exam Preparation System", version="1.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ExamStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUBMITTED = "submitted"

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_exams: int = 0
    total_score: float = 0.0
    badges: List[str] = []
    theme: str = "light"
    language: str = "en"
    following: List[str] = []
    followers: List[str] = []

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: DifficultyLevel
    category: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuestionCreate(BaseModel):
    text: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: DifficultyLevel
    category: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None

class ExamSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    questions: List[str]  # question IDs
    answers: Dict[str, int] = {}  # question_id -> selected_option_index
    score: Optional[float] = None
    status: ExamStatus = ExamStatus.IN_PROGRESS
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    time_limit: int = 30  # minutes

class ExamResult(BaseModel):
    session_id: str
    score: float
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    time_taken: int  # minutes
    detailed_results: List[Dict[str, Any]]

class Badge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    icon: str
    criteria: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = serialize_doc(value)
            else:
                serialized[key] = value
        return serialized
    
    return doc

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def check_and_award_badges(user: User):
    """Check if user qualifies for any badges and award them"""
    badges_to_award = []
    
    # Badge: First Exam
    if user.total_exams == 1 and "first_exam" not in user.badges:
        badges_to_award.append("first_exam")
    
    # Badge: 10 Exams
    if user.total_exams == 10 and "ten_exams" not in user.badges:
        badges_to_award.append("ten_exams")
    
    # Badge: High Scorer (average score > 80%)
    if user.total_exams > 0 and (user.total_score / user.total_exams) > 80 and "high_scorer" not in user.badges:
        badges_to_award.append("high_scorer")
    
    if badges_to_award:
        await db.users.update_one(
            {"id": user.id},
            {"$push": {"badges": {"$each": badges_to_award}}}
        )
        return badges_to_award
    
    return []

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": serialize_doc(user.dict())}

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": serialize_doc(user)}

@api_router.get("/auth/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

# Question management endpoints
@api_router.post("/questions")
async def create_question(question_data: QuestionCreate, current_user: User = Depends(get_current_user)):
    question = Question(**question_data.dict())
    await db.questions.insert_one(question.dict())
    return question

@api_router.get("/questions")
async def get_questions(
    category: Optional[str] = None,
    difficulty: Optional[DifficultyLevel] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    filter_query = {}
    if category:
        filter_query["category"] = category
    if difficulty:
        filter_query["difficulty"] = difficulty
    
    questions = await db.questions.find(filter_query).limit(limit).to_list(limit)
    return [Question(**q) for q in questions]

@api_router.get("/questions/random")
async def get_random_question(current_user: User = Depends(get_current_user)):
    pipeline = [{"$sample": {"size": 1}}]
    questions = await db.questions.aggregate(pipeline).to_list(1)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")
    return Question(**questions[0])

# Exam session endpoints
@api_router.post("/exam/start")
async def start_exam(
    num_questions: int = 10,
    category: Optional[str] = None,
    difficulty: Optional[DifficultyLevel] = None,
    current_user: User = Depends(get_current_user)
):
    # Build query for random questions
    filter_query = {}
    if category:
        filter_query["category"] = category
    if difficulty:
        filter_query["difficulty"] = difficulty
    
    # Get random questions
    pipeline = [{"$match": filter_query}, {"$sample": {"size": num_questions}}]
    questions = await db.questions.aggregate(pipeline).to_list(num_questions)
    
    if len(questions) < num_questions:
        raise HTTPException(status_code=400, detail="Not enough questions available")
    
    # Create exam session
    exam_session = ExamSession(
        user_id=current_user.id,
        questions=[q["id"] for q in questions]
    )
    
    await db.exam_sessions.insert_one(exam_session.dict())
    
    # Return questions without correct answers
    safe_questions = []
    for q in questions:
        safe_q = {
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],
            "difficulty": q["difficulty"],
            "category": q["category"],
            "image_url": q.get("image_url"),
            "video_url": q.get("video_url")
        }
        safe_questions.append(safe_q)
    
    return {
        "session_id": exam_session.id,
        "questions": safe_questions,
        "time_limit": exam_session.time_limit
    }

@api_router.post("/exam/{session_id}/answer")
async def submit_answer(
    session_id: str,
    question_id: str,
    selected_option: int,
    current_user: User = Depends(get_current_user)
):
    session = await db.exam_sessions.find_one({"id": session_id, "user_id": current_user.id})
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")
    
    if session["status"] != ExamStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Exam session is not active")
    
    # Update answer
    await db.exam_sessions.update_one(
        {"id": session_id},
        {"$set": {f"answers.{question_id}": selected_option}}
    )
    
    return {"message": "Answer submitted successfully"}

@api_router.post("/exam/{session_id}/submit")
async def submit_exam(session_id: str, current_user: User = Depends(get_current_user)):
    session = await db.exam_sessions.find_one({"id": session_id, "user_id": current_user.id})
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")
    
    if session["status"] != ExamStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Exam session is not active")
    
    # Get all questions for this session
    questions = await db.questions.find({"id": {"$in": session["questions"]}}).to_list(len(session["questions"]))
    question_dict = {q["id"]: q for q in questions}
    
    # Calculate score
    total_questions = len(session["questions"])
    correct_answers = 0
    detailed_results = []
    
    for question_id in session["questions"]:
        question = question_dict[question_id]
        user_answer = session["answers"].get(question_id)
        correct_answer = question["correct_answer"]
        is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_answers += 1
        
        detailed_results.append({
            "question_id": question_id,
            "question_text": question["text"],
            "options": question["options"],
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question["explanation"]
        })
    
    score = (correct_answers / total_questions) * 100
    
    # Update session
    completed_at = datetime.utcnow()
    time_taken = int((completed_at - session["started_at"]).total_seconds() / 60)
    
    await db.exam_sessions.update_one(
        {"id": session_id},
        {
            "$set": {
                "status": ExamStatus.COMPLETED,
                "score": score,
                "completed_at": completed_at
            }
        }
    )
    
    # Update user stats
    await db.users.update_one(
        {"id": current_user.id},
        {
            "$inc": {
                "total_exams": 1,
                "total_score": score
            }
        }
    )
    
    # Check for badges
    updated_user = await db.users.find_one({"id": current_user.id})
    new_badges = await check_and_award_badges(User(**updated_user))
    
    # Create result
    result = ExamResult(
        session_id=session_id,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_answers,
        incorrect_answers=total_questions - correct_answers,
        time_taken=time_taken,
        detailed_results=detailed_results
    )
    
    return {
        "result": result,
        "new_badges": new_badges
    }

@api_router.get("/exam/history")
async def get_exam_history(current_user: User = Depends(get_current_user)):
    try:
        sessions = await db.exam_sessions.find(
            {"user_id": current_user.id, "status": ExamStatus.COMPLETED}
        ).sort("completed_at", -1).to_list(50)
        
        # Serialize documents to handle ObjectId
        serialized_sessions = serialize_doc(sessions)
        return serialized_sessions
    except Exception as e:
        logger.error(f"Error in exam history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# User profile endpoints
@api_router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    try:
        # Get recent exam sessions
        recent_sessions = await db.exam_sessions.find(
            {"user_id": current_user.id, "status": ExamStatus.COMPLETED}
        ).sort("completed_at", -1).limit(5).to_list(5)
        
        # Serialize sessions to handle ObjectId
        serialized_sessions = serialize_doc(recent_sessions)
        
        # Calculate average score
        avg_score = 0
        if current_user.total_exams > 0:
            avg_score = current_user.total_score / current_user.total_exams
        
        return {
            "user": serialize_doc(current_user.dict()),
            "recent_sessions": serialized_sessions,
            "average_score": avg_score,
            "total_exams": current_user.total_exams
        }
    except Exception as e:
        logger.error(f"Error in profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.put("/profile/settings")
async def update_settings(
    theme: Optional[str] = None,
    language: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    update_data = {}
    if theme:
        update_data["theme"] = theme
    if language:
        update_data["language"] = language
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Settings updated successfully"}

# Leaderboard endpoint
@api_router.get("/leaderboard")
async def get_leaderboard(current_user: User = Depends(get_current_user)):
    try:
        pipeline = [
            {"$match": {"total_exams": {"$gt": 0}}},
            {"$addFields": {"average_score": {"$divide": ["$total_score", "$total_exams"]}}},
            {"$sort": {"average_score": -1}},
            {"$limit": 10},
            {"$project": {
                "username": 1,
                "total_exams": 1,
                "average_score": 1,
                "badges": 1
            }}
        ]
        
        leaderboard = await db.users.aggregate(pipeline).to_list(10)
        
        # Serialize documents to handle ObjectId
        serialized_leaderboard = serialize_doc(leaderboard)
        return serialized_leaderboard
    except Exception as e:
        logger.error(f"Error in leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Initialize default questions
@api_router.post("/admin/init")
async def initialize_questions():
    # Check if questions already exist
    existing_questions = await db.questions.count_documents({})
    if existing_questions > 0:
        return {"message": "Questions already initialized"}
    
    # Sample questions
    sample_questions = [
        {
            "text": "What is the capital of France?",
            "options": ["London", "Berlin", "Paris", "Madrid"],
            "correct_answer": 2,
            "explanation": "Paris is the capital city of France.",
            "difficulty": "easy",
            "category": "Geography"
        },
        {
            "text": "Which planet is known as the Red Planet?",
            "options": ["Venus", "Mars", "Jupiter", "Saturn"],
            "correct_answer": 1,
            "explanation": "Mars is called the Red Planet because of its reddish appearance.",
            "difficulty": "easy",
            "category": "Science"
        },
        {
            "text": "What is 15 × 7?",
            "options": ["105", "95", "115", "85"],
            "correct_answer": 0,
            "explanation": "15 × 7 = 105",
            "difficulty": "medium",
            "category": "Mathematics"
        },
        {
            "text": "Who wrote 'Romeo and Juliet'?",
            "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
            "correct_answer": 1,
            "explanation": "Romeo and Juliet was written by William Shakespeare.",
            "difficulty": "medium",
            "category": "Literature"
        },
        {
            "text": "What is the chemical symbol for gold?",
            "options": ["Go", "Gd", "Au", "Ag"],
            "correct_answer": 2,
            "explanation": "Au is the chemical symbol for gold, from the Latin word 'aurum'.",
            "difficulty": "hard",
            "category": "Chemistry"
        }
    ]
    
    # Insert sample questions
    questions_to_insert = []
    for q_data in sample_questions:
        question = Question(**q_data)
        questions_to_insert.append(question.dict())
    
    await db.questions.insert_many(questions_to_insert)
    return {"message": f"Initialized {len(sample_questions)} questions"}

# Include the router in the main app
app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()