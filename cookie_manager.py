
import os
import logging
import browser_cookie3
import time
from http.cookiejar import MozillaCookieJar

logger = logging.getLogger(__name__)

class CookieManager:
    def __init__(self, cookie_file='cookies.txt', refresh_interval=3600):
        self.cookie_file = cookie_file
        self.refresh_interval = refresh_interval
        self.last_refresh = 0

    def ensure_fresh_cookies(self):
        """Ensures cookies are fresh, refreshing if needed"""
        if time.time() - self.last_refresh > self.refresh_interval:
            self.refresh_cookies()

    def refresh_cookies(self):
        """Extracts fresh YouTube cookies from browser"""
        try:
            # Get cookies from common browsers
            cj = browser_cookie3.load(domain_name='.youtube.com')
            
            # Convert to Mozilla/Netscape format
            mozilla_cj = MozillaCookieJar(self.cookie_file)
            for cookie in cj:
                mozilla_cj.set_cookie(cookie)
            
            # Save to file
            mozilla_cj.save()
            self.last_refresh = time.time()
            logger.info("Successfully refreshed YouTube cookies")
            
        except Exception as e:
            logger.error(f"Error refreshing cookies: {str(e)}")
            raise
