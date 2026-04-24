import urllib.parse
from curl_cffi import requests
from loguru import logger

def find_decision_maker_email(domain: str, objective: str, api_key: str):
    """
    Hooks into Hunter.io to find specific roles based on the Persona's objective.
    Returns: dict {"email": str, "first_name": str, "position": str} or None
    """
    if not api_key or not domain:
        return None
        
    # Clean domain
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    
    url = f"https://api.hunter.io/v2/domain-search?domain={urllib.parse.quote(domain)}&api_key={api_key}"
    
    try:
        response = requests.get(url, impersonate="chrome120")
        if response.status_code != 200:
            logger.warning(f"Hunter API returned {response.status_code} for {domain}")
            return None
            
        data = response.json().get("data", {})
        emails = data.get("emails", [])
        
        if not emails:
            return None
            
        # Define what we are hunting
        if objective == "job_hunt":
            high_priority_keywords = ["HR", "Human Resources", "Recruiter", "Talent", "Acquisition", "Founder", "CEO"]
        elif objective == "freelance" or objective == "b2b_agency":
            high_priority_keywords = ["CEO", "Founder", "Owner", "Marketing", "CMO", "Director"]
        else:
            high_priority_keywords = ["CEO", "Founder", "Owner", "Director"]
            
        best_match = None
        best_score = -1
        
        for e in emails:
            pos = str(e.get("position") or "").lower()
            score = 0
            
            # Simple keyword matching
            for kw in high_priority_keywords:
                if kw.lower() in pos:
                    score += 10
                    break
                    
            # Bonus if they have a first name (critical for AI personalization)
            if e.get("first_name"):
                score += 5
                
            # Bonus if verified
            if e.get("confidence", 0) > 90:
                score += 2
                
            if score > best_score:
                best_score = score
                best_match = {
                    "email": e.get("value"),
                    "first_name": e.get("first_name", ""),
                    "position": e.get("position", "")
                }
                
        # If we didn't find a high priority match, but we have emails, we could just return the best one
        # Let's demand at least a generic score > 0 (meaning it has a first name or is highly verified)
        # Or just return the top generic one if we're desperate.
        if best_match and (best_score >= 5 or len(emails) == 1):
            return best_match
            
        if emails and best_match:
             return best_match
             
        return None
        
    except Exception as e:
        logger.error(f"Error enriching {domain} via Hunter.io: {e}")
        return None
