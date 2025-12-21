from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
import pymysql
import bcrypt
import os
import json
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
from Backend.session_manager import session_manager 

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

connection = pymysql.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE,
    cursorclass=DictCursor,
    autocommit=True
)

router = APIRouter()

class SignupData(BaseModel):
    email: EmailStr
    password: str

class LoginData(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
async def signup(data: SignupData):
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (data.email, hashed_pw))

    return {"message": "✅ Sign up successful", "email": data.email}


@router.post("/login")
async def login(data: LoginData, response: Response):
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id, password_hash FROM users WHERE email = %s", (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Username not valid. Please signup first"
            )

        if not bcrypt.checkpw(data.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
            raise HTTPException(
                status_code=401,
                detail="Password doesn't match"
            )
    
    # Create server-side session (invalidates old sessions)
    session_id = session_manager.create_session(
        user_id=user["user_id"],
        email=data.email
    )
    
    # Set session_id cookie (NEVER store user_id directly in cookie)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=False,  # Set to False for development (frontend needs to read it)
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",  # CSRF protection
        path="/",
        max_age=86400  # 24 hours
    )

    return {
        "message": "✅ Login successful",
        "user_id": user["user_id"],
        "email": data.email
    }


@router.post("/logout")
async def logout(response: Response, request: Request):
    """
    Logout: invalidate session and clear cookie.
    """
    session_id = request.cookies.get("session_id")
    
    if session_id:
        session_manager.invalidate_session(session_id)
    
    # Clear session cookie
    response.delete_cookie(key="session_id", path="/")
    
    return {"message": "✅ Logged out successfully"}
