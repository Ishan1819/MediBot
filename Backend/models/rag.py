import requests
from bs4 import BeautifulSoup
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai


def extract_text_from_website(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()  
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        return " ".join([p.get_text() for p in paragraphs]) if paragraphs else "No content available."
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return "Error fetching content."

# URLs for maternity guidance
career_urls = [
    # maternity hopitals in pune
    "https://www.pmc.gov.in/en/hosp-list",
    "https://www.justdial.com/Pune/Maternity-Hospitals/nct-10314263",
    "https://www.pmc.gov.in/en/hospital_list",
    # general
    "https://resources.healthgrades.com/right-care/pregnancy/9-months-pregnant",
    "https://nhsrcindia.org/sites/default/files/2021-12/Care%20During%20Pregnancy%20and%20Childbirth%20Training%20Manual%20for%20CHO%20at%20AB-HWC.pdf",
    "https://www.healthline.com/health/pregnancy/9-months-pregnant#symptoms",
    "https://www.stemcyteindia.com/9month/#:~:text=9th%20months%20pregnant%20baby's%20position,and%2050.7cm%20in%20height",
    "https://vanshivf.com/9-month-pregnancy-care-tips/",
    "https://www.in.pampers.com/pregnancy/pregnancy-calendar/9-months-pregnant",
    "https://aurawomen.in/blog/how-to-take-care-of-nine-months-pregnancy/",
    # complications
    "https://www.nichd.nih.gov/health/topics/pregnancy/conditioninfo/complications",
    "https://my.clevelandclinic.org/health/articles/24442-pregnancy-complications",
    # breastfeeding
    "https://llli.org/breastfeeding-info/",
    # postpartum recovery
    "https://familydoctor.org/recovering-from-delivery/",
    # symptoms during pregnancy
    "https://my.clevelandclinic.org/health/articles/pregnancy-pains",
    "https://www.betterhealth.vic.gov.au/health/healthyliving/pregnancy-signs-and-symptoms",
    "https://www.medparkhospital.com/en-US/lifestyles/symptoms-of-pregnancy",
    # fetal development milestones
    "https://my.clevelandclinic.org/health/articles/7247-fetal-development-stages-of-growth",
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/prenatal-care/art-20045302",
    # vaccination
    "https://www.marchofdimes.org/find-support/topics/planning-baby/vaccinations-and-pregnancy",
    "https://www.acog.org/womens-health/faqs/routine-tests-during-pregnancy",
    # dietary guidelines
    "https://www.mayoclinic.org/healthy-lifestyle/pregnancy-week-by-week/in-depth/pregnancy-nutrition/art-20043844",
    "https://www.nhs.uk/pregnancy/keeping-well/have-a-healthy-diet/",
    # safe medications during pregnancy
    "https://health.clevelandclinic.org/pregnancy-safe-medications",
    "https://www.medicinesinpregnancy.org/",
    # signs of labor and when to go to hospital
    "https://www.nhs.uk/pregnancy/labour-and-birth/signs-of-labour/signs-that-labour-has-begun/"
]

#loading embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./career_db")
collection = chroma_client.get_or_create_collection(name="career_guidance")

#ChromaDB - Add documents with source metadata
existing_ids = set(collection.get()["ids"])
for url in career_urls:
    if url not in existing_ids:
        text = extract_text_from_website(url)
        collection.add(
            ids=[url],
            documents=[text],
            metadatas=[{"source": url}]  # Add source metadata
        )

genai.configure(api_key="AIzaSyDlC2TVSnLedPYPZW2RON1pi99ZF2jM7lE")


def needs_history_context(query: str) -> bool:
    """
    Uses LLM to determine if the current query depends on previous conversation context.
    
    Args:
        query: Current user query (in English)
    
    Returns:
        bool: True if query needs conversation history, False otherwise
    """
    try:
        prompt = f"""You are a conversation analyzer. Your task is to determine if the following question requires previous conversation context to be answered correctly.

Question: "{query}"

Does this question DEPEND ON or REFER TO previous conversation context (e.g., uses words like "it", "that", "tell me more", "continue", "elaborate", "what about", etc.)?

Answer with ONLY one word: YES or NO

Answer:"""
        
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        answer = response.text.strip().upper()
        
        return "YES" in answer
    except Exception as e:
        print(f"Error in needs_history_context: {e}")
        # Default to False - treat as independent query
        return False


def summarize_conversation_history(history: list) -> str:
    """
    Uses LLM to summarize conversation history into concise bullet points.
    
    Args:
        history: List of dicts with 'role' and 'content' keys
                 [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    
    Returns:
        str: Concise summary (1-2 bullet points) of medical topics discussed
    """
    if not history:
        return ""
    
    try:
        # Format history for summarization (role-based, last 10 messages max)
        formatted_history = ""
        for i, msg in enumerate(history[-10:], 1):
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            formatted_history += f"{role_label}: {msg['content']}\n\n"
        
        prompt = f"""
You are a MEDICAL CONVERSATION SUMMARIZER.

Your task is to identify the LAST ACTIVE MEDICAL TOPIC discussed in the conversation
and the user's intent related to that topic.

IMPORTANT RULES:
- If the current or recent user queries are VERY SHORT or VAGUE
  (e.g. "safe?", "is it safe?", "dangerous?", "explain", "tell me more", "continue"),
  you MUST infer that they refer to the LAST CLEAR MEDICAL TOPIC.
- If there is ANY ambiguity about which topic the user refers to,
  ALWAYS choose the MOST RECENT medical topic.
- DO NOT ask clarifying questions.
- DO NOT introduce new topics.
- DO NOT include greetings, language, tone, or advice.
- DO NOT include explanations or recommendations.

Conversation History:
{formatted_history}

OUTPUT FORMAT:
- Provide 1–2 SHORT bullet points
- Each bullet must describe:
  • the medical topic
  • the user’s concern or intent

Example output:
- Iron supplementation during the second trimester and concerns about its safety.

Summary:
"""
        
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        return summary
    except Exception as e:
        print(f"Error in summarize_conversation_history: {e}")
        return ""



def get_best_maternity_guide(query, results, conversation_history=None, target_language="en", is_greeting=False, is_non_rag=False):
    """
    Fetches the best response based on AI guidance and retrieved documents.
    
    Args:
        query: User query (in English after translation)
        results: ChromaDB search results
        conversation_history: List of dicts with 'role' and 'content' keys (optional)
                              [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        target_language: Language code for response (default: "en")
        is_greeting: Whether the query is a greeting
        is_non_rag: Whether the query is a non-RAG intent (identity, capability, privacy)
    
    Returns:
        str: Response in the target language
    """
    if not results["documents"]:
        error_msg = "Sorry, I couldn't find relevant information."
        # Translate error message if needed
        if target_language != "en":
            from Backend.models.translator import translate_from_english
            return translate_from_english(error_msg, target_language)
        return error_msg

    matched_texts = "\n\n".join(results["documents"][0])
    
    # Extract unique source URLs from metadata
    source_urls = []
    if "metadatas" in results and results["metadatas"]:
        for metadata_list in results["metadatas"]:
            for metadata in metadata_list:
                if metadata and "source" in metadata:
                    source_url = metadata["source"]
                    if source_url not in source_urls:
                        source_urls.append(source_url)
    
    # LLM-based follow-up detection and history summarization
    history_context_for_system = ""
    topic_anchoring_rule = ""
    needs_context = False
    
    # Only check for history context if NOT a greeting and history exists
    # if conversation_history and not is_greeting:
        # Check if query needs conversation context
        # needs_context = needs_history_context(query)
        
        # if needs_context:
            # Summarize conversation history
    summary = summarize_conversation_history(conversation_history)
    print(f"Conversation history summary: {summary}")
    if summary:
        history_context_for_system = f"\n\nPREVIOUS CONTEXT (FOR UNDERSTANDING ONLY):\n{summary}"
        # Add topic anchoring rule for follow-ups
        topic_anchoring_rule = "\n\nTOPIC ANCHORING RULE: This is a FOLLOW-UP question. You MUST answer STRICTLY within the scope of the MOST RECENT medical topic from the previous context. DO NOT introduce new topics or switch subjects. Stay focused on what was just discussed."
    
    print("Here")
    # Language instruction based ONLY on current query - HARD OVERRIDE
    language_instruction = ""
    if target_language != "en":
        from Backend.models.translator import LANGUAGE_NAMES
        lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        language_instruction = f"\n\nCRITICAL LANGUAGE INSTRUCTION: You MUST respond ONLY in {lang_name} language. IGNORE any language used in previous messages. The response language is determined EXCLUSIVELY by the CURRENT query, NOT by conversation history."
    
    # Special handling for greetings - ONLY if no conversation history
    greeting_instruction = ""
    if is_greeting and not conversation_history:
        greeting_instruction = "\n\nGREETING DETECTED: The user has ONLY greeted you. Respond in ENGLISH with ONLY a warm, brief greeting. Example: 'Hello! I'm Dr. MAMA, your pregnancy care assistant. How can I help you today?' DO NOT include any medical information."
        language_instruction = ""  # Override language instruction for greetings
    elif is_greeting and conversation_history:
        # If greeting but history exists, treat as normal query (user might be being polite)
        pass
    
    system_prompt = f"""
    
    You are Dr. MAMA, a helpful AI assistant specializing in pregnancy and postpartum care.
    You were created by Ishan Patil to help expecting mothers and new parents.
    
    CRITICAL RULES:
    1. GREETINGS → If user ONLY says hi/hello (no question), respond ONLY with: "Hello! I'm Dr. MAMA. How can I help you today?" Nothing else.
    2. CREATOR → If asked who created you, say "I was created by Ishan Patil."
    3. LANGUAGE → Respond ONLY in the language of the CURRENT query. COMPLETELY IGNORE any language from conversation history.
    4. FOLLOW-UP QUESTIONS → If user says "tell me more" or similar, expand ONLY on the previous topic from the context below.
    5. INDEPENDENT QUESTIONS → If it's a new/different question, provide fresh answer. Don't mix with previous topics.
    6. FOCUS → Answer ONLY what was asked. No extra summaries unless requested.
    7. Don't answer in Indonesian (Bahasa Indonesia) 🇮🇩 ever.
    
    CONVERSATION HISTORY USAGE:
    - Previous context is provided ONLY when the current query is a follow-up
    - History is for topic continuity, NOT for language style
    - NEVER copy language from history
    
    DO NOT repeat greetings in responses to medical questions.
    DO NOT mix answers from different topics unless explicitly asked.

    For medical information:
    - Use bullet points and sections for clarity
    - Use markdown formatting
    - Use **bold** for important terms and *italics* for emphasis
    - Keep answers concise and precise{history_context_for_system}{topic_anchoring_rule}{language_instruction}{greeting_instruction}
    """

    user_prompt = f"User Query: {query}\n\nExtracted Information:\n{matched_texts}"

    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    response = model.generate_content(system_prompt + "\n\n" + user_prompt)

    # Clean up the response to ensure proper formatting
    formatted_response = response.text.strip()
    
    # Append sources ONLY for informational RAG-based responses
    # DO NOT show sources for:
    # - Greetings (hi, hello, etc.)
    # - Non-RAG intents (identity questions like "who am I?", capability questions, privacy)
    # - Any response that doesn't rely on retrieved documents
    should_show_sources = (
        source_urls and  # Sources exist (documents were retrieved)
        len(source_urls) > 0 and  # At least one source
        not is_greeting and  # Not a greeting
        not is_non_rag  # Not an identity/capability/privacy question
    )
    
    if should_show_sources:
        formatted_response += "\n\n---\n**Sources:**\n"
        for source in source_urls:
            formatted_response += f"- {source}\n"
    
    return formatted_response
