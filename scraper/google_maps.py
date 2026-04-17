import asyncio
import re
import random
from typing import List, Dict
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth
from playwright_stealth import Stealth
from scraper.user_agents import get_random_user_agent
from scraper.proxy_manager import ProxyManager
import yaml

SCROLL_PAUSE_MS = 2500
PAGE_LOAD_WAIT_MS = 2000
MAX_SCROLL_ROUNDS = 20

# CSS Selectors for Google Maps
SEL_NAME     = "h1.DUwDvf, h1[class*='fontHeadlineLarge']"
SEL_ADDRESS  = "[data-item-id='address']"
SEL_PHONE    = "[data-item-id^='phone:tel:']"
SEL_WEBSITE  = "a[data-item-id='authority']"
SEL_RATING   = "div.F7nice span[aria-hidden='true']"
SEL_REVIEWS  = "div.F7nice span[aria-label*='reviews']"

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    for prefix in ["Address: ", "Phone: ", "Website: "]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text

async def get_business_links(page: Page, max_leads: int) -> List[str]:
    logger.info("Scrolling results to discover listings...")
    seen = set()
    links = []
    
    container = page.locator('div[role="feed"]')
    
    for _ in range(MAX_SCROLL_ROUNDS):
        # Broadened the locator to catch Google's newer class structures
        anchors = await page.locator('a[href*="/maps/place/"], a.hfpxzc').all()
        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if href and href not in seen:
                seen.add(href)
                links.append(href)
                
        if len(links) >= max_leads:
            break
            
        try:
            if await container.count() > 0:
                await container.evaluate("el => el.scrollBy(0, 800)")
            else:
                await page.keyboard.press("PageDown")
        except:
            await page.keyboard.press("End")
            
        await page.wait_for_timeout(SCROLL_PAUSE_MS)
        
        if await page.get_by_text("You've reached the end of the list").count() > 0:
            break
            
    logger.info(f"Found {len(links[:max_leads])} listing URLs.")
    return links[:max_leads]

async def scrape_listing(page: Page, url: str) -> Dict:
    lead = {
        "business_name": "", "address": "", "phone": "", 
        "website": "", "rating": "", "review_count": 0
    }
    
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(PAGE_LOAD_WAIT_MS)
        
        el = page.locator(SEL_NAME)
        if await el.count() > 0:
            lead["business_name"] = clean_text(await el.first.inner_text())
            
        el = page.locator(SEL_RATING)
        if await el.count() > 0:
            lead["rating"] = clean_text(await el.first.inner_text())
            
        el = page.locator(SEL_REVIEWS)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            count_str = label.split(" ")[0].replace(",", "")
            if count_str.isdigit():
                lead["review_count"] = int(count_str)
                
        el = page.locator(SEL_ADDRESS)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            lead["address"] = clean_text(label)
            
        el = page.locator(SEL_PHONE)
        if await el.count() > 0:
            label = await el.first.get_attribute("aria-label") or ""
            lead["phone"] = clean_text(label)
            
        el = page.locator(SEL_WEBSITE)
        if await el.count() > 0:
            lead["website"] = await el.first.get_attribute("href") or ""
            
    except Exception as e:
        logger.warning(f"Error scraping a listing URL: {e}")
        
    return lead

async def extract_google_maps_leads(niche: str, location: str, max_leads: int) -> List[Dict]:
    """Orchestrates Playwright to scrape basic Google Maps details."""
    leads = []
    query = f"{niche} in {location}"
    maps_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    
    logger.info(f"Navigating to Google Maps for query: {query}")
    
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    proxy_manager = ProxyManager(config)

    async with async_playwright() as p:
        # Running headful (headless=False) drastically reduces Google Maps bot detection and timeouts!
        args = ["--disable-blink-features=AutomationControlled"]
        browser = await p.chromium.launch(headless=False, args=args)
        
        pw_proxy = proxy_manager.get_playwright_proxy(domain="google.com")
        
        context_kwargs = {
            "user_agent": get_random_user_agent(),
            "viewport": {"width": random.randint(1280, 1920), "height": random.randint(800, 1080)}
        }
        if pw_proxy:
            context_kwargs["proxy"] = pw_proxy
            logger.debug("Routing Google Maps through Playwright Context Proxy...")
            
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        
        # Extra Playwright Evasion
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Apply strict anti-bot masking to bypass reCAPTCHA / Headless tracking
        await Stealth().apply_stealth_async(page)
        
        try:
            await page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"Google Maps page load timed out or took too long, proceeding with available DOM... Error: {e}")
        await page.wait_for_timeout(3000)
        
        # Accept cookies if applicable
        try:
            accept_btn = page.get_by_role("button", name=re.compile(r"Accept|Agree", re.I))
            if await accept_btn.count() > 0:
                await accept_btn.first.click()
                await page.wait_for_timeout(1000)
        except:
            pass
            
        links = await get_business_links(page, max_leads)
        
        for i, link in enumerate(links, 1):
            logger.info(f"[{i}/{len(links)}] Scraping listing basic info...")
            
            # Anti-Bot: Move mouse randomly exactly like a real user
            x, y = random.randint(100, 500), random.randint(100, 500)
            await page.mouse.move(x, y)
            
            lead = await scrape_listing(page, link)
            if lead["business_name"]:
                leads.append(lead)
            await page.wait_for_timeout(800)
            
        await browser.close()
        
    return leads
