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


def is_followup_query(query: str) -> bool:
    """
    Detects if a query is a follow-up/continuation request.
    Follow-ups are short, referential queries that depend on recent context.
    
    Args:
        query: User query (in English after translation)
    
    Returns:
        bool: True if query is a follow-up, False otherwise
    """
    query_lower = query.lower().strip()
    
    # Exact match patterns (common follow-ups)
    exact_patterns = [
        "tell me more", "explain", "continue", "go on", "elaborate",
        "what about", "and then", "next", "more info", "more information",
        "tell more", "say more", "more details", "expand", "can you explain",
        "explain more", "tell me about it", "about it", "about that",
        "last one", "last question", "previous", "that one"
    ]
    
    # Pattern for numbered references ("first point", "third point", "point 2", etc.)
    numbered_patterns = [
        "first point", "second point", "third point", "fourth point", "fifth point",
        "last point", "next point", "point 1", "point 2", "point 3", "point 4", "point 5",
        "1st point", "2nd point", "3rd point", "4th point", "5th point"
    ]
    
    # Referential words (it, that, this, those, etc.)
    referential_words = ["it", "that", "this", "those", "these", "them"]
    
    # Check exact patterns
    if query_lower in exact_patterns:
        return True
    
    # Check if starts with exact patterns
    for pattern in exact_patterns + numbered_patterns:
        if query_lower.startswith(pattern):
            return True
    
    # Check if query is very short (1-3 words) and contains referential words
    words = query_lower.split()
    if len(words) <= 3:
        for ref_word in referential_words:
            if ref_word in words:
                return True
    
    # Check for questions about "it" or "that" (e.g., "is it safe?", "what about that?")
    if any(ref in query_lower for ref in ["it ", " it", "that ", " that", "this ", " this"]):
        # But exclude questions that introduce new topics
        new_topic_indicators = ["what is", "who is", "when is", "where is", "why is", "how is"]
        if not any(indicator in query_lower for indicator in new_topic_indicators):
            return True
    
    return False


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


def summarize_conversation_history(history: list, is_followup: bool = False) -> str:
    """
    Summarizes conversation history prioritizing RECENT context.
    
    CONTEXT SELECTION RULE:
    - If is_followup=True → Use ONLY the last assistant response (most recent medical info)
    - If is_followup=False → Use last 5 user-assistant exchanges (last 10 messages)
    
    Args:
        history: List of dicts with 'role' and 'content' keys
                 [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        is_followup: Whether current query is a follow-up (detected by is_followup_query)
    
    Returns:
        str: Concise summary focused on RECENT medical topic
    """
    if not history:
        return ""
    
    try:
        # CRITICAL: Select context based on query type
        if is_followup:
            # For follow-ups: Use ONLY the last assistant response
            # Find the most recent assistant message
            relevant_history = []
            for msg in reversed(history):
                if msg['role'] == 'assistant':
                    relevant_history = [msg]
                    break
            
            if not relevant_history:
                return "No recent medical information available."
            
            # Return the last assistant response directly (no summarization needed)
            last_response = relevant_history[0]['content']
            # Extract first 300 chars for context (avoid overwhelming the prompt)
            if len(last_response) > 300:
                return f"Recent context: {last_response[:300]}..."
            return f"Recent context: {last_response}"
        
        else:
            # For independent queries: Use last 5 exchanges (10 messages)
            relevant_history = history[-10:]
        
        # Format history for summarization
        formatted_history = ""
        for msg in relevant_history:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            formatted_history += f"{role_label}: {msg['content']}\n\n"
        
        prompt = f"""
You are a MEDICAL CONVERSATION CONTEXT EXTRACTOR.

Your task: Extract ALL RELEVANT USER FACTS and the MOST RECENT medical topic.

CRITICAL RULES:
1. EXTRACT USER FACTS: Identify ANY information the user shared about themselves:
   - Pregnancy month/trimester/week (e.g., "5 months pregnant", "third trimester", "week 20")
   - Symptoms (e.g., "feeling dizzy", "nausea", "back pain")
   - Medical conditions (e.g., "diabetes", "high blood pressure")
   - Previous medical history
   - ANY other personal health information

2. EXTRACT RECENT TOPIC: What medical topic was recently discussed?

3. PRIORITIZE RECENCY: If the same fact appears multiple times, use the MOST RECENT version.

4. BE COMPLETE: Include ALL relevant facts, not just one.

5. NO SPECULATION: Use ONLY what the user explicitly stated.

Conversation History:
{formatted_history}

OUTPUT FORMAT:
**User Facts:**
- [List each fact the user shared about themselves]

**Recent Topic:**
- [The medical topic being discussed]

Example:
**User Facts:**
- User is 5 months pregnant
- Experiencing dizziness

**Recent Topic:**
- Managing dizziness during pregnancy

Context:
"""
        
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        return summary if summary else "No recent medical topic discussed."
        
    except Exception as e:
        print(f"Error in summarize_conversation_history: {e}")
        return ""



def get_last_assistant_language(history: list) -> str:
    """
    Extracts the language of the last assistant response for language stability.
    
    Args:
        history: Conversation history list
    
    Returns:
        str: Language code of last response, or None if not detectable
    """
    if not history:
        return None
    
    # Find last assistant message
    for msg in reversed(history):
        if msg['role'] == 'assistant':
            content = msg['content']
            # Simple heuristic: check if response contains non-ASCII (likely non-English)
            # Or check for language markers in markdown sources
            try:
                from Backend.models.translator import detect_language
                return detect_language(content[:100])  # Check first 100 chars
            except:
                return None
    
    return None


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
    
    # === CRITICAL: FOLLOW-UP DETECTION & CONTEXT SELECTION ===
    is_followup = is_followup_query(query)
    print(f"🔍 Is follow-up query: {is_followup}")
    
    # Summarize history with recency priority
    history_context_for_system = ""
    topic_anchoring_rule = ""
    
    if conversation_history and not is_greeting:
        summary = summarize_conversation_history(conversation_history, is_followup=is_followup)
        print(f"📝 Conversation context: {summary}")
        
        if summary:
            if is_followup:
                # For follow-ups: Strict anchoring to recent context
                history_context_for_system = f"\n\nRECENT CONTEXT (CRITICAL - THIS IS WHAT USER IS ASKING ABOUT):\n{summary}"
                topic_anchoring_rule = "\n\n🎯 FOLLOW-UP DETECTED: The user is asking about the RECENT CONTEXT above. Answer STRICTLY about that topic. DO NOT introduce new information unless directly relevant. DO NOT change topics. Expand on what was just discussed."
            else:
                # For independent queries: Use user facts + recent topic
                history_context_for_system = f"\n\nUSER CONTEXT (CRITICAL - USE THIS INFORMATION):\n{summary}"
                topic_anchoring_rule = "\n\n💡 IMPORTANT: The USER CONTEXT above contains facts the user shared earlier. USE these facts to answer the current question. DO NOT ask for information that's already provided in the context. If the user asks about something they already told you (like pregnancy month), answer using the context."
    
    # === LANGUAGE STABILITY RULE ===
    # Maintain language from last assistant response (unless explicit override)
    last_response_language = get_last_assistant_language(conversation_history)
    print(f"🌐 Last response language: {last_response_language}")
    print(f"🌐 Current target language: {target_language}")
    
    # Language lock: For follow-ups, use last response language unless explicitly overridden
    final_language = target_language
    if is_followup and last_response_language and target_language == "en":
        # If follow-up detected and current query is in English but last response was in another language,
        # maintain the previous language (user likely didn't switch languages intentionally)
        final_language = last_response_language
        print(f"🔒 Language locked to previous response: {final_language}")
    
    language_instruction = ""
    if final_language != "en":
        from Backend.models.translator import LANGUAGE_NAMES
        lang_name = LANGUAGE_NAMES.get(final_language, final_language)
        if is_followup:
            language_instruction = f"\n\nLANGUAGE LOCK: Continue responding in {lang_name} (same as previous response). DO NOT switch languages."
        else:
            language_instruction = f"\n\nLANGUAGE: Respond in {lang_name}."
    
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

    1. GREETINGS →
    If the user ONLY says hi/hello (no medical question),
    respond ONLY with:
    "Hello! I'm Dr. MAMA. How can I help you today?"
    Nothing else.

    2. CREATOR →
    If asked who created you, respond:
    "I was created by Ishan Patil."

    3. LANGUAGE SELECTION (STRICT):
    - If not specified explicitly then use English language always.
    - For follow-up questions → MAINTAIN the language of the previous response.
    - Supported languages are ONLY those provided in the allowed language list.
    - If the detected or requested language is NOT in the supported list,
        you MUST FALL BACK TO ENGLISH.
    - NEVER invent, guess, or auto-switch to any unsupported language.
    - COMPLETELY IGNORE language used in conversation history.

    4. FOLLOW-UP QUESTIONS →
    If the query is vague or referential
    (e.g. "tell me more", "explain", "continue", "third point", "last question"),
    you MUST expand ONLY on the MOST RECENT assistant medical response.

    5. CONTEXT RULE →
    - For follow-up queries → use ONLY the most recent medical information.
    - For non-follow-up queries → CHECK USER CONTEXT for user facts (pregnancy month, symptoms, conditions).
    - USE those facts to answer questions. DO NOT ask for information already in context.
    - Example: If context shows "User is 5 months pregnant" and user asks "which month am I in?" → Answer "You are 5 months pregnant."

    6. INDEPENDENT QUESTIONS →
    If the question is new or unrelated, answer it fresh.
    DO NOT mix previous topics unless explicitly asked.
    BUT ALWAYS check USER CONTEXT for relevant facts first.

    7. FOCUS →
    Answer ONLY what was asked.
    No extra summaries unless the user asks for them.

    8. RESTRICTED LANGUAGES →
    NEVER respond in Indonesian (Bahasa Indonesia 🇮🇩), even if requested.

    CONVERSATION HISTORY USAGE:
    - History is ONLY for topic continuity.
    - History MUST NOT influence language choice.
    - NEVER copy phrasing or language style from history.

    RESPONSE FORMAT (MEDICAL):
    - Prefer numbered points (1, 2, 3…) when helpful
    - Use bullet points and sections
    - Use markdown formatting
    - Use **bold** for key terms and *italics* for emphasis
    - Keep answers concise, precise, and medically relevant

    DO NOT:
    - Repeat greetings in medical answers
    - Mix unrelated topics
    - Change language unless explicitly requested AND supported
    - Ask for information that's already in USER CONTEXT

    {history_context_for_system}
    {topic_anchoring_rule}
    {language_instruction}
    {greeting_instruction}
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


# You are Dr. MAMA, a helpful AI assistant specializing in pregnancy and postpartum care.
# You were created by Ishan Patil to help expecting mothers and new parents.{history_context_for_system}{topic_anchoring_rule}

# === CRITICAL RULES ===

# 1. GREETINGS
#    - If user ONLY says hi/hello (no question) → "Hello! I'm Dr. MAMA. How can I help you today?"
#    - DO NOT repeat greetings in medical responses

# 2. CREATOR
#    - If asked who created you → "I was created by Ishan Patil."

# 3. LANGUAGE STABILITY
#    - For follow-up questions → MAINTAIN the language of the previous response
#    - For new questions → Use the language of the current query
#    - NEVER mix languages within a single response
#    - NEVER switch languages mid-conversation unless explicitly requested

# 4. FOLLOW-UP QUESTIONS ("tell me more", "explain", "continue", "third point")
#    - The RECENT CONTEXT above shows what we just discussed
#    - Answer STRICTLY about that context
#    - DO NOT introduce new topics
#    - DO NOT say "no context" - the context is RIGHT ABOVE
#    - Expand or clarify what was JUST discussed

# 5. INDEPENDENT QUESTIONS
#    - Provide fresh, focused answer
#    - Don't reference previous topics unless relevant

# 6. RESPONSE STRUCTURE (MEDICAL INFORMATION)
#    - Use NUMBERED LISTS (1, 2, 3...) for steps, precautions, foods, symptoms, etc.
#    - Use **bold** for important terms (e.g., **Iron deficiency**, **Third trimester**)
#    - Use *italics* for emphasis (e.g., *essential*, *recommended*)
#    - Keep answers CONCISE and PRECISE
#    - Avoid long paragraphs - break into points

# 7. FOCUS
#    - Answer ONLY what was asked
#    - No extra summaries unless requested
#    - No unnecessary elaboration

# 8. LANGUAGE RESTRICTIONS
#    - DO NOT respond in Indonesian (Bahasa Indonesia) 🇮🇩

# === EXAMPLE RESPONSE FORMAT ===

# Question: "What foods should I eat in the third trimester?"

# Response:
# **Third Trimester Nutrition:**

# 1. **Iron-rich foods**: Spinach, lentils, red meat
# 2. **Calcium sources**: Milk, yogurt, cheese
# 3. **Protein**: Eggs, fish, chicken
# 4. **Fiber**: Whole grains, fruits, vegetables
# 5. **Omega-3**: Salmon, walnuts, chia seeds

# *Consult your doctor for personalized dietary advice.*{language_instruction}{greeting_instruction}