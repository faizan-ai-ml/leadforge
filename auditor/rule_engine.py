import re
from bs4 import BeautifulSoup
from loguru import logger

def audit_html(html_content: str, url: str) -> dict:
    """Runs a barrage of rule-based logical checks on business HTML."""
    findings = {
        "seo": {
            "has_title": False,
            "has_meta_desc": False,
            "has_h1": False,
            "multiple_h1": False,
            "images_missing_alt_count": 0,
            "has_canonical": False,
            "has_og_tags": False,
            "heavy_page": False
        },
        "ux": {
            "has_viewport": False,
            "has_responsive_framework": False,
            "has_cta": False
        },
        "trust": {
            "has_ssl": url.startswith("https://"),
            "has_contact_form": False,
            "has_phone_pattern": False,
            "has_tracking_pixel": False
        },
        "tech": {
            "stack": "Custom/Unknown"
        },
        "contact": {
            "emails": []
        }
    }

    if not html_content:
        return findings

    try:
        # Check page size (> 3MB roughly 3,000,000 characters in uncompressed HTML)
        if len(html_content) > 3_000_000:
            findings["seo"]["heavy_page"] = True

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # --- SEO CHECKS ---
        title = soup.find('title')
        if title and title.text.strip():
            findings["seo"]["has_title"] = True
            
        meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
        if meta_desc and meta_desc.get('content', '').strip():
            findings["seo"]["has_meta_desc"] = True
            
        h1s = soup.find_all('h1')
        if len(h1s) == 1:
            findings["seo"]["has_h1"] = True
        elif len(h1s) > 1:
            findings["seo"]["has_h1"] = True
            findings["seo"]["multiple_h1"] = True
            
        images = soup.find_all('img')
        missing_alt = sum(1 for img in images if not img.get('alt') or not str(img.get('alt')).strip())
        findings["seo"]["images_missing_alt_count"] = missing_alt
        
        if soup.find('link', rel='canonical'):
            findings["seo"]["has_canonical"] = True
            
        if soup.find('meta', property=re.compile(r'^og:title$', re.I)):
            findings["seo"]["has_og_tags"] = True

        # --- UX CHECKS ---
        viewport = soup.find('meta', attrs={'name': re.compile(r'^viewport$', re.I)})
        if viewport:
            findings["ux"]["has_viewport"] = True
            
        html_lower = html_content.lower()
        if 'bootstrap' in html_lower or 'tailwind' in html_lower:
             findings["ux"]["has_responsive_framework"] = True
             
        cta_keywords = ["contact", "call", "quote", "book", "schedule", "appointment", "free trial"]
        buttons_links = soup.find_all(['a', 'button'])
        for el in buttons_links:
            text = el.get_text().strip().lower()
            if any(k in text for k in cta_keywords):
                findings["ux"]["has_cta"] = True
                break

        # --- TRUST CHECKS ---
        if soup.find('form'):
            findings["trust"]["has_contact_form"] = True
            
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        if re.search(phone_pattern, html_content):
            findings["trust"]["has_phone_pattern"] = True
            
        if 'gtag' in html_lower or 'fbq' in html_lower or 'google-analytics' in html_lower or 'analytics' in html_lower:
             findings["trust"]["has_tracking_pixel"] = True

        # --- CONTACT EXTRACTION ---
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, html_content)
        # Filter duplicates and ignore massive lists (filter generic image filetypes or assets that might accidentally match regex)
        valid_emails = list(set([e.lower() for e in found_emails if not any(e.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])]))
        findings["contact"]["emails"] = valid_emails

        # --- TECH STACK ---
        if 'wp-content' in html_lower:
            findings["tech"]["stack"] = "WordPress"
        elif 'cdn.shopify' in html_lower or 'shopify' in html_lower:
            findings["tech"]["stack"] = "Shopify"
        elif 'static.wixstatic' in html_lower or 'wix.com' in html_lower:
             findings["tech"]["stack"] = "Wix"
        elif 'squarespace.com' in html_lower:
             findings["tech"]["stack"] = "Squarespace"
             
    except Exception as e:
        logger.error(f"Error parsing HTML during audit for url {url}: {e}")
        
    return findings
