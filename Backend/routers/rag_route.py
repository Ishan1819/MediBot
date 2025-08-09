# # from fastapi import APIRouter, HTTPException
# # from pydantic import BaseModel
# # from ..models.rag import collection, get_best_maternity_guide

# # router = APIRouter()

# # class QueryRequest(BaseModel):
# #     message: str

# # @router.post("/query_rag/")
# # async def query_rag(request: QueryRequest):
# #     try:
# #         # Query the ChromaDB collection
# #         results = collection.query(
# #             query_texts=[request.message],
# #             n_results=3
# #         )
        
# #         # Get response using the RAG model
# #         response = get_best_maternity_guide(
# #             query=request.message,
# #             results=results,
# #             conversation_history=[]  # You can maintain conversation history if needed
# #         )
        
# #         return {"response": response}
    
# #     except Exception as e:
# #         print(f"Error in RAG query: {str(e)}")  # Log the error
# #         raise HTTPException(
# #             status_code=500,
# #             detail="Failed to process your query. Please try again."
# #         )
        
        
        
        
        
        
        
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from ..models.rag import collection, get_best_maternity_guide
# from Backend.routers.auth_route import connection  # ✅ Import your db connection (adjust if needed)

# router = APIRouter()

# class QueryRequest(BaseModel):
#     user_id: int
#     message: str

# @router.post("/query_rag/")
# async def query_rag(request: QueryRequest):
#     # data = await request.json()
#     print("Incoming request:", request.dict())
#     print("User ID:", request.user_id)
#     print("Message:", request.message)

#     try:
#         # Step 1: Query ChromaDB
#         results = collection.query(
#             query_texts=[request.message],
#             n_results=3
#         )
        
#         # Step 2: Get the RAG-based response
#         response = get_best_maternity_guide(
#             query=request.message,
#             results=results,
#             conversation_history=[]
#         )

#         # Step 3: Save message + response to DB
#         with connection.cursor() as cursor:
#             cursor.execute(
#                 "INSERT INTO messages (user_id, message, response) VALUES (%s, %s, %s)",
#                 (request.user_id, request.message, response)
#             )
#             connection.commit()

#         # Step 4: Return response to frontend
#         return {"response": response}
    
#     except Exception as e:
#         print(f"Error in RAG query: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to process your query. Please try again."
#         )



























from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import json

from ..models.rag import collection, get_best_maternity_guide
from Backend.routers.auth_route import connection  # import DB connection

router = APIRouter()

class QueryRequest(BaseModel):
    message: str
    # removed user_id from request body, it will come from cookie


@router.post("/query_rag/")
async def query_rag(request: Request, data: QueryRequest):
    # Extract user info from cookies
    user_cookie = request.cookies.get("user")
    if not user_cookie:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login.")

    try:
        user_info = json.loads(user_cookie)
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user cookie. Please login again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user cookie format. Please login again.")

    print("User ID from cookie:", user_id)
    print("Message from request body:", data.message)

    try:
        # Step 1: Query ChromaDB
        results = collection.query(
            query_texts=[data.message],
            n_results=3
        )

        # Step 2: Get the RAG-based response
        response_text = get_best_maternity_guide(
            query=data.message,
            results=results,
            conversation_history=[]
        )

        # Step 3: Save message + response to DB with user_id from cookie
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages (user_id, message, response) VALUES (%s, %s, %s)",
                (user_id, data.message, response_text)
            )
            connection.commit()

        # Step 4: Return response to frontend
        return {"response": response_text}

    except Exception as e:
        print(f"Error in RAG query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your query. Please try again."
        )
