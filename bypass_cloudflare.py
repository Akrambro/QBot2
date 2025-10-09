import time
import random

def wait_with_random_delay(min_seconds=5, max_seconds=15):
    """Add random delay to avoid detection patterns"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def get_random_user_agent():
    """Return random user agent to avoid detection"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    ]
    return random.choice(agents)