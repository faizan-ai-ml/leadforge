import os
import random
from typing import Optional, Dict

class ProxyManager:
    def __init__(self, config: dict):
        self.use_proxies = config.get("use_proxies", False)
        self.strategy = config.get("proxy_strategy", "round_robin")
        
        proxy_str = os.getenv("PROXY_URLS", "")
        self.proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]
        
        self._current_index = 0
        
    def get_proxy(self, domain: str = None) -> Optional[str]:
        """Returns a proxy string based on the chosen strategy."""
        if not self.use_proxies or not self.proxies:
            return None
            
        if self.strategy == "random":
            return random.choice(self.proxies)
            
        if self.strategy == "sticky" and domain:
            # Hash the domain to pick a consistent proxy
            idx = hash(domain) % len(self.proxies)
            return self.proxies[idx]
            
        # Default: round_robin
        proxy = self.proxies[self._current_index % len(self.proxies)]
        self._current_index += 1
        return proxy

    def get_requests_proxy(self, domain: str = None) -> Optional[Dict[str, str]]:
        """Format for python requests / curl_cffi format: {'http': '...', 'https': '...'}"""
        proxy = self.get_proxy(domain)
        if not proxy:
            return None
            
        # Ensure scheme is present
        if not proxy.startswith('http'):
            proxy = f"http://{proxy}"
            
        return {"http": proxy, "https": proxy}

    def get_playwright_proxy(self, domain: str = None) -> Optional[Dict[str, str]]:
        """Format for Playwright context: {'server': 'ip:port', 'username': '...', 'password': '...'}"""
        proxy_url = self.get_proxy(domain)
        if not proxy_url:
            return None
            
        # Basic parsing (handling user:pass@ip:port)
        if not proxy_url.startswith('http'):
            proxy_url = f"http://{proxy_url}"
            
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        
        pw_proxy = {"server": f"{parsed.scheme or 'http'}://{parsed.hostname}:{parsed.port}"}
        
        if parsed.username and parsed.password:
            pw_proxy["username"] = parsed.username
            pw_proxy["password"] = parsed.password
            
        return pw_proxy
