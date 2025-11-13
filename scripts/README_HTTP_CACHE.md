# HTTP Cache

Simple disk-based caching for HTTP requests.

## Quick Start

```python
from http_cache import HTTPCache

# Create cache
cache = HTTPCache(cache_dir="./cache", ttl=3600)  # 1 hour TTL

# Make request (cached automatically)
response = cache.request("https://api.example.com/data")

# Second request uses cache (instant!)
response = cache.request("https://api.example.com/data")
```

## Features

- Caches HTTP responses to disk
- Configurable TTL (time-to-live)
- Supports GET, POST, and other methods
- Optional post-processing of responses

## Basic Usage

```python
# Initialize
cache = HTTPCache(
    cache_dir="./cache",  # Where to store cache files
    ttl=3600             # Expire after 1 hour (seconds)
)

# Make cached requests
data = cache.request("https://api.example.com/users")

# Force refresh (ignore cache)
fresh_data = cache.request("https://api.example.com/users", force_refresh=True)

# Clear old cache entries
cache.clear(older_than=86400)  # Clear entries older than 1 day
```

## Post-Processing

```python
# Register a JSON processor
cache.register_post_processor(
    "json",
    lambda r: json.loads(r.get("text", "{}"))
)

# Get JSON directly
data = cache.request(
    "https://api.example.com/data",
    post_processor="json"
)
```

## Files

- `http_cache.py` - Main cache implementation
- `http_cache_example.py` - Usage examples
- `test_http_cache.py` - Test suite

Run tests: `python test_http_cache.py`