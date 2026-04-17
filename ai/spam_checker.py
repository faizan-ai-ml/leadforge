import re
from loguru import logger

SPAM_TRIGGER_WORDS = [
    "free", "guaranteed", "no risk", "click here", "earn money",
    "limited time", "act now", "winner", "congratulations",
    "buy now", "cash bonus", "double your", "earn extra",
    "eliminate debt", "exclusive deal", "risk free", "100% free"
]

def clean_spam_words(email_text: str) -> str:
    """Removes or flags common spam trigger words to improve deliverability."""
    if not email_text:
        return email_text
        
    cleaned_text = email_text
    found_spam = False
    
    for word in SPAM_TRIGGER_WORDS:
        # Case insensitive regex replacement
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        if pattern.search(cleaned_text):
            found_spam = True
            # Instead of deleting completely, we replace with an empty string, 
            # though sometimes it breaks English flow. 
            # Better strategy: We just log it so the LLM prompt instructions can do the heavy lifting,
            # but we explicitly remove "risk free" or "100% free" entirely.
            # Here we just blindly remove them to adhere strictly to the requirement.
            cleaned_text = pattern.sub('', cleaned_text)
            
    # Clean up double spaces if any words were removed
    cleaned_text = re.sub(' +', ' ', cleaned_text)
    
    if found_spam:
        logger.debug("Spam words were detected and removed from the generated email.")
        
    return cleaned_text
