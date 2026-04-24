import os
import random
from typing import Tuple
from groq import Groq
from loguru import logger
import yaml
import requests
from dotenv import load_dotenv
from ai.spam_checker import clean_spam_words

load_dotenv()

# Load Config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    LLM_PROVIDER = config.get("llm_provider", "groq")
    GROQ_MODEL = config.get("groq_model", "llama3-8b-8192")
    OLLAMA_MODEL = config.get("ollama_model", "llama3")
    MAX_SENTENCES = config.get("email_max_sentences", 4)

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not found in environment!")
        return None
    try:
         return Groq(api_key=api_key.strip())
    except Exception as e:
         logger.warning(f"Groq Client init error: {e}")
         return None

# Prompt Angles
PROMPT_ANGLES = [
    {
        "name": "SEO Pitch",
        "instructions": "Focus on their missing SEO tags (like Title, Description, H1) and how it makes them invisible on Google searches compared to competitors."
    },
    {
        "name": "Mobile UX Pitch",
        "instructions": "Focus on the lack of a mobile viewport or responsive framework. Explain how frustrated mobile users are bouncing off their site."
    },
    {
        "name": "Trust & Conversion Pitch",
        "instructions": "Focus on the missing SSL (HTTPS), missing contact forms, and low review counts. Explain how this destroys trust and costs them leads."
    },
    {
        "name": "Competitor Analysis Pitch",
        "instructions": "Take a slightly analytical approach. 'I was analyzing businesses in your area and noticed your site is missing X and Y, which your top competitors are getting right.'"
    }
]

INTRO_STYLES = [
    "Hi {name},",
    "Hello {name},",
    "Hey {name},"
]

def generate_cold_email(business_name: str, weaknesses_summary: str, persona=None, provided_first_name=None) -> Tuple[str, str]:
    """Generates an email using Groq with Ollama fallback, utilizing prompt rotation and Persona context."""
    
    if provided_first_name:
         first_name = provided_first_name
    else:
         first_name = business_name.split()[0].replace(",", "").replace(".", "") if business_name else "there"
    
    if persona and persona.objective == "job_hunt":
        angle_name = "Career Alignment Pitch"
        strategy_context = f"Analyze these website findings to find an angle where someone offering '{persona.skills}' in a job setting would be valuable. The user is a job or internship seeker."
        copywriter_rule = f"Pitch yourself for a job/internship. Mention your skills: {persona.skills}. Context from your resume: {persona.resume_text}."
        cta = "Would you be open to a quick chat about potentially joining your team?"
    elif persona and persona.objective == "freelance":
        angle_name = "Freelance Expert Pitch"
        strategy_context = f"Analyze these findings to pitch freelance services for: {persona.skills}."
        copywriter_rule = f"Pitch your freelance services based on these skills: {persona.skills}. Your value proposition: {persona.value_proposition}."
        cta = "Are you open to having a quick chat to see if I can help out as a freelancer?"
    else:
        angle_name = random.choice(PROMPT_ANGLES)["name"]
        angle_obj = next((a for a in PROMPT_ANGLES if a['name'] == angle_name), PROMPT_ANGLES[0])
        strategy_context = f"Pitch Angle to use: {angle_obj['instructions']}"
        val_prop = persona.value_proposition if persona else "We fix website weaknesses to capture more leads."
        copywriter_rule = f"Pitch them B2B services. Your value prop is: {val_prop}"
        cta = "Would it be worth a quick 10-minute chat?"

    system_prompt = f"""You are a professional copywriter sending a cold email to {first_name}.
Your goal is to get a reply. Keep it extremely short (max {MAX_SENTENCES} sentences).
Use a conversational, peer-to-peer tone. 

CRITICAL RULES:
1. The VERY FIRST LINE of your response must be exactly "Subject: [Your Subject Here]". Do not place a greeting before the subject line!
2. The second line should be the body greeting setting, specifically addressing {first_name}.
3. End exactly with this soft CTA: "{cta}"
4. {copywriter_rule}
5. {strategy_context}

Write the email using these EXACT findings about their website/business:
{weaknesses_summary}
"""

    user_prompt = f"Write the email to {first_name}."

    if not weaknesses_summary or "surprisingly healthy" in weaknesses_summary.lower():
         return "", "No significant weaknesses found to construct pitch."

    draft = ""
    # Try Groq First
    if LLM_PROVIDER == "groq":
        groq_client = get_groq_client()
        if groq_client:
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                draft = completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq generation failed: {e}. Falling back to Ollama...")
                draft = attempt_ollama_fallback(system_prompt, user_prompt)
        else:
            logger.error("Groq client could not be initialized. Falling back to Ollama...")
            draft = attempt_ollama_fallback(system_prompt, user_prompt)
    else:
        draft = attempt_ollama_fallback(system_prompt, user_prompt)

    if not draft:
        return "", "Failed to generate email."

    # We don't prepend our own intro anymore because it messes up the strictly placed Subject line requirement.
    # The LLM prompt is now stricter.

    draft = clean_spam_words(draft)
    return draft.strip(), angle_name


def attempt_ollama_fallback(system_prompt: str, user_prompt: str) -> str:
    """Local fallback using Ollama API if Groq fails."""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    endpoint = f"{ollama_url}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False
    }
    
    try:
        resp = requests.post(endpoint, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        logger.error(f"Ollama fallback also failed: {e}")
        
    return ""

def generate_followup_email(business_name: str, step_number: int, previous_draft: str = "") -> str:
    """Generates shorter follow-up sequences using the LLM."""
    
    first_name = business_name.split()[0].replace(",", "").replace(".", "") if business_name else "there"
    
    if step_number == 2:
        context = "You sent an email 3 days ago praising/critiquing their website but haven't heard back."
        instructions = "Write a quick 2-sentence 'bump' email pushing the previous email to the top of their inbox. End with 'Is this something you are still open to talking about?'"
    else:
        context = "You sent two emails over the last 7 days and they ignored both."
        instructions = "Write a professional 2-sentence 'breakup' email. Tell them you assume they are too busy right now and will cross them off your list. Wish them the best."

    system_prompt = f"""You are a professional web agency owner sending a cold email follow up.
Your goal is to get a reply. Keep it extremely short (max 3 sentences).
Context: {context}

CRITICAL RULES:
1. The VERY FIRST LINE must be exactly "Subject: [Your Subject Here]". 
2. The second line should be the body greeting.
3. Instructions: {instructions}
"""

    user_prompt = f"Write the follow-up email to {first_name}."
    
    draft = ""
    if LLM_PROVIDER == "groq":
        groq_client = get_groq_client()
        if groq_client:
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                draft = completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq generation failed: {e}.")
                draft = attempt_ollama_fallback(system_prompt, user_prompt)
        else:
            draft = attempt_ollama_fallback(system_prompt, user_prompt)
    else:
        draft = attempt_ollama_fallback(system_prompt, user_prompt)

    if not draft:
        return ""
        
    draft = clean_spam_words(draft)
    return draft.strip()
