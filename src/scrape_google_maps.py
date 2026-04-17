"""
╔══════════════════════════════════════════════════╗
║       Google Maps Lead Scraper (Fast Scrape)     ║
║  Built with Python + Playwright  (100% Free)     ║
╚══════════════════════════════════════════════════╝

SETUP (run these once):
  pip install playwright python-dotenv
  playwright install chromium

USAGE:
  python scrape_google_maps.py
"""

import asyncio
import csv
import re
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright
import database

# ─────────────────────────────────────────────────────────
#  CONFIG  — edit these defaults if you want
# ─────────────────────────────────────────────────────────
DEFAULT_HEADLESS   = False   # True = run silently, False = watch the browser
SCROLL_PAUSE_MS    = 2500    # how long to wait after each scroll (ms)
PAGE_LOAD_WAIT_MS  = 2000    # how long to wait when opening a listing (ms)
WEBSITE_TIMEOUT_MS = 8000    # max time to load a business website for email
MAX_SCROLL_ROUNDS  = 15      # how many times to scroll the results panel

# Selectors (update if Google changes their HTML)
SEL_NAME     = "h1.DUwDvf, h1[class*='fontHeadlineLarge']"
SEL_ADDRESS  = "[data-item-id='address']"
SEL_PHONE    = "[data-item-id^='phone:tel:']"
SEL_WEBSITE  = "a[data-item-id='authority']"
SEL_RATING   = "div.F7nice span[aria-hidden='true']"
SEL_CATEGORY = "button.DkEaL"
SEL_REVIEWS  = "div.F7nice span[aria-label*='reviews']"

# ─────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────
def clean(text: str) -> str:
    """Strip leading/trailing whitespace and common prefixes."""
    if not text:
        return ""
    text = text.strip()
    for prefix in ["Address: ", "Phone: ", "Website: "]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text


def extract_emails_from_html(html: str) -> list:
    """Find email addresses in raw HTML using regex."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, html)
    # Filter out common false positives (image filenames, etc.)
    blocked = {"example.com", "domain.com", "email.com", "youremail.com",
               "sentry.io", "wixpress.com", "squarespace.com"}
    cleaned = [e.lower() for e in emails
               if not any(e.lower().endswith(b) for b in blocked)]
    return list(dict.fromkeys(cleaned))  # deduplicate, keep order


def print_progress(current: int, total: int, name: str):
    bar_len = 20
    filled = int(bar_len * current / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r  [{bar}] {current}/{total}  {name[:35]:<35}", end="", flush=True)


# ─────────────────────────────────────────────────────────
#  CORE SCRAPER
# ─────────────────────────────────────────────────────────
async def get_business_links(page, max_leads: int) -> list:
    """Scroll the Google Maps results panel and collect listing URLs."""
    print("  Scrolling results to find listings...")
    seen = set()
    links = []

    # The scrollable results container
    container = page.locator('div[role="feed"]')

    for _ in range(MAX_SCROLL_ROUNDS):
        # Grab all place links currently visible
        anchors = await page.locator('a[href*="/maps/place/"]').all()
        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if href and href not in seen:
                seen.add(href)
                links.append(href)

        if len(links) >= max_leads:
            break

        # Scroll down inside the panel
        try:
            await container.evaluate("el => el.scrollBy(0, 800)")
        except Exception:
            await page.keyboard.press("End")

        await page.wait_for_timeout(SCROLL_PAUSE_MS)

        # Check if "You've reached the end of the list" appeared
        end_text = page.get_by_text("You've reached the end of the list")
        if await end_text.count() > 0:
            break

    print(f"\n  Found {len(links[:max_leads])} listing links.")
    return links[:max_leads]


async def scrape_listing(page, url: str, scrape_email: bool, browser, business_type: str) -> dict:
    """Open one Google Maps listing and pull all available data."""
    lead = {
        "name": "", "category": "", "rating": "", "reviews": "",
        "address": "", "phone": "", "website": "", "email": "",
        "facebook": "", "instagram": "", "linkedin": "", "twitter": "",
        "youtube": "", "tiktok": "", "tech_stack": "", "has_contact_form": "No", "raw_website_text": ""
    }

    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

        # Name
        el = page.locator(SEL_NAME)
        if await el.count() > 0:
            lead["name"] = clean(await el.first.inner_text())

        # Category
        el = page.locator(SEL_CATEGORY)
        if await el.count() > 0:
            lead["category"] = clean(await el.first.inner_text())

        # Rating
        el = page.locator(SEL_RATING)
        if await el.count() > 0:
            lead["rating"] = clean(await el.first.inner_text())

        # Reviews count
        el = page.locator(SEL_REVIEWS)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            lead["reviews"] = label.split(" ")[0]

        # Address
        el = page.locator(SEL_ADDRESS)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            lead["address"] = clean(label)

        # Phone
        el = page.locator(SEL_PHONE)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            lead["phone"] = clean(label)

        # Website
        el = page.locator(SEL_WEBSITE)
        if await el.count() > 0:
            lead["website"] = await el.first.get_attribute("href") or ""

        # Email & Website Reading — visit website if we have one
        if scrape_email and lead["website"]:
            email, website_text, socials = await scrape_website_data(lead["website"], browser)
            lead["email"] = email
            lead.update(socials)
            if website_text:
                lead["raw_website_text"] = website_text

    except Exception as e:
        print(f"\n  ⚠  Error scraping listing: {e}")

    return lead


async def extract_social_links(tab) -> dict:
    """Evaluate DOM to find social media hrefs."""
    social_urls = {
        "facebook": "", "instagram": "", "linkedin": "",
        "twitter": "", "youtube": "", "tiktok": ""
    }
    
    try:
        hrefs = await tab.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h);
        }''')
        
        for href in hrefs:
            href_lower = href.lower()
            if 'facebook.com' in href_lower and not social_urls["facebook"]:
                if 'sharer' not in href_lower:
                    social_urls["facebook"] = href
            elif 'instagram.com' in href_lower and not social_urls["instagram"]:
                social_urls["instagram"] = href
            elif 'linkedin.com' in href_lower and not social_urls["linkedin"]:
                social_urls["linkedin"] = href
            elif ('twitter.com' in href_lower or 'x.com/' in href_lower) and not social_urls["twitter"]:
                if 'share' not in href_lower:
                    social_urls["twitter"] = href
            elif 'youtube.com' in href_lower and not social_urls["youtube"]:
                social_urls["youtube"] = href
            elif 'tiktok.com' in href_lower and not social_urls["tiktok"]:
                social_urls["tiktok"] = href
    except Exception:
        pass
        
    return social_urls


async def scrape_website_data(url: str, browser) -> tuple[str, str, dict]:
    """Open the business website and scan for email addresses and social links."""
    contact_pages = ["", "/contact", "/contact-us", "/about", "/about-us"]
    found_email = ""
    website_text = ""
    found_socials = {
        "facebook": "", "instagram": "", "linkedin": "",
        "twitter": "", "youtube": "", "tiktok": ""
    }
    found_tech = []
    has_contact_form = "No"

    try:
        tab = await browser.new_page()
        await tab.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })

        for path in contact_pages:
            try:
                target = url.rstrip("/") + path
                await tab.goto(target, timeout=WEBSITE_TIMEOUT_MS,
                               wait_until="domcontentloaded")
                html = await tab.content()
                
                # Tech Stack Check
                html_lower = html.lower()
                if 'wp-content' in html_lower or 'wordpress' in html_lower:
                    if 'WordPress' not in found_tech: found_tech.append('WordPress')
                if 'cdn.shopify.com' in html_lower or 'shopify' in html_lower:
                    if 'Shopify' not in found_tech: found_tech.append('Shopify')
                if 'wix.com' in html_lower:
                    if 'Wix' not in found_tech: found_tech.append('Wix')
                if 'squarespace.com' in html_lower:
                    if 'Squarespace' not in found_tech: found_tech.append('Squarespace')
                    
                # Contact Form Check
                if has_contact_form == "No":
                    try:
                        if await tab.locator("form").count() > 0:
                            has_contact_form = "Yes"
                    except Exception:
                        pass
                
                # Grab body innerText if we need more reading material for AI
                if len(website_text) < 1500:
                    try:
                        inner_text = await tab.locator('body').inner_text(timeout=2000)
                        website_text += " " + inner_text[:5000] # Safe limit per page
                    except:
                        pass
                
                emails = extract_emails_from_html(html)
                if emails and not found_email:
                    found_email = emails[0]
                    
                socials = await extract_social_links(tab)
                for platform, link in socials.items():
                    if link and not found_socials[platform]:
                        found_socials[platform] = link

                if len(website_text) > 1500 and found_email:
                    break
                        
            except Exception:
                continue

        await tab.close()
    except Exception:
        pass

    found_socials["tech_stack"] = ", ".join(found_tech)
    found_socials["has_contact_form"] = has_contact_form

    return found_email, website_text, found_socials


# ─────────────────────────────────────────────────────────
#  CSV EXPORT
# ─────────────────────────────────────────────────────────
def save_to_csv(leads: list, filename: str):
    if not leads:
        print("\n  No leads collected — nothing to save.")
        return

    fieldnames = ["name", "category", "rating", "reviews",
                  "address", "phone", "website", "email",
                  "facebook", "instagram", "linkedin", "twitter",
                  "youtube", "tiktok", "tech_stack", "has_contact_form", "raw_website_text"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)

    print(f"\n\n  ✅  Saved {len(leads)} leads → {filename}")


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────
async def run():
    print("\n" + "═" * 52)
    print("   Google Maps Lead Scraper  (Fast Data Dump)")
    print("═" * 52)
    
    database.init_db()

    # ── User input ─────────────────────────────────────
    business_type = input("\n  Business type  (e.g. restaurant, web agency): ").strip()
    location      = input("  Location       (e.g. Karachi, Lahore, Dubai):   ").strip()
    max_str       = input("  Max leads      (default 30):                     ").strip()
    email_str     = input("  Scrape emails + AI? (y/n, default y):            ").strip().lower()

    max_leads    = int(max_str) if max_str.isdigit() else 30
    scrape_email = (email_str != "n")

    if not business_type or not location:
        print("  ✗ Business type and location are required.")
        return

    query    = f"{business_type} in {location}"
    maps_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("output", exist_ok=True)
    out_file = os.path.join("output", f"leads_{business_type.replace(' ','_')}_{location.replace(' ','_')}_{stamp}.csv")

    print(f"\n  Searching: {query}")
    print(f"  Target leads: {max_leads}  |  AI + Email scraping: {'on' if scrape_email else 'off'}\n")

    # ── Launch browser ─────────────────────────────────
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=DEFAULT_HEADLESS)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # Navigate to Google Maps search
        print("  Opening Google Maps...")
        await page.goto(maps_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Dismiss cookie consent if it appears
        try:
            accept_btn = page.get_by_role("button", name=re.compile(r"Accept|Agree", re.I))
            if await accept_btn.count() > 0:
                await accept_btn.first.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Collect listing URLs
        links = await get_business_links(page, max_leads)

        if not links:
            print("  ✗ No listings found. Try a different query or location.")
            await browser.close()
            return

        # Scrape each listing
        leads = []
        print(f"\n  Scraping {len(links)} listings... this will be much faster now.\n")

        for i, link in enumerate(links, 1):
            lead = await scrape_listing(page, link, scrape_email, browser, business_type)
            if lead["name"]:
                leads.append(lead)
                database.insert_lead("Google Maps", query, lead)
                email_icon = "✉" if lead["email"] else " "
                status = f"{email_icon} {lead['name'][:40]}"
                print_progress(i, len(links), status)
            await page.wait_for_timeout(800)

        await browser.close()

    # ── Save results ────────────────────────────────────
    save_to_csv(leads, out_file)

    # ── Summary ─────────────────────────────────────────
    with_phone   = sum(1 for l in leads if l["phone"])
    with_website = sum(1 for l in leads if l["website"])
    with_email   = sum(1 for l in leads if l["email"])

    print("\n" + "─" * 40)
    print(f"  Total leads    : {len(leads)}")
    print(f"  With phone     : {with_phone}")
    print(f"  With website   : {with_website}")
    print(f"  With email     : {with_email}")
    print(f"  Output file    : {out_file}")
    print("─" * 40 + "\n")
    print("\n  👉 Data saved to database! Now run `python enrich_leads.py` to use AI to write personalized emails.")


if __name__ == "__main__":
    asyncio.run(run())
