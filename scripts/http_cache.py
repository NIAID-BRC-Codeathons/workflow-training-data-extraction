"""
HTTP Request Cache Module

A disk-based caching system for HTTP requests that stores key-value pairs of:
1. key: requests (URL + method + params)
2. value: raw response
3. value: post-processed responses (extendable)
"""

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime, timedelta
import requests


class HTTPCache:
    """
    A disk-based cache for HTTP requests that stores raw responses and supports
    post-processing of cached responses.
    
    Features:
    - File-based persistence
    - TTL (time-to-live) support
    - Custom key generation
    - Post-processing hooks
    """
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        ttl: Optional[int] = 3600
    ):
        """
        Initialize the HTTP cache.
        
        Args:
            cache_dir: Directory to store cached responses
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        
        # Post-processing functions registry
        self.post_processors: Dict[str, Callable] = {}
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_cache_key(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None
    ) -> str:
        """
        Generate a unique cache key for the request.
        
        Args:
            url: The request URL
            method: HTTP method
            params: Query parameters
            headers: Request headers (optional)
            data: Request body data
            
        Returns:
            A unique hash key for the request
        """
        key_parts = {
            "url": url,
            "method": method.upper(),
            "params": params or {},
            "data": data or {}
        }
        
        # Optionally include headers in cache key
        if headers:
            # Only include specific headers that affect response
            relevant_headers = {
                k: v for k, v in headers.items()
                if k.lower() in ['accept', 'content-type', 'authorization']
            }
            if relevant_headers:
                key_parts["headers"] = relevant_headers
        
        # Create a stable string representation
        key_string = json.dumps(key_parts, sort_keys=True)
        
        # Generate SHA256 hash
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _is_expired(self, cached_data: Dict[str, Any]) -> bool:
        """
        Check if cached data has expired.
        
        Args:
            cached_data: The cached data dictionary
            
        Returns:
            True if expired, False otherwise
        """
        if self.ttl is None:
            return False
        
        cached_time = cached_data.get("timestamp", 0)
        current_time = time.time()
        
        return (current_time - cached_time) > self.ttl
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Load cached data from disk.
        
        Args:
            cache_key: The cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "rb") as f:
                cached_data = pickle.load(f)
            
            if self._is_expired(cached_data):
                cache_file.unlink()  # Delete expired cache file
                return None
            
            return cached_data
        except Exception as e:
            print(f"Error loading cache from disk: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Save cached data to disk.
        
        Args:
            cache_key: The cache key
            data: Data to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving cache to disk: {e}")
    
    def get(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None,
        post_processor: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached response for a request.
        
        Args:
            url: The request URL
            method: HTTP method
            params: Query parameters
            headers: Request headers
            data: Request body data
            post_processor: Name of post-processor to apply
            
        Returns:
            Cached response (raw or post-processed) or None
        """
        cache_key = self._generate_cache_key(url, method, params, headers, data)
        
        # Load from disk cache
        cached_data = self._load_from_cache(cache_key)
        if cached_data:
            return self._apply_post_processor(cached_data, post_processor)
        
        return None
    
    def set(
        self,
        url: str,
        response: requests.Response,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None
    ) -> None:
        """
        Cache a response.
        
        Args:
            url: The request URL
            response: The response object to cache
            method: HTTP method
            params: Query parameters
            headers: Request headers
            data: Request body data
        """
        cache_key = self._generate_cache_key(url, method, params, headers, data)
        
        # Prepare cache data
        cached_data = {
            "timestamp": time.time(),
            "url": url,
            "method": method,
            "params": params,
            "headers": headers,
            "data": data,
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "text": response.text,
                "encoding": response.encoding,
                "url": response.url
            },
            "processed": {}  # Store post-processed versions
        }
        
        # Save to disk cache
        self._save_to_cache(cache_key, cached_data)
    
    def request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None,
        post_processor: Optional[str] = None,
        force_refresh: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Any]:
        """
        Make a cached HTTP request.
        
        Args:
            url: The request URL
            method: HTTP method
            params: Query parameters
            headers: Request headers
            data: Request body data
            post_processor: Name of post-processor to apply
            force_refresh: Force a fresh request (ignore cache)
            **kwargs: Additional arguments for requests library
            
        Returns:
            Response data (raw or post-processed)
        """
        # Check cache unless force refresh
        if not force_refresh:
            cached = self.get(url, method, params, headers, data, post_processor)
            if cached is not None:
                return cached
        
        # Make the actual request
        response = requests.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            data=data,
            **kwargs
        )
        
        # Cache the response
        self.set(url, response, method, params, headers, data)
        
        # Get the cached version (which includes post-processing if requested)
        return self.get(url, method, params, headers, data, post_processor)
    
    def register_post_processor(
        self,
        name: str,
        processor: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Register a post-processing function.
        
        Args:
            name: Name of the post-processor
            processor: Function that takes cached data and returns processed result
        """
        self.post_processors[name] = processor
    
    def _apply_post_processor(
        self,
        cached_data: Dict[str, Any],
        processor_name: Optional[str]
    ) -> Any:
        """
        Apply a post-processor to cached data.
        
        Args:
            cached_data: The cached data
            processor_name: Name of the post-processor
            
        Returns:
            Processed data or raw response
        """
        if not processor_name:
            return cached_data["response"]
        
        # Check if already processed
        if processor_name in cached_data.get("processed", {}):
            return cached_data["processed"][processor_name]
        
        # Apply processor
        if processor_name in self.post_processors:
            processor = self.post_processors[processor_name]
            processed_result = processor(cached_data["response"])
            
            # Cache the processed result
            if "processed" not in cached_data:
                cached_data["processed"] = {}
            cached_data["processed"][processor_name] = processed_result
            
            # Update caches with processed data
            cache_key = self._generate_cache_key(
                cached_data["url"],
                cached_data["method"],
                cached_data.get("params"),
                cached_data.get("headers"),
                cached_data.get("data")
            )
            
            self._save_to_cache(cache_key, cached_data)
            
            return processed_result
        
        return cached_data["response"]
    
    def clear(self, older_than: Optional[int] = None) -> int:
        """
        Clear the cache.
        
        Args:
            older_than: Clear only entries older than this many seconds
            
        Returns:
            Number of entries cleared
        """
        cleared = 0
        current_time = time.time()
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.pkl"):
            if older_than is not None:
                try:
                    with open(cache_file, "rb") as f:
                        data = pickle.load(f)
                    if (current_time - data.get("timestamp", 0)) <= older_than:
                        continue
                except:
                    pass
            
            cache_file.unlink()
            cleared += 1
        
        return cleared
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "disk_entries": len(list(self.cache_dir.glob("*.pkl"))),
            "post_processors": list(self.post_processors.keys()),
            "ttl": self.ttl,
            "cache_dir": str(self.cache_dir)
        }
        
        # Calculate total size of disk cache
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.pkl"))
        stats["disk_size_bytes"] = total_size
        stats["disk_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return stats


# Example post-processors
def json_processor(response: Dict[str, Any]) -> Any:
    """Extract JSON from response."""
    try:
        return json.loads(response["text"])
    except:
        return None


def text_processor(response: Dict[str, Any]) -> str:
    """Extract text from response."""
    return response["text"]


def status_processor(response: Dict[str, Any]) -> int:
    """Extract status code from response."""
    return response["status_code"]


# Example usage
if __name__ == "__main__":
    # Create cache instance
    cache = HTTPCache(
        cache_dir="./http_cache",
        ttl=3600  # 1 hour TTL
    )
    
    # Register post-processors
    cache.register_post_processor("json", json_processor)
    cache.register_post_processor("text", text_processor)
    cache.register_post_processor("status", status_processor)
    
    # Example 1: Basic caching
    print("Example 1: Basic GET request")
    response1 = cache.request("https://api.github.com/users/github")
    print(f"Status: {response1['status_code']}")
    
    # Example 2: With post-processing
    print("\nExample 2: GET with JSON post-processing")
    json_data = cache.request(
        "https://api.github.com/users/github",
        post_processor="json"
    )
    if json_data:
        print(f"User: {json_data.get('name', 'N/A')}")
    
    # Example 3: POST request with data
    print("\nExample 3: POST request with data")
    response3 = cache.request(
        "https://httpbin.org/post",
        method="POST",
        data={"key": "value"},
        post_processor="json"
    )
    if response3:
        print(f"Posted data: {response3.get('data', {})}")
    
    # Show cache statistics
    print("\nCache Statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
