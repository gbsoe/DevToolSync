
import os
import time
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)
COOKIE_FILE = 'cookies.txt'

def serialize_netscape(cookies):
    """Convert Playwright cookies to Netscape format"""
    lines = []
    for c in cookies:
        domain = c['domain']
        secure = 'TRUE' if c.get('secure') else 'FALSE'
        http_only = 'TRUE' if c.get('httpOnly') else 'FALSE'
        path = c.get('path', '/')
        expires = str(int(c.get('expires', time.time() + 3600*24*7)))  # Default 1 week
        name = c['name']
        value = c['value']
        lines.append(f"{domain}\t{http_only}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
    return "\n".join(lines)

def refresh_cookies():
    """Get fresh YouTube cookies using Playwright"""
    try:
        email = os.environ.get('YT_EMAIL')
        password = os.environ.get('YT_PASS')

        if not email or not password:
            raise ValueError("YouTube credentials not found in environment variables")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to Google sign-in
            page.goto('https://accounts.google.com/signin/v2/identifier?service=youtube')
            page.fill('input[type="email"]', email)
            page.click('button[jsname="LgbsSe"]')
            
            # Wait for and fill password
            page.wait_for_selector('input[type="password"]', timeout=60000)
            page.fill('input[type="password"]', password)
            page.click('button[jsname="LgbsSe"]')
            
            # Wait for successful navigation to YouTube
            page.wait_for_url('https://www.youtube.com/*', timeout=60000)
            cookies = context.cookies()
            browser.close()

        # Save cookies to file
        with open(COOKIE_FILE, 'w') as f:
            f.write(serialize_netscape(cookies))
            
        logger.info("Successfully refreshed YouTube cookies")
        return True

    except Exception as e:
        logger.error(f"Error refreshing cookies: {str(e)}")
        return False

def ensure_fresh_cookies():
    """Ensure cookies exist and are fresh (< 1 hour old)"""
    try:
        if not os.path.exists(COOKIE_FILE) or \
           os.path.getmtime(COOKIE_FILE) < (time.time() - 3600):
            return refresh_cookies()
        return True
    except Exception as e:
        logger.error(f"Error checking cookies: {str(e)}")
        return False
