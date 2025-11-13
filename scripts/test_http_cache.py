"""
Test script for HTTPCache class.

This script tests various features of the HTTPCache including:
- Basic caching functionality
- Post-processing capabilities
- TTL expiration
- Memory and disk cache operations
- Custom extensions
"""

import unittest
import tempfile
import shutil
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from http_cache import HTTPCache
from http_cache_example import ExtendedHTTPCache, APICache


class TestHTTPCache(unittest.TestCase):
    """Test cases for HTTPCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = HTTPCache(
            cache_dir=self.temp_dir,
            ttl=2  # 2 seconds for testing
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_key_generation(self):
        """Test cache key generation for different request parameters."""
        # Same parameters should generate same key
        key1 = self.cache._generate_cache_key(
            "https://example.com",
            "GET",
            {"param": "value"}
        )
        key2 = self.cache._generate_cache_key(
            "https://example.com",
            "GET",
            {"param": "value"}
        )
        self.assertEqual(key1, key2)
        
        # Different parameters should generate different keys
        key3 = self.cache._generate_cache_key(
            "https://example.com",
            "POST",
            {"param": "value"}
        )
        self.assertNotEqual(key1, key3)
        
        # Different URLs should generate different keys
        key4 = self.cache._generate_cache_key(
            "https://different.com",
            "GET",
            {"param": "value"}
        )
        self.assertNotEqual(key1, key4)
    
    def test_cache_expiration(self):
        """Test TTL expiration functionality."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"test": "data"}'
        mock_response.text = '{"test": "data"}'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        # Cache the response
        self.cache.set("https://example.com", mock_response)
        
        # Should be available immediately
        cached = self.cache.get("https://example.com")
        self.assertIsNotNone(cached)
        
        # Wait for expiration
        time.sleep(3)
        
        # Should be expired now
        cached = self.cache.get("https://example.com")
        self.assertIsNone(cached)
    
    def test_post_processor_registration(self):
        """Test post-processor registration and application."""
        # Register a test processor
        def test_processor(response):
            return {"processed": True, "status": response["status_code"]}
        
        self.cache.register_post_processor("test", test_processor)
        
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'test'
        mock_response.text = 'test'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        # Cache the response
        self.cache.set("https://example.com", mock_response)
        
        # Get with post-processor
        processed = self.cache.get("https://example.com", post_processor="test")
        self.assertEqual(processed, {"processed": True, "status": 200})
    
    def test_disk_cache(self):
        """Test that disk caching works."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'test'
        mock_response.text = 'test'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        # Cache the response
        self.cache.set("https://example.com", mock_response)
        
        # Check disk cache
        cache_files = list(Path(self.temp_dir).glob("*.pkl"))
        self.assertEqual(len(cache_files), 1)
        
        # Verify disk cache works
        cached = self.cache.get("https://example.com")
        self.assertIsNotNone(cached)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        # Initially empty
        stats = self.cache.get_stats()
        self.assertEqual(stats["disk_entries"], 0)
        
        # Add some entries
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'test'
        mock_response.text = 'test'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        self.cache.set("https://example1.com", mock_response)
        self.cache.set("https://example2.com", mock_response)
        
        stats = self.cache.get_stats()
        self.assertEqual(stats["disk_entries"], 2)
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add some entries
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'test'
        mock_response.text = 'test'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        self.cache.set("https://example1.com", mock_response)
        self.cache.set("https://example2.com", mock_response)
        
        # Clear all
        cleared = self.cache.clear()
        self.assertEqual(cleared, 2)  # 2 disk entries
        
        # Verify empty
        stats = self.cache.get_stats()
        self.assertEqual(stats["disk_entries"], 0)
    
    @patch('requests.request')
    def test_request_method(self, mock_request):
        """Test the request method with mocked HTTP calls."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"result": "success"}'
        mock_response.text = '{"result": "success"}'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://api.example.com/test"
        mock_request.return_value = mock_response
        
        # First request should hit the network
        result1 = self.cache.request("https://api.example.com/test")
        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(result1["status_code"], 200)
        
        # Second request should use cache
        result2 = self.cache.request("https://api.example.com/test")
        self.assertEqual(mock_request.call_count, 1)  # Still 1, not 2
        self.assertEqual(result2["status_code"], 200)
        
        # Force refresh should hit network again
        result3 = self.cache.request("https://api.example.com/test", force_refresh=True)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(result3["status_code"], 200)


class TestExtendedHTTPCache(unittest.TestCase):
    """Test cases for ExtendedHTTPCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = ExtendedHTTPCache(
            cache_dir=self.temp_dir,
            ttl=60
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_links_processor(self):
        """Test link extraction processor."""
        response = {
            "text": 'Visit https://example.com and http://test.org for more info.'
        }
        links = self.cache.extract_links_processor(response)
        self.assertEqual(len(links), 2)
        self.assertIn("https://example.com", links)
        self.assertIn("http://test.org", links)
    
    def test_word_count_processor(self):
        """Test word count processor."""
        response = {
            "text": "This is a test sentence with some words."
        }
        stats = self.cache.word_count_processor(response)
        self.assertEqual(stats["total_words"], 8)
        self.assertEqual(stats["unique_words"], 8)
        self.assertGreater(stats["characters"], 0)
    
    def test_html_title_processor(self):
        """Test HTML title extraction."""
        response = {
            "text": '<html><head><title>Test Page</title></head><body>Content</body></html>'
        }
        title = self.cache.parse_html_title_processor(response)
        self.assertEqual(title, "Test Page")
        
        # Test with no title
        response_no_title = {"text": "<html><body>No title here</body></html>"}
        title = self.cache.parse_html_title_processor(response_no_title)
        self.assertEqual(title, "No title found")
    
    @patch('requests.request')
    def test_batch_request(self, mock_request):
        """Test batch request functionality."""
        # Setup mock responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{"data": "test"}'
        mock_response.text = '{"data": "test"}'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        mock_request.return_value = mock_response
        
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
        
        results = self.cache.batch_request(urls, delay=0.01)
        
        self.assertEqual(len(results), 3)
        for url in urls:
            self.assertIn(url, results)
            self.assertTrue(results[url]["success"])
    
    def test_cache_info(self):
        """Test cache info retrieval."""
        # Initially not cached
        info = self.cache.get_cache_info("https://example.com")
        self.assertFalse(info["cached"])
        
        # Cache something
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'test'
        mock_response.text = 'test'
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com"
        
        self.cache.set("https://example.com", mock_response)
        
        # Now should be cached
        info = self.cache.get_cache_info("https://example.com")
        self.assertTrue(info["cached"])
        self.assertIn("location", info)
        self.assertIn("timestamp", info)


class TestAPICache(unittest.TestCase):
    """Test cases for APICache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = APICache(
            api_base_url="https://api.example.com",
            api_key="test_key",
            rate_limit=10,
            cache_dir=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_api_error_processor(self):
        """Test API error processor."""
        # Test error response
        error_response = {
            "status_code": 404,
            "text": '{"message": "Not found", "code": 404}'
        }
        result = self.cache.api_error_processor(error_response)
        self.assertTrue(result["has_error"])
        self.assertEqual(result["status_code"], 404)
        self.assertIn("Not found", result["error_message"])
        
        # Test success response
        success_response = {
            "status_code": 200,
            "text": '{"data": "success"}'
        }
        result = self.cache.api_error_processor(success_response)
        self.assertFalse(result["has_error"])
    
    def test_api_data_processor(self):
        """Test API data extraction processor."""
        # Test with data field
        response_with_data = {
            "text": '{"data": {"id": 1, "name": "Test"}, "status": "ok"}'
        }
        result = self.cache.api_data_processor(response_with_data)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "Test")
        
        # Test without data field
        response_without_data = {
            "text": '{"id": 2, "name": "Direct"}'
        }
        result = self.cache.api_data_processor(response_without_data)
        self.assertEqual(result["id"], 2)
        self.assertEqual(result["name"], "Direct")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Make several requests quickly
        start_time = time.time()
        
        for i in range(5):
            self.cache._check_rate_limit()
        
        # Should complete quickly (no rate limiting hit)
        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0)
        
        # Verify request times are tracked
        self.assertEqual(len(self.cache.request_times), 5)


def run_integration_test():
    """Run a simple integration test with real HTTP requests."""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST (requires internet connection)")
    print("=" * 60)
    
    cache = HTTPCache(
        cache_dir="./test_cache",
        ttl=60
    )
    
    # Register JSON processor
    cache.register_post_processor(
        "json",
        lambda r: json.loads(r.get("text", "{}"))
    )
    
    try:
        print("\n1. Testing with httpbin.org...")
        
        # First request (network)
        start = time.time()
        response1 = cache.request(
            "https://httpbin.org/get",
            params={"test": "value"},
            timeout=5
        )
        time1 = time.time() - start
        print(f"   First request: {time1:.3f}s (from network)")
        
        # Second request (cached)
        start = time.time()
        response2 = cache.request(
            "https://httpbin.org/get",
            params={"test": "value"}
        )
        time2 = time.time() - start
        print(f"   Second request: {time2:.3f}s (from cache)")
        
        # Verify cache is faster
        assert time2 < time1, "Cached request should be faster"
        print("   ✓ Cache is working correctly")
        
        # Test with post-processor
        json_response = cache.request(
            "https://httpbin.org/get",
            params={"test": "value"},
            post_processor="json"
        )
        assert "args" in json_response, "JSON response should have 'args' field"
        print("   ✓ Post-processor working correctly")
        
        print("\n2. Cache statistics:")
        stats = cache.get_stats()
        print(f"   Disk entries: {stats['disk_entries']}")
        print(f"   Disk size: {stats.get('disk_size_mb', 0):.2f} MB")
        
        # Clean up
        shutil.rmtree("./test_cache", ignore_errors=True)
        print("\n✓ Integration test passed!")
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        shutil.rmtree("./test_cache", ignore_errors=True)


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration test
    run_integration_test()