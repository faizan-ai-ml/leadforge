from curl_cffi import requests
import urllib.robotparser
import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from loguru import logger
import re
import yaml
import os
from scraper.user_agents import get_random_user_agent
from scraper.proxy_manager import ProxyManager

# Load politely settings
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    delay_min = config.get("delay_between_requests_min", 3)
    delay_max = config.get("delay_between_requests_max", 8)

def can_fetch(url: str, user_agent: str) -> bool:
    """Check robots.txt if we are allowed to scrape this URL."""
    try:
        parsed_uri = urlparse(url)
        robots_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # If no robots.txt or fails to read, we cautiously assume yes for public small biz
        return True

def extract_emails_from_html(html: str) -> str:
    """Regex to find an email address."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, html)
    blocked = {"example.com", "domain.com", "sentry.io", "wixpress.com", "squarespace.com"}
    cleaned = [e.lower() for e in emails if not any(e.lower().endswith(b) for b in blocked)]
    return cleaned[0] if cleaned else ""

def scrape_website_html(url: str) -> dict:
    """Polite requests-based scraper with retries and delays."""
    user_agent = get_random_user_agent()
    
    if not url.startswith('http'):
        url = 'https://' + url

    # Politeness
    if not can_fetch(url, user_agent):
        logger.warning(f"robots.txt disallowed scraping for {url}. Proceeding anyway as fallback, but logged.")
        
    delay = random.uniform(delay_min, delay_max)
    logger.debug(f"Sleeping for {delay:.2f}s before hitting {url}")
    time.sleep(delay)

    headers = {'User-Agent': user_agent, 'Accept': 'text/html'}
    
    result = {
        "html": "",
        "status_code": 0,
        "email": "",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "blocked": False
    }

    max_retries = 3
    
    proxy_manager = ProxyManager(config)
    proxies = proxy_manager.get_requests_proxy(domain=url)
    if proxies:
        logger.debug(f"Routing through Proxy from ProxyManager...")

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=10, proxies=proxies, impersonate="chrome110")
            result["status_code"] = resp.status_code
            if resp.status_code == 200:
                result["html"] = resp.text
                result["email"] = extract_emails_from_html(resp.text)
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # If no email on homepage, hunt down the Contact page
                if not result["email"]:
                    from urllib.parse import urljoin
                    contact_url = None
                    for a in soup.find_all('a', href=True):
                        # Look for common contact paths
                        if 'contact' in a['href'].lower() or 'about' in a['href'].lower():
                            contact_url = urljoin(url, a['href'])
                            break
                    
                    if contact_url:
                        try:
                            logger.debug(f"Email missing on homepage, deep-scraping contact page: {contact_url}")
                            c_resp = requests.get(contact_url, headers=headers, timeout=8, proxies=proxies, impersonate="chrome110")
                            if c_resp.status_code == 200:
                                result["email"] = extract_emails_from_html(c_resp.text)
                        except Exception as ce:
                            logger.debug(f"Contact page deep-scrape failed: {ce}")

                # Basic Social check
                for a in soup.find_all('a', href=True):
                    href = a['href'].lower()
                    if 'facebook.com' in href and not result["facebook"] and 'sharer' not in href:
                        result["facebook"] = a['href']
                    elif 'instagram.com' in href and not result["instagram"]:
                        result["instagram"] = a['href']
                    elif 'linkedin.com' in href and not result["linkedin"]:
                        result["linkedin"] = a['href']
                return result
            elif resp.status_code in [403, 401, 429]:
                logger.warning(f"Blocked by {url} (status {resp.status_code}). WAF detected.")
                result["blocked"] = True
                return result
        except Exception as e:
            logger.debug(f"Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
            
    logger.error(f"Failed to fetch {url} after {max_retries} attempts.")
    return result
