#!/usr/bin/env python3
"""
ProMED Outbreak Scraper
Scrapes ProMED-mail for human and animal disease outbreak data from the last 6 months
Uses Firecrawl for web scraping and data extraction
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import signal

from firecrawl import FirecrawlApp

# Configuration
FIRECRAWL_CONFIG = {
    "api_key": os.getenv("FIRECRAWL_API_KEY", "your-api-key-here")
}

# Global list to track visited URLs
visited_urls = []

# Timeout handler
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def execute_search(query: str, num_results: int = 5, use_timeout_signal: bool = True) -> List[Dict[str, Any]]:
    """
    Execute a search query using Firecrawl
    
    Args:
        query: The search query
        num_results: Number of results to return
        use_timeout_signal: Whether to use signal-based timeout (only works in main thread)
    
    Returns:
        List of search results with content
    """
    print(f"Searching with Firecrawl: {query}")
    
    # Initialize the Firecrawl client
    firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_CONFIG["api_key"])
    results = []
    
    try:
        # Only use signal-based timeout in the main thread
        if use_timeout_signal:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
        
        # Execute search with Firecrawl
        search_response = firecrawl_app.search(
            query=query,
            params={
                'timeout': 30000,
                'limit': num_results,
                'scrapeOptions': {'formats': ['markdown']}
            }
        )
        
        # Reset alarm if we used it
        if use_timeout_signal:
            signal.alarm(0)
        
        # Get data items based on the response structure
        if hasattr(search_response, 'data'):
            data_items = search_response.data
        elif isinstance(search_response, dict) and 'data' in search_response:
            data_items = search_response['data']
        else:
            print(f"Unexpected response format: {type(search_response)}")
            data_items = []
            
        # Check if we have results
        if not search_response or len(data_items) == 0:
            print(f"No results found for query: {query}")
            return []
        
        # Process results
        formatted_results = []
        
        for item in data_items:
            # Extract URL
            url = item.url if hasattr(item, 'url') else item.get('url', '')
            
            # Extract markdown content
            content = item.markdown if hasattr(item, 'markdown') else item.get('markdown', '')
            if not content:
                content = item.content if hasattr(item, 'content') else item.get('content', '')
            
            # Get title
            title = item.title if hasattr(item, 'title') else item.get('title', url)
            
            formatted_results.append({
                "title": title,
                "url": url,
                "source": url.split("//")[-1].split("/")[0] if "//" in url else "unknown",
                "snippet": content[:500] + "..." if len(content) > 500 else content,
                "content": content,
                "query": query
            })
        
        # Only print response dictionary if zero results found
        if len(formatted_results) == 0:
            if hasattr(search_response, '__dict__'):
                response_dict = search_response.__dict__
            elif isinstance(search_response, dict):
                response_dict = search_response
            else:
                response_dict = {"response": str(search_response)}
                
            print(f"Zero results - Response dictionary: {response_dict}")
        
        print(f"Found {len(formatted_results)} results from Firecrawl")
        
        # Track visited URLs globally
        global visited_urls
        visited_urls.extend([item["url"] for item in formatted_results if item["url"]])
        
        return formatted_results
        
    except TimeoutError:
        print(f"Search timed out after 30 seconds: {query}")
        return []
    except Exception as e:
        print(f"Error searching with Firecrawl: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_date_range(months_back: int = 6) -> tuple:
    """
    Get the date range for searching (last N months)
    
    Args:
        months_back: Number of months to go back
    
    Returns:
        Tuple of (start_date, end_date) as strings
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)  # Approximate months
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def search_promed_outbreaks(months_back: int = 6, max_results_per_query: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search ProMED for outbreak data from the last N months
    
    Args:
        months_back: Number of months to search back
        max_results_per_query: Maximum results per search query
    
    Returns:
        Dictionary with categorized outbreak data
    """
    start_date, end_date = get_date_range(months_back)
    print(f"\n{'='*60}")
    print(f"Searching ProMED for outbreaks from {start_date} to {end_date}")
    print(f"{'='*60}\n")
    
    # Search queries for different types of outbreaks
    search_queries = [
        f"site:promedmail.org human disease outbreak {datetime.now().year}",
        f"site:promedmail.org animal disease outbreak {datetime.now().year}",
        f"site:promedmail.org zoonotic disease {datetime.now().year}",
        f"site:promedmail.org epidemic alert {datetime.now().year}",
        f"site:promedmail.org infectious disease {datetime.now().year}",
        f"site:promedmail.org confirmed outbreak {datetime.now().year}",
        f"site:promedmail.org potential outbreak {datetime.now().year}",
    ]
    
    all_results = {
        "human_outbreaks": [],
        "animal_outbreaks": [],
        "zoonotic_outbreaks": [],
        "all_results": []
    }
    
    for query in search_queries:
        print(f"\n--- Executing query: {query} ---")
        results = execute_search(query, num_results=max_results_per_query)
        
        for result in results:
            # Categorize based on content
            content_lower = result['content'].lower()
            title_lower = result['title'].lower()
            
            # Add to all results
            all_results["all_results"].append(result)
            
            # Categorize
            if any(term in content_lower or term in title_lower for term in ['human', 'patient', 'case', 'people']):
                all_results["human_outbreaks"].append(result)
            
            if any(term in content_lower or term in title_lower for term in ['animal', 'livestock', 'cattle', 'poultry', 'wildlife', 'veterinary']):
                all_results["animal_outbreaks"].append(result)
            
            if any(term in content_lower or term in title_lower for term in ['zoonotic', 'zoonosis', 'animal to human', 'spillover']):
                all_results["zoonotic_outbreaks"].append(result)
    
    # Remove duplicates based on URL
    for category in all_results:
        seen_urls = set()
        unique_results = []
        for item in all_results[category]:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_results.append(item)
        all_results[category] = unique_results
    
    return all_results


def extract_outbreak_details(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key details from an outbreak report
    
    Args:
        result: Search result with content
    
    Returns:
        Dictionary with extracted outbreak details
    """
    content = result.get('content', '')
    title = result.get('title', '')
    
    # Extract key information (basic pattern matching)
    details = {
        "title": title,
        "url": result.get('url', ''),
        "source": result.get('source', ''),
        "diseases_mentioned": [],
        "locations_mentioned": [],
        "key_terms": [],
        "summary": content[:500] + "..." if len(content) > 500 else content
    }
    
    # Common disease patterns
    disease_keywords = [
        'influenza', 'flu', 'measles', 'mpox', 'monkeypox', 'ebola', 'dengue',
        'malaria', 'tuberculosis', 'covid', 'coronavirus', 'anthrax', 'rabies',
        'avian', 'h5n1', 'h1n1', 'salmonella', 'e. coli', 'cholera', 'typhoid',
        'yellow fever', 'zika', 'west nile', 'lyme', 'plague', 'marburg'
    ]
    
    content_lower = content.lower()
    for disease in disease_keywords:
        if disease in content_lower:
            details["diseases_mentioned"].append(disease)
    
    # Key terms
    key_terms = ['outbreak', 'epidemic', 'pandemic', 'cases', 'deaths', 'confirmed', 
                 'suspected', 'alert', 'emergency', 'surveillance']
    for term in key_terms:
        if term in content_lower:
            details["key_terms"].append(term)
    
    return details


def generate_summary_report(outbreak_data: Dict[str, List[Dict[str, Any]]], output_file: str = "promed_outbreak_summary.json"):
    """
    Generate a summary report of outbreak data
    
    Args:
        outbreak_data: Dictionary with categorized outbreak data
        output_file: Output file path for JSON report
    """
    print(f"\n{'='*60}")
    print("GENERATING SUMMARY REPORT")
    print(f"{'='*60}\n")
    
    summary = {
        "report_date": datetime.now().isoformat(),
        "date_range": get_date_range(6),
        "statistics": {},
        "outbreaks_by_category": {},
        "detailed_reports": {}
    }
    
    # Statistics
    summary["statistics"] = {
        "total_reports": len(outbreak_data["all_results"]),
        "human_outbreaks": len(outbreak_data["human_outbreaks"]),
        "animal_outbreaks": len(outbreak_data["animal_outbreaks"]),
        "zoonotic_outbreaks": len(outbreak_data["zoonotic_outbreaks"]),
        "unique_urls": len(set(item['url'] for item in outbreak_data["all_results"]))
    }
    
    print("STATISTICS:")
    for key, value in summary["statistics"].items():
        print(f"  {key}: {value}")
    
    # Process each category
    for category in ["human_outbreaks", "animal_outbreaks", "zoonotic_outbreaks"]:
        print(f"\n{category.upper().replace('_', ' ')}:")
        category_details = []
        
        for result in outbreak_data[category][:20]:  # Limit to top 20 per category
            details = extract_outbreak_details(result)
            category_details.append(details)
            print(f"\n  - {details['title'][:80]}...")
            if details['diseases_mentioned']:
                print(f"    Diseases: {', '.join(details['diseases_mentioned'][:5])}")
        
        summary["outbreaks_by_category"][category] = category_details
    
    # Disease frequency analysis
    all_diseases = []
    for category in summary["outbreaks_by_category"].values():
        for report in category:
            all_diseases.extend(report["diseases_mentioned"])
    
    disease_counts = defaultdict(int)
    for disease in all_diseases:
        disease_counts[disease] += 1
    
    summary["most_reported_diseases"] = dict(sorted(disease_counts.items(), 
                                                     key=lambda x: x[1], 
                                                     reverse=True)[:10])
    
    print(f"\nMOST REPORTED DISEASES:")
    for disease, count in summary["most_reported_diseases"].items():
        print(f"  {disease}: {count} reports")
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Report saved to: {output_file}")
    print(f"{'='*60}\n")
    
    return summary


def main():
    """
    Main function to run the ProMED scraper
    """
    print("\n" + "="*60)
    print("ProMED OUTBREAK SCRAPER")
    print("Scraping last 6 months of outbreak data")
    print("="*60 + "\n")
    
    # Check for API key
    if FIRECRAWL_CONFIG["api_key"] == "your-api-key-here":
        print("ERROR: Please set your Firecrawl API key!")
        print("Set the FIRECRAWL_API_KEY environment variable or edit the script.")
        return
    
    try:
        # Search for outbreak data
        outbreak_data = search_promed_outbreaks(months_back=6, max_results_per_query=10)
        
        # Generate summary report
        summary = generate_summary_report(outbreak_data)
        
        print("\n✓ Scraping complete!")
        print(f"✓ Found {summary['statistics']['total_reports']} total reports")
        print(f"✓ Identified {len(summary['most_reported_diseases'])} unique diseases")
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
    except Exception as e:
        print(f"\nError during scraping: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()