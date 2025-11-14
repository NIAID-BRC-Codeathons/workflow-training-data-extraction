#!/usr/bin/env python3
"""
Test script to verify the Firecrawl fix works correctly
"""

import sys
import os

# Add current directory to path to import the fixed script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the execute_search function from the fixed script
exec(open('FireCrawl_Script_Scrape_Symptoms').read())

def test_search():
    """Test the fixed search function"""
    print("Testing Firecrawl search with fixed error handling...")
    
    try:
        # Test with a simple query
        results = execute_search("measles cases reported 2024 OR 2025 US state health department", num_results=3)
        
        if results:
            print(f"✅ Search successful! Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.get('title', 'No title')}")
                print(f"   URL: {result.get('url', 'No URL')}")
                print(f"   Snippet: {result.get('snippet', 'No snippet')[:100]}...")
        else:
            print("⚠️ No results returned, but no error occurred")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()