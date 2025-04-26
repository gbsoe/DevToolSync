import os
import time
import logging
import requests

logger = logging.getLogger(__name__)
COOKIE_FILE = 'cookies.txt'

def create_netscape_cookies_file():
    """Create a Netscape format cookies file directly with common YouTube cookies"""
    logger.info("Creating Netscape format cookies file for YouTube")
    
    # Create header that identifies file as Netscape format
    lines = ["# Netscape HTTP Cookie File"]
    lines.append("# https://curl.haxx.se/rfc/cookie_spec.html")
    lines.append("# This is a generated file!  Do not edit.")
    lines.append("")
    
    # Add essential YouTube cookies in the correct format
    # Format: domain flag path secure expiry name value
    expires = str(int(time.time() + 3600 * 24 * 7))  # Default 1 week
    
    # These are some common YouTube cookies that allow basic functionality
    cookies = [
        (".youtube.com", "TRUE", "/", "TRUE", expires, "CONSENT", "YES+cb"),
        (".youtube.com", "TRUE", "/", "TRUE", expires, "VISITOR_INFO1_LIVE", "y1OUdbXCbS4"),
        (".youtube.com", "TRUE", "/", "TRUE", expires, "YSC", "aaaaaaaaaaa"),
        (".youtube.com", "TRUE", "/", "TRUE", expires, "PREF", "f4=4000000&f6=40000000&hl=en"),
        (".youtube.com", "TRUE", "/", "TRUE", expires, "GPS", "1"),
        ("youtube.com", "TRUE", "/", "TRUE", expires, "SID", "ageaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    ]
    
    # Add each cookie to the file content
    for cookie in cookies:
        domain, flag, path, secure, expiry, name, value = cookie
        line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}"
        lines.append(line)
    
    # Try to get more cookies from a real YouTube request
    try:
        session = requests.Session()
        response = session.get('https://www.youtube.com/')
        
        if response.status_code == 200:
            # Add any cookies received from the real request
            for cookie in session.cookies:
                # Proper Netscape format
                domain = f".{cookie.domain}" if not cookie.domain.startswith('.') else cookie.domain
                line = f"{domain}\tTRUE\t{cookie.path}\t{'TRUE' if cookie.secure else 'FALSE'}\t{expires}\t{cookie.name}\t{cookie.value}"
                lines.append(line)
            logger.info("Added cookies from live YouTube request")
    except Exception as e:
        logger.warning(f"Could not get live cookies from YouTube: {e}")
    
    # Write file
    content = "\n".join(lines)
    with open(COOKIE_FILE, 'w') as f:
        f.write(content)
    
    logger.info(f"Created cookies file with {len(lines) - 4} cookies")
    return True

def refresh_cookies():
    """Create YouTube cookies file without using Playwright"""
    try:
        return create_netscape_cookies_file()
    except Exception as e:
        logger.error(f"Error creating cookies: {str(e)}")
        return False

def ensure_fresh_cookies():
    """Ensure cookies exist and are fresh (< 1 hour old)"""
    try:
        # Check if cookie file exists and is less than 1 hour old
        if not os.path.exists(COOKIE_FILE) or \
           os.path.getmtime(COOKIE_FILE) < (time.time() - 3600):
            logger.info("Creating or refreshing cookie file")
            return refresh_cookies()
        logger.info("Using existing cookie file")
        return True
    except Exception as e:
        logger.error(f"Error checking cookies: {str(e)}")
        return False