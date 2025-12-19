from fastapi import FastAPI
from Backend.routers import reminder_route, whisper_route, hospital_route, rag_route, auth_route, chat_history, tts_route
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware  
import uvicorn

app = FastAPI(title="MediBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Cookie", "Set-Cookie"],
    expose_headers=["Set-Cookie"],
)

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

# Include routers
app.include_router(reminder_route.router, prefix="/reminder", tags=["Reminders"])
app.include_router(whisper_route.router, prefix="/api/transcribe", tags=["Audio Transcription"])
app.include_router(hospital_route.router, prefix="/hospital", tags=["Hospital Finder"])
app.include_router(rag_route.router, prefix="/rag", tags=["RAG Queries"])
app.include_router(whisper_route.router, prefix="/api/speech", tags=["Speech Recognition"])
app.include_router(auth_route.router, prefix="/api", tags=["Authentication"])
app.include_router(chat_history.router, prefix="/history", tags=["Chat History"])
app.include_router(tts_route.router, prefix="/tts", tags=["Text to Speech"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
