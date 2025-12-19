import os
import google.generativeai as genai
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Language mappings - ONLY these languages are supported
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

# Supported language codes - if detected language is not in this list, default to English
SUPPORTED_LANGUAGES = list(LANGUAGE_NAMES.keys())


def is_greeting(text: str) -> bool:
    """
    Checks if the text is a PURE greeting (not a question with greeting words).
    
    Args:
        text: Input text to check
        
    Returns:
        bool: True if greeting, False otherwise
    """
    # Pure greetings (exact matches or starts with)
    pure_greetings = [
        # English - exact matches
        "hi", "hello", "hey", "hii", "hiii", "hello!", "hi!", "hey!",
        # English - phrases
        "good morning", "good afternoon", "good evening", "good night",
        "greetings", "howdy", "what's up", "whats up", "good day",
        # Marathi
        "नमस्कार", "नमस्ते", "हॅलो", "हाय",
        # Hindi
        "नमस्ते", "सुप्रभात", "शुभ संध्या",
    ]
    
    text_lower = text.lower().strip()
    
    # Remove punctuation for comparison
    import string
    text_clean = text_lower.translate(str.maketrans('', '', string.punctuation))
    
    # Check if it's ONLY a greeting (not a question or statement)
    # If text contains question words or is longer than a simple greeting, it's not a pure greeting
    question_words = ["what", "how", "when", "where", "why", "who", "which", "should", "can", "is", "are", "do", "does", "will", "would"]
    
    # If it contains question words or is a long sentence, it's not a pure greeting
    if any(qword in text_lower for qword in question_words):
        return False
    
    # Check if text is exactly a greeting or starts with one (followed by nothing or just punctuation)
    for greeting in pure_greetings:
        if text_clean == greeting or text_clean == greeting.strip():
            return True
    
    return False


def detect_language(text: str) -> str:
    """
    Detects the language of the input text and validates against supported languages.
    
    Args:
        text: Input text to detect language
        
    Returns:
        str: Language code (e.g., 'en', 'mr', 'hi') - defaults to 'en' if unsupported
    """
    try:
        detected_lang = detect(text)
        print(f"🌐 Raw detected language: {detected_lang}")
        
        # Check if detected language is in our supported list
        if detected_lang in SUPPORTED_LANGUAGES:
            print(f"✅ Supported language: {detected_lang} ({LANGUAGE_NAMES.get(detected_lang, 'Unknown')})")
            return detected_lang
        else:
            print(f"⚠️ Unsupported language '{detected_lang}' detected. Defaulting to English.")
            return "en"
            
    except LangDetectException as e:
        print(f"⚠️ Language detection failed: {e}. Defaulting to English.")
        return "en"


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translates text from source language to English using Gemini.
    Only translates if source language is in supported list.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        
    Returns:
        str: Translated English text
    """
    # If already English or unsupported language, return as is
    if source_lang == "en":
        return text
    
    # Validate source language is supported
    if source_lang not in SUPPORTED_LANGUAGES:
        print(f"⚠️ Source language '{source_lang}' not supported. Treating as English.")
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
    Only translates if target language is in supported list.
    
    Args:
        text: English text to translate
        target_lang: Target language code
        
    Returns:
        str: Translated text in target language (or original if unsupported)
    """
    # If already English or unsupported language, return as is
    if target_lang == "en":
        return text
    
    # Validate target language is supported
    if target_lang not in SUPPORTED_LANGUAGES:
        print(f"⚠️ Target language '{target_lang}' not supported. Returning English response.")
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
        tuple: (english_query, detected_language, is_greeting_flag)
    """
    # Check if it's a greeting - always respond in English for greetings
    is_greeting_msg = is_greeting(query)
    
    detected_lang = detect_language(query)
    
    # Check if query explicitly asks for English response
    english_indicators = ["give in english", "in english", "translate to english", "english mein", "english me"]
    override_to_english = any(indicator in query.lower() for indicator in english_indicators)
    
    # Force English for greetings or explicit English request
    if is_greeting_msg or override_to_english:
        if override_to_english:
            # Remove the English request from query
            clean_query = query.lower()
            for indicator in english_indicators:
                clean_query = clean_query.replace(indicator, "")
            query = clean_query.strip()
        detected_lang = "en"  # Override to English
        print("🔄 Responding in English (greeting or explicit request)")
    
    # Translate query to English for RAG processing (if not already English)
    if detected_lang != "en":
        english_query = translate_to_english(query, detected_lang)
    else:
        english_query = query
    
    return english_query, detected_lang, is_greeting_msg
