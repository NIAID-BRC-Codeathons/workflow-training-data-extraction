#!/usr/bin/env python3
"""
Enhanced ProMED Outbreak Scraper
Advanced version with better date filtering, disease analysis, and reporting
"""

import os
import json
import re
from firecrawl_response_formatter import format_response
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, Counter
import signal

from firecrawl import FirecrawlApp
import dotenv


# get api-key from detenv or error
FIRECRAWL_API_KEY = dotenv.get_key(dotenv.find_dotenv(), "FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise ValueError("FIRECRAWL_API_KEY not set in .env")

# Configuration
FIRECRAWL_CONFIG = {
    "api_key": FIRECRAWL_API_KEY
}

# Global list to track visited URLs
visited_urls = []

# Timeout handler
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


class ProMEDScraper:
    """Enhanced ProMED scraper with better filtering and analysis"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.firecrawl = FirecrawlApp(api_key=api_key)
        self.visited_urls: Set[str] = set()
        self.all_results: List[Dict[str, Any]] = []
        
    def get_date_range(self, months_back: int = 6) -> tuple:
        """Get the date range for filtering"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        return start_date, end_date
    
    def extract_date_from_content(self, content: str, title: str) -> Optional[datetime]:
        """
        Try to extract date from content or title
        Looks for common date patterns in ProMED posts
        """
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # 01 Jan 2025
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',  # Jan 01, 2025
        ]
        
        text_to_search = f"{title} {content[:500]}"
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            if matches:
                try:
                    # Try to parse the first match
                    date_str = matches[0]
                    # Handle different formats
                    for fmt in ['%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except:
                    continue
        
        return None
    
    def is_within_date_range(self, result: Dict[str, Any], start_date: datetime, end_date: datetime) -> bool:
        """Check if a result is within the specified date range"""
        extracted_date = self.extract_date_from_content(
            result.get('content', ''), 
            result.get('title', '')
        )
        
        if extracted_date:
            return start_date <= extracted_date <= end_date
        
        # If we can't determine the date, include it (conservative approach)
        return True
    
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Execute a search query using Firecrawl"""
        print(f"  Searching: {query}")
        
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            search_response = self.firecrawl.search(
                query=query,
                
                    timeout = 30000,
                    limit = num_results,
                    scrape_options = {'formats': ['markdown']}
                
            )
            
            signal.alarm(0)
            

            return format_response(query, search_response)
            
            # Get data items
            if hasattr(search_response, 'data'):
                data_items = search_response.data
            elif isinstance(search_response, dict) and 'data' in search_response:
                data_items = search_response['data']
            else:
                return []
            
            if not data_items:
                return []
            
            # Process results
            formatted_results = []
            for item in data_items:
                url = item.url if hasattr(item, 'url') else item.get('url', '')
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                
                content = item.markdown if hasattr(item, 'markdown') else item.get('markdown', '')
                if not content:
                    content = item.content if hasattr(item, 'content') else item.get('content', '')
                
                title = item.title if hasattr(item, 'title') else item.get('title', url)
                
                formatted_results.append({
                    "title": title,
                    "url": url,
                    "source": url.split("//")[-1].split("/")[0] if "//" in url else "unknown",
                    "snippet": content[:500] + "..." if len(content) > 500 else content,
                    "content": content,
                    "query": query,
                    "scraped_date": datetime.now().isoformat()
                })
                
                self.visited_urls.add(url)
            
            print(f"    Found {len(formatted_results)} new results")
            return formatted_results
            
        except TimeoutError:
            print(f"    Search timed out")
            return []
        except Exception as e:
            print(f"    Error: {e}")
            return []
    
    def scrape_outbreaks(self, months_back: int = 6, max_results_per_query: int = 10) -> Dict[str, Any]:
        """Main scraping function"""
        start_date, end_date = self.get_date_range(months_back)
        print(f"\n{'='*70}")
        print(f"SCRAPING PROMED OUTBREAKS")
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"{'='*70}\n")
        
        current_year = datetime.now().year
        
        # Comprehensive search queries
        search_queries = [
            # Human disease queries
            f"site:promedmail.org human disease outbreak {current_year}",
            f"site:promedmail.org infectious disease human {current_year}",
            f"site:promedmail.org epidemic confirmed cases {current_year}",
            
            # Animal disease queries
            f"site:promedmail.org animal disease outbreak {current_year}",
            f"site:promedmail.org livestock disease {current_year}",
            f"site:promedmail.org avian influenza {current_year}",
            f"site:promedmail.org veterinary alert {current_year}",
            
            # Zoonotic queries
            f"site:promedmail.org zoonotic disease {current_year}",
            f"site:promedmail.org zoonosis outbreak {current_year}",
            
            # General outbreak queries
            f"site:promedmail.org outbreak alert {current_year}",
            f"site:promedmail.org disease surveillance {current_year}",
            f"site:promedmail.org public health emergency {current_year}",
        ]
        
        all_results = []
        
        for i, query in enumerate(search_queries, 1):
            print(f"Query {i}/{len(search_queries)}:")
            results = self.search(query, num_results=max_results_per_query)
            
            # Filter by date
            filtered_results = [
                r for r in results 
                if self.is_within_date_range(r, start_date, end_date)
            ]
            
            all_results.extend(filtered_results)
            print(f"    {len(filtered_results)} results within date range")
        
        print(f"\n{'='*70}")
        print(f"Total unique reports collected: {len(all_results)}")
        print(f"{'='*70}\n")
        
        return self.categorize_and_analyze(all_results)
    
    def categorize_and_analyze(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize results and perform analysis"""
        categorized = {
            "human_outbreaks": [],
            "animal_outbreaks": [],
            "zoonotic_outbreaks": [],
            "potential_outbreaks": [],
            "confirmed_outbreaks": [],
            "all_results": results
        }
        
        for result in results:
            content_lower = result['content'].lower()
            title_lower = result['title'].lower()
            full_text = content_lower + " " + title_lower
            
            # Categorize by type
            if any(term in full_text for term in ['human', 'patient', 'case', 'people', 'person']):
                categorized["human_outbreaks"].append(result)
            
            if any(term in full_text for term in ['animal', 'livestock', 'cattle', 'poultry', 
                                                    'wildlife', 'veterinary', 'avian', 'bird',
                                                    'swine', 'pig', 'horse', 'dog', 'cat']):
                categorized["animal_outbreaks"].append(result)
            
            if any(term in full_text for term in ['zoonotic', 'zoonosis', 'animal to human', 
                                                    'spillover', 'cross-species']):
                categorized["zoonotic_outbreaks"].append(result)
            
            # Categorize by status
            if any(term in full_text for term in ['potential', 'suspected', 'possible', 'unconfirmed']):
                categorized["potential_outbreaks"].append(result)
            
            if any(term in full_text for term in ['confirmed', 'laboratory-confirmed', 'verified']):
                categorized["confirmed_outbreaks"].append(result)
        
        return categorized
    
    def extract_detailed_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed information from a report"""
        content = result.get('content', '')
        title = result.get('title', '')
        
        # Disease detection (expanded list)
        disease_keywords = [
            'influenza', 'flu', 'h5n1', 'h1n1', 'h3n2', 'avian influenza',
            'measles', 'mpox', 'monkeypox', 'ebola', 'marburg',
            'dengue', 'malaria', 'yellow fever', 'zika', 'chikungunya',
            'tuberculosis', 'tb', 'covid', 'coronavirus', 'sars', 'mers',
            'anthrax', 'rabies', 'plague', 'cholera', 'typhoid',
            'salmonella', 'e. coli', 'listeria', 'campylobacter',
            'west nile', 'lyme disease', 'tick-borne',
            'hantavirus', 'lassa fever', 'crimean-congo',
            'rift valley fever', 'african swine fever', 'foot and mouth',
            'brucellosis', 'q fever', 'tularemia'
        ]
        
        # Location patterns
        location_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2,})\b',  # City, STATE/COUNTRY
            r'\b(in|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # in/from Location
        ]
        
        content_lower = content.lower()
        
        # Extract diseases
        diseases_found = [d for d in disease_keywords if d in content_lower]
        
        # Extract locations
        locations_found = []
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            locations_found.extend([m if isinstance(m, str) else ' '.join(m) for m in matches[:5]])
        
        # Extract key metrics
        case_match = re.search(r'(\d+)\s+(?:cases|patients|infections)', content_lower)
        death_match = re.search(r'(\d+)\s+(?:deaths|fatalities|died)', content_lower)
        
        # Severity indicators
        severity_keywords = {
            'high': ['emergency', 'severe', 'critical', 'fatal', 'deaths', 'pandemic'],
            'medium': ['alert', 'outbreak', 'epidemic', 'spreading'],
            'low': ['suspected', 'potential', 'monitoring', 'surveillance']
        }
        
        severity = 'unknown'
        for level, keywords in severity_keywords.items():
            if any(kw in content_lower for kw in keywords):
                severity = level
                break
        
        return {
            "title": title,
            "url": result.get('url', ''),
            "source": result.get('source', ''),
            "diseases_mentioned": diseases_found,
            "locations_mentioned": list(set(locations_found))[:10],
            "cases_reported": case_match.group(1) if case_match else None,
            "deaths_reported": death_match.group(1) if death_match else None,
            "severity": severity,
            "extracted_date": self.extract_date_from_content(content, title),
            "summary": content[:500] + "..." if len(content) > 500 else content
        }
    
    def generate_report(self, categorized_data: Dict[str, Any], output_file: str = "promed_outbreak_report.json"):
        """Generate comprehensive analysis report"""
        print(f"\n{'='*70}")
        print("GENERATING ANALYSIS REPORT")
        print(f"{'='*70}\n")
        
        report = {
            "report_metadata": {
                "generated_date": datetime.now().isoformat(),
                "date_range": {
                    "start": self.get_date_range(6)[0].strftime('%Y-%m-%d'),
                    "end": self.get_date_range(6)[1].strftime('%Y-%m-%d')
                },
                "total_sources_scraped": len(self.visited_urls)
            },
            "statistics": {},
            "detailed_analysis": {},
            "outbreaks_by_category": {}
        }
        
        # Statistics
        report["statistics"] = {
            "total_reports": len(categorized_data["all_results"]),
            "human_outbreaks": len(categorized_data["human_outbreaks"]),
            "animal_outbreaks": len(categorized_data["animal_outbreaks"]),
            "zoonotic_outbreaks": len(categorized_data["zoonotic_outbreaks"]),
            "potential_outbreaks": len(categorized_data["potential_outbreaks"]),
            "confirmed_outbreaks": len(categorized_data["confirmed_outbreaks"]),
        }
        
        print("SUMMARY STATISTICS:")
        for key, value in report["statistics"].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Detailed analysis for each category
        all_diseases = []
        all_locations = []
        severity_counts = Counter()
        
        for category in ["human_outbreaks", "animal_outbreaks", "zoonotic_outbreaks"]:
            print(f"\n{category.upper().replace('_', ' ')}:")
            category_details = []
            
            for result in categorized_data[category]:
                details = self.extract_detailed_info(result)
                category_details.append(details)
                
                all_diseases.extend(details['diseases_mentioned'])
                all_locations.extend(details['locations_mentioned'])
                if details['severity'] != 'unknown':
                    severity_counts[details['severity']] += 1
                
                if len(category_details) <= 5:  # Print first 5
                    print(f"  • {details['title'][:70]}...")
                    if details['diseases_mentioned']:
                        print(f"    Diseases: {', '.join(details['diseases_mentioned'][:3])}")
                    if details['cases_reported']:
                        print(f"    Cases: {details['cases_reported']}")
            
            report["outbreaks_by_category"][category] = category_details
        
        # Disease frequency analysis
        disease_counts = Counter(all_diseases)
        report["detailed_analysis"]["most_reported_diseases"] = dict(disease_counts.most_common(15))
        
        # Location analysis
        location_counts = Counter(all_locations)
        report["detailed_analysis"]["most_affected_locations"] = dict(location_counts.most_common(15))
        
        # Severity distribution
        report["detailed_analysis"]["severity_distribution"] = dict(severity_counts)
        
        print(f"\nMOST REPORTED DISEASES:")
        for disease, count in list(disease_counts.most_common(10)):
            print(f"  {disease}: {count} reports")
        
        print(f"\nSEVERITY DISTRIBUTION:")
        for severity, count in severity_counts.items():
            print(f"  {severity.upper()}: {count} reports")
        
        # Save report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n{'='*70}")
        print(f"✓ Report saved to: {output_file}")
        print(f"{'='*70}\n")
        
        return report


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("ENHANCED PROMED OUTBREAK SCRAPER")
    print("="*70 + "\n")
    
    # Check API key
    api_key = FIRECRAWL_CONFIG["api_key"]
    if api_key == "your-api-key-here":
        print("❌ ERROR: Firecrawl API key not set!")
        print("Set FIRECRAWL_API_KEY environment variable or edit the script.")
        return
    
    try:
        # Initialize scraper
        scraper = ProMEDScraper(api_key)
        
        # Scrape outbreaks
        categorized_data = scraper.scrape_outbreaks(months_back=6, max_results_per_query=10)
        
        # Generate report
        report = scraper.generate_report(categorized_data)
        
        print("\n✓ Scraping and analysis complete!")
        print(f"✓ Total reports: {report['statistics']['total_reports']}")
        print(f"✓ Unique diseases identified: {len(report['detailed_analysis']['most_reported_diseases'])}")
        print(f"✓ Unique locations: {len(report['detailed_analysis']['most_affected_locations'])}")
        
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()