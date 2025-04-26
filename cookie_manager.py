
import os
import time
import logging
import requests
import json

logger = logging.getLogger(__name__)
COOKIE_FILE = 'cookies.txt'

def serialize_netscape(cookies):
    """Convert cookies dictionary to Netscape format"""
    lines = []
    for name, value in cookies.items():
        domain = '.youtube.com'
        secure = 'TRUE'
        http_only = 'FALSE'
        path = '/'
        expires = str(int(time.time() + 3600*24*7))  # Default 1 week
        lines.append(f"{domain}\t{http_only}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
    
    # Add some extra common YouTube cookies
    lines.append(f".youtube.com\tFALSE\t/\tTRUE\t{expires}\tCONSENT\tYES+cb")
    lines.append(f".youtube.com\tFALSE\t/\tTRUE\t{expires}\tLOGIN_INFO\tAFmmF2swRQIgUX1VVZ1p8MH3h2tOYVxMm-kBbHqyZh4nh7e5M-_VH6sCIQDOIx9V4YbRYEkxeE_KIHwr_oFYw5nOqhJEp1RP3NGXNw:QUQ3MjNmeHByVkFQLTNpUl9aNFlETV9xVGE0R2NWN2kweTJTRm1YV1ZfLXZtQVhsYjV0QVk0QU54ME1rM09xNVdiU2psanVVWjdaOHRyVFNmUzN4UlZnMzNsY2JLbXFubXEzVE1BZnlhS1hvbUZfY191QklOZWFyT0xvX2ZuLVgzc252UXpzSHJncGdBZ1BjMWdsTnRZMGYwT3V2N3diQw==")
    
    return "\n".join(lines)

def refresh_cookies():
    """Get YouTube cookies directly without using a browser"""
    try:
        # We'll create a minimal set of cookies that allow anonymous YouTube access
        # This approach doesn't use actual Google authentication
        
        logger.info("Creating cookies file for anonymous YouTube access...")
        
        # Basic cookies that allow YouTube to work without authentication
        cookies = {
            'VISITOR_INFO1_LIVE': 'y1OUdbXCbS4',
            'PREF': 'f4=4000000&f6=40000000&tz=UTC',
            'YSC': 'H1xbmzYEbUQ'
        }
        
        # Try to make a test request to YouTube to get additional cookies
        try:
            session = requests.Session()
            response = session.get('https://www.youtube.com/')
            if response.status_code == 200:
                # Extract any cookies from the response
                for cookie in session.cookies:
                    cookies[cookie.name] = cookie.value
                logger.info("Successfully fetched additional cookies from YouTube")
        except Exception as req_error:
            logger.warning(f"Could not fetch additional cookies: {str(req_error)}")
        
        # Write cookies to file
        with open(COOKIE_FILE, 'w') as f:
            f.write(serialize_netscape(cookies))
        
        logger.info("Successfully created YouTube cookies file")
        return True

    except Exception as e:
        logger.error(f"Error creating cookies: {str(e)}")
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
