import requests
import time
from fake_useragent import UserAgent

def get_bypass_headers():
    """Generate headers to bypass Cloudflare detection"""
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def wait_with_backoff(attempt):
    """Exponential backoff for retries"""
    wait_time = min(300, (2 ** attempt) + (time.time() % 1))
    print(f"⏳ Waiting {wait_time:.1f}s before retry...")
    time.sleep(wait_time)