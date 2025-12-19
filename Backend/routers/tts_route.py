from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
import os
import tempfile
import hashlib

router = APIRouter()

# Language code mapping for gTTS
GTTS_LANGUAGE_MAP = {
    "en": "en",
    "mr": "mr",  # Marathi
    "hi": "hi",  # Hindi
    "ta": "ta",  # Tamil
    "te": "te",  # Telugu
    "ml": "ml",  # Malayalam
    "gu": "gu",  # Gujarati
    "bn": "bn",  # Bengali
    "pa": "pa",  # Punjabi (not well supported, fallback to hi)
    "kn": "kn",  # Kannada
    "ur": "ur",  # Urdu
    "es": "es",  # Spanish
    "fr": "fr",  # French
    "de": "de",  # German
}


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


@router.post("/text-to-speech/")
async def text_to_speech(data: TTSRequest):
    """
    Converts text to speech in the specified language.
    
    Args:
        text: Text to convert to speech
        language: Language code (e.g., 'en', 'mr', 'hi')
    
    Returns:
        Audio file in MP3 format
    """
    try:
        # Get the appropriate language code for gTTS
        lang_code = GTTS_LANGUAGE_MAP.get(data.language, "en")
        
        # Fallback for unsupported languages
        if data.language == "pa":  # Punjabi not well supported
            lang_code = "hi"  # Use Hindi as fallback
        
        print(f"🔊 Generating TTS for language: {data.language} (using {lang_code})")
        print(f"📝 Text length: {len(data.text)} characters")
        
        # Generate unique filename based on text and language
        text_hash = hashlib.md5(f"{data.text}{data.language}".encode()).hexdigest()
        filename = f"tts_{text_hash}.mp3"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        # Check if file already exists (cache)
        if not os.path.exists(filepath):
            # Create TTS object and save
            tts = gTTS(text=data.text, lang=lang_code, slow=False)
            tts.save(filepath)
            print(f"✅ Audio file generated: {filepath}")
        else:
            print(f"📦 Using cached audio file: {filepath}")
        
        # Return the audio file
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            filename=filename,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
    
    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate speech: {str(e)}"
        )


@router.get("/supported-languages/")
async def get_supported_languages():
    """
    Returns list of supported languages for TTS.
    """
    return {
        "supported_languages": list(GTTS_LANGUAGE_MAP.keys()),
        "language_names": {
            "en": "English",
            "mr": "Marathi",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "gu": "Gujarati",
            "bn": "Bengali",
            "pa": "Punjabi",
            "kn": "Kannada",
            "ur": "Urdu",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
        }
    }
