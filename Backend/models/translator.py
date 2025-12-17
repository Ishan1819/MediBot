import os
import google.generativeai as genai
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Language mappings
LANGUAGE_NAMES = {
    "mr": "Marathi",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "or": "Odia",
    "bn": "Bengali",
    "pa": "Punjabi",
    "kn": "Kannada",
    "as": "Assamese",
    "ur": "Urdu",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}


def detect_language(text: str) -> str:
    """
    Detects the language of the input text.
    
    Args:
        text: Input text to detect language
        
    Returns:
        str: Language code (e.g., 'en', 'mr', 'hi')
    """
    try:
        lang = detect(text)
        print(f"🌐 Detected language: {lang} ({LANGUAGE_NAMES.get(lang, 'Unknown')})")
        return lang
    except LangDetectException as e:
        print(f"⚠️ Language detection failed: {e}. Defaulting to English.")
        return "en"


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translates text from source language to English using Gemini.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        
    Returns:
        str: Translated English text
    """
    if source_lang == "en":
        return text
    
    try:
        print(f"🌍 Translating from {LANGUAGE_NAMES.get(source_lang, source_lang)} to English...")
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        prompt = (
            f"Translate the following {LANGUAGE_NAMES.get(source_lang, source_lang)} text into fluent English:\n\n"
            f"{text}\n\n"
            f"Output ONLY the English translation, nothing else."
        )
        
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        print(f"✅ Translation: {translated_text}")
        return translated_text
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text  # Return original if translation fails


def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translates English text to target language using Gemini.
    
    Args:
        text: English text to translate
        target_lang: Target language code
        
    Returns:
        str: Translated text in target language
    """
    if target_lang == "en":
        return text
    
    try:
        print(f"🌍 Translating from English to {LANGUAGE_NAMES.get(target_lang, target_lang)}...")
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        prompt = (
            f"Translate the following English text into fluent {LANGUAGE_NAMES.get(target_lang, target_lang)}:\n\n"
            f"{text}\n\n"
            f"Output ONLY the {LANGUAGE_NAMES.get(target_lang, target_lang)} translation, nothing else."
            f"Maintain the same formatting (bullet points, markdown, etc.)."
        )
        
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        print(f"✅ Translation complete")
        return translated_text
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text  # Return original if translation fails


def process_multilingual_query(query: str) -> tuple:
    """
    Process a query in any language and prepare for RAG processing.
    
    Args:
        query: User query in any language
        
    Returns:
        tuple: (english_query, detected_language)
    """
    detected_lang = detect_language(query)
    
    # Check if query explicitly asks for English response
    english_indicators = ["give in english", "in english", "translate to english", "english mein"]
    override_to_english = any(indicator in query.lower() for indicator in english_indicators)
    
    if override_to_english:
        # Remove the English request from query
        clean_query = query.lower()
        for indicator in english_indicators:
            clean_query = clean_query.replace(indicator, "")
        query = clean_query.strip()
        detected_lang = "en"  # Override to English
        print("🔄 User requested English response")
    
    # Translate query to English for RAG processing
    english_query = translate_to_english(query, detected_lang)
    
    return english_query, detected_lang
