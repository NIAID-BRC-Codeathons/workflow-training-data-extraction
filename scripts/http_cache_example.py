"""
Example usage and extension of the HTTPCache class.

This script demonstrates:
1. Basic caching of HTTP requests
2. Custom post-processors for different response formats
3. Extending the cache for specific use cases
"""

import json
from typing import Dict, Any, List
from http_cache import HTTPCache
import time


class ExtendedHTTPCache(HTTPCache):
    """
    Extended version of HTTPCache with additional features for specific use cases.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Register custom post-processors
        self.register_post_processor("extract_links", self.extract_links_processor)
        self.register_post_processor("extract_headers", self.extract_headers_processor)
        self.register_post_processor("parse_html_title", self.parse_html_title_processor)
        self.register_post_processor("word_count", self.word_count_processor)
    
    @staticmethod
    def extract_links_processor(response: Dict[str, Any]) -> List[str]:
        """Extract all URLs from response text."""
        import re
        text = response.get("text", "")
        # Simple URL regex pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def extract_headers_processor(response: Dict[str, Any]) -> Dict[str, str]:
        """Extract and return response headers."""
        return response.get("headers", {})
    
    @staticmethod
    def parse_html_title_processor(response: Dict[str, Any]) -> str:
        """Extract title from HTML response."""
        import re
        text = response.get("text", "")
        title_match = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE)
        return title_match.group(1) if title_match else "No title found"
    
    @staticmethod
    def word_count_processor(response: Dict[str, Any]) -> Dict[str, int]:
        """Count words in the response text."""
        text = response.get("text", "")
        words = text.split()
        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "characters": len(text)
        }
    
    def batch_request(
        self,
        urls: List[str],
        method: str = "GET",
        post_processor: str = None,
        delay: float = 0.1
    ) -> Dict[str, Any]:
        """
        Make batch requests with optional delay between requests.
        
        Args:
            urls: List of URLs to request
            method: HTTP method
            post_processor: Post-processor to apply
            delay: Delay between requests in seconds
            
        Returns:
            Dictionary mapping URLs to responses
        """
        results = {}
        
        for i, url in enumerate(urls):
            if i > 0:
                time.sleep(delay)
            
            try:
                response = self.request(
                    url=url,
                    method=method,
                    post_processor=post_processor
                )
                results[url] = {
                    "success": True,
                    "data": response
                }
            except Exception as e:
                results[url] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def get_cache_info(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """
        Get information about a cached entry.
        
        Args:
            url: The URL to check
            method: HTTP method
            
        Returns:
            Cache information or None if not cached
        """
        cache_key = self._generate_cache_key(url, method)
        
        # Check disk cache
        cached_data = self._load_from_cache(cache_key)
        if cached_data:
            return {
                "cached": True,
                "location": "disk",
                "timestamp": cached_data.get("timestamp"),
                "age_seconds": time.time() - cached_data.get("timestamp", 0),
                "processed_formats": list(cached_data.get("processed", {}).keys())
            }
        
        return {"cached": False}


class APICache(ExtendedHTTPCache):
    """
    Specialized cache for API requests with rate limiting and retry logic.
    """
    
    def __init__(
        self,
        api_base_url: str = None,
        api_key: str = None,
        rate_limit: int = 60,  # requests per minute
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.request_times = []
        
        # Register API-specific processors
        self.register_post_processor("api_error", self.api_error_processor)
        self.register_post_processor("api_data", self.api_data_processor)
    
    @staticmethod
    def api_error_processor(response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract error information from API response."""
        if response.get("status_code", 200) >= 400:
            try:
                error_data = json.loads(response.get("text", "{}"))
                return {
                    "has_error": True,
                    "status_code": response.get("status_code"),
                    "error_message": error_data.get("message", "Unknown error"),
                    "error_details": error_data
                }
            except:
                return {
                    "has_error": True,
                    "status_code": response.get("status_code"),
                    "error_message": response.get("text", "Unknown error")
                }
        return {"has_error": False}
    
    @staticmethod
    def api_data_processor(response: Dict[str, Any]) -> Any:
        """Extract data field from API response."""
        try:
            json_data = json.loads(response.get("text", "{}"))
            return json_data.get("data", json_data)
        except:
            return None
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        current_time = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        if len(self.request_times) >= self.rate_limit:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_time = 60 - (current_time - oldest_request)
            if wait_time > 0:
                time.sleep(wait_time)
                # Clean up again after waiting
                self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        self.request_times.append(current_time)
    
    def request(self, url: str, **kwargs) -> Any:
        """
        Make an API request with rate limiting.
        
        Args:
            url: The request URL (can be relative if api_base_url is set)
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        # Apply rate limiting
        self._check_rate_limit()
        
        # Construct full URL if base URL is provided
        if self.api_base_url and not url.startswith("http"):
            url = f"{self.api_base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # Add API key to headers if provided
        if self.api_key:
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.api_key}"
            kwargs["headers"] = headers
        
        return super().request(url, **kwargs)


def demo_basic_usage():
    """Demonstrate basic HTTPCache usage."""
    print("=" * 60)
    print("BASIC HTTP CACHE DEMO")
    print("=" * 60)
    
    # Create a basic cache
    cache = HTTPCache(
        cache_dir="./demo_cache",
        ttl=300  # 5 minutes
    )
    
    # Register a simple JSON processor
    cache.register_post_processor("json", lambda r: json.loads(r.get("text", "{}")))
    
    print("\n1. Making first request (will hit the network)...")
    start = time.time()
    response = cache.request("https://httpbin.org/get", params={"test": "value"})
    print(f"   Time taken: {time.time() - start:.3f}s")
    print(f"   Status code: {response['status_code']}")
    
    print("\n2. Making same request again (should be cached)...")
    start = time.time()
    response = cache.request("https://httpbin.org/get", params={"test": "value"})
    print(f"   Time taken: {time.time() - start:.3f}s")
    print(f"   Status code: {response['status_code']}")
    
    print("\n3. Request with JSON post-processing...")
    json_response = cache.request(
        "https://httpbin.org/get",
        params={"test": "value"},
        post_processor="json"
    )
    print(f"   Args from response: {json_response.get('args', {})}")
    
    print("\n4. Cache statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")


def demo_extended_usage():
    """Demonstrate ExtendedHTTPCache with custom processors."""
    print("\n" + "=" * 60)
    print("EXTENDED HTTP CACHE DEMO")
    print("=" * 60)
    
    # Create extended cache
    cache = ExtendedHTTPCache(
        cache_dir="./extended_cache",
        ttl=600  # 10 minutes
    )
    
    print("\n1. Fetching HTML and extracting title...")
    title = cache.request(
        "https://example.com",
        post_processor="parse_html_title"
    )
    print(f"   Page title: {title}")
    
    print("\n2. Getting word count from response...")
    word_stats = cache.request(
        "https://example.com",
        post_processor="word_count"
    )
    print(f"   Word statistics: {word_stats}")
    
    print("\n3. Extracting links from page...")
    links = cache.request(
        "https://example.com",
        post_processor="extract_links"
    )
    print(f"   Found {len(links)} links")
    if links:
        print(f"   First link: {links[0]}")
    
    print("\n4. Checking cache info for the URL...")
    cache_info = cache.get_cache_info("https://example.com")
    print(f"   Cache info: {cache_info}")


def demo_api_cache():
    """Demonstrate APICache with rate limiting."""
    print("\n" + "=" * 60)
    print("API CACHE DEMO")
    print("=" * 60)
    
    # Create API cache
    api_cache = APICache(
        api_base_url="https://api.github.com",
        rate_limit=30,  # 30 requests per minute
        cache_dir="./api_cache",
        ttl=1800  # 30 minutes
    )
    
    print("\n1. Fetching GitHub user info...")
    user_data = api_cache.request(
        "/users/github",
        post_processor="api_data"
    )
    if user_data:
        print(f"   User: {user_data.get('name', 'N/A')}")
        print(f"   Public repos: {user_data.get('public_repos', 0)}")
    
    print("\n2. Batch requesting multiple endpoints...")
    urls = [
        "/users/github",
        "/users/torvalds",
        "/users/gvanrossum"
    ]
    
    results = api_cache.batch_request(
        urls,
        post_processor="api_data",
        delay=0.5  # Half second delay between requests
    )
    
    print("   Results:")
    for url, result in results.items():
        if result["success"]:
            data = result["data"]
            if isinstance(data, dict):
                name = data.get("name", "N/A")
                print(f"     {url}: {name}")
            else:
                print(f"     {url}: Success")
        else:
            print(f"     {url}: Failed - {result['error']}")


if __name__ == "__main__":
    # Run demonstrations
    demo_basic_usage()
    demo_extended_usage()
    demo_api_cache()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nThe HTTPCache class is now ready to use in your scripts!")
    print("Import it with: from http_cache import HTTPCache")
    print("\nKey features:")
    print("- Caches HTTP requests with configurable TTL")
    print("- Disk-based caching for persistence")
    print("- Extensible with custom post-processors")
    print("- Can be subclassed for specific use cases")