import os
import re
from loguru import logger
from playwright.async_api import async_playwright
import yaml
from scraper.user_agents import get_random_user_agent

# Load screenshot config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    screenshots_enabled = config.get("screenshot_enabled", True)
    screenshot_dir = config.get("screenshot_folder", "screenshots/")

os.makedirs(screenshot_dir, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Removes invalid characters for filenames"""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.replace(" ", "_")[:50]

async def capture_screenshot(url: str, business_name: str) -> str:
    """Uses Playwright to capture a mobile screenshot of the site."""
    if not screenshots_enabled or not url:
        return ""
        
    if not url.startswith('http'):
        url = 'https://' + url
        
    filename = sanitize_filename(business_name) + ".png"
    filepath = os.path.join(screenshot_dir, filename)
    
    if os.path.exists(filepath):
        return filepath # Already captured
        
    logger.debug(f"Capturing mobile screenshot for {business_name} at {url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Emulate iPhone 13 Mini viewport
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 375, "height": 812},
                is_mobile=True,
                device_scale_factor=2
            )
            page = await context.new_page()
            
            # Navigate quickly, ignore heavy loaded scripts if possible
            await page.goto(url, wait_until="load", timeout=15000)
            
            # Dismiss typical cookie banners blindly if they obstruct
            await page.evaluate('''() => {
                const elements = document.querySelectorAll('button, a, div');
                for (let el of elements) {
                    if (el.innerText && el.innerText.match(/(accept|agree|got it|allow all)/i)) {
                        el.click();
                    }
                }
            }''')
            
            await page.wait_for_timeout(1500) # wait for animations
            await page.screenshot(path=filepath, full_page=False)
            await browser.close()
            return filepath
            
    except Exception as e:
        logger.warning(f"Failed to capture screenshot for {url}: {e}")
        return ""
