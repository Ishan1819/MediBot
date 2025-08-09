# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, EmailStr
# import pymysql
# import bcrypt
# import os
# from dotenv import load_dotenv
# from pymysql.cursors import DictCursor 
# # from database import connection 

# load_dotenv()

# # Load DB credentials
# MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# # Connect to MySQL
# connection = pymysql.connect(
#     host=MYSQL_HOST,
#     user=MYSQL_USER,
#     password=MYSQL_PASSWORD,
#     database=MYSQL_DATABASE,
#     cursorclass=DictCursor,
#     autocommit=True
# )

# router = APIRouter()


# # Pydantic Models
# class SignupData(BaseModel):
#     email: EmailStr
#     password: str


# class LoginData(BaseModel):
#     email: EmailStr
#     password: str


# # 🔐 Sign Up Route
# @router.post("/signup")
# async def signup(data: SignupData):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT user_id FROM users WHERE email = %s", (data.email,))
#         if cursor.fetchone():
#             raise HTTPException(status_code=400, detail="Email already registered")

#         hashed_pw = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
#         cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (data.email, hashed_pw))

#     return {"message": "✅ Sign up successful", "email": data.email}


# # 🔓 Login Route
# @router.post("/login")
# async def login(data: LoginData):
#     with connection.cursor() as cursor:
#         # Check if email exists
#         cursor.execute("SELECT user_id, password_hash FROM users WHERE email = %s", (data.email,))
#         user = cursor.fetchone()

#         if not user:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Username not valid. Please signup first"
#             )

#         # Check if password matches
#         if not bcrypt.checkpw(data.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
#             raise HTTPException(
#                 status_code=401,
#                 detail="Password doesn't match"
#             )

#     return {
#         "message": "✅ Login successful",
#         "user_id": user["user_id"],
#         "email": data.email
#     }







from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, EmailStr
import pymysql
import bcrypt
import os
import json
from dotenv import load_dotenv
from pymysql.cursors import DictCursor 

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
    
    # Prepare user info dict to store in cookie
    user_info = {
        "user_id": user["user_id"],
        "email": data.email
    }
    # Set cookie - convert dict to JSON string
    response.set_cookie(key="user", value=json.dumps(user_info), httponly=True, samesite="lax")

    return {
        "message": "✅ Login successful",
        "user_id": user["user_id"],
        "email": data.email
    }
