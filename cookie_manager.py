
import os
import time
import logging
from playwright.sync_api import sync_playwright
import json

logger = logging.getLogger(__name__)
COOKIE_FILE = 'cookies.txt'

def serialize_netscape(cookies):
    """Convert cookies dictionary to Netscape format"""
    # Add header that identifies file as Netscape format
    lines = ["# Netscape HTTP Cookie File"]
    lines.append("# https://curl.haxx.se/rfc/cookie_spec.html")
    lines.append("# This is a generated file!  Do not edit.")
    lines.append("")
    
    for cookie in cookies:
        domain = cookie['domain'] if cookie['domain'].startswith('.') else '.' + cookie['domain']
        http_only = "TRUE" if cookie.get('httpOnly', False) else "FALSE"
        secure = "TRUE" if cookie.get('secure', False) else "FALSE"
        path = cookie['path']
        expires = str(int(cookie.get('expires', time.time() + 3600 * 24 * 7)))  # Default 1 week
        name = cookie['name']
        value = cookie['value']
        
        # Format: domain\tdomain_initial_dot\tpath\tsecure\texpiry\tname\tvalue
        line = f"{domain}\t{http_only}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        lines.append(line)
    
    return "\n".join(lines)

def refresh_cookies():
    """Get fresh YouTube cookies using Playwright"""
    try:
        email = os.environ.get('YT_EMAIL')
        password = os.environ.get('YT_PASS')

        if not email or not password:
            logger.error("YouTube credentials not found in environment variables")
            return False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()

            logger.info("Navigating to Google sign-in page...")
            page.goto('https://accounts.google.com/signin/v2/identifier?service=youtube')
            
            logger.info("Entering email...")
            page.fill('input[type="email"]', email)
            page.click('button[jsname="LgbsSe"]')

            logger.info("Waiting for password field...")
            page.wait_for_selector('input[type="password"]', timeout=60000)

            logger.info("Entering password...")
            page.fill('input[type="password"]', password)
            page.click('button[jsname="LgbsSe"]')

            logger.info("Waiting for YouTube navigation...")
            page.wait_for_url('https://www.youtube.com/*', timeout=60000)
            
            logger.info("Getting cookies...")
            cookies = context.cookies()
            
            logger.info("Writing cookies to file...")
            with open(COOKIE_FILE, 'w') as f:
                f.write(serialize_netscape(cookies))

            logger.info("Successfully refreshed YouTube cookies")
            browser.close()
            return True

    except Exception as e:
        logger.error(f"Error refreshing cookies: {str(e)}")
        if 'browser' in locals():
            browser.close()
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
