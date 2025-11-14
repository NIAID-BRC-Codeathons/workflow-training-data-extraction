#!/usr/bin/env python3
"""
Firecrawl Validation Agent
Reads the data gathering plan JSON and executes Firecrawl searches and crawls
to collect validation data for outbreak hypotheses.
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import dotenv
from firecrawl import FirecrawlApp
from firecrawl_response_formatter import format_response
from data_repository_writer import write_to_repository

# Get API key from .env
FIRECRAWL_API_KEY = dotenv.get_key(dotenv.find_dotenv(), "FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise ValueError("FIRECRAWL_API_KEY not set in .env")


class FirecrawlValidationAgent:
    def __init__(self, plan_path="data_gathering_plan.json"):
        self.plan_path = plan_path
        self.firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        self.results = {
            "metadata": {
                "execution_start": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                "plan_source": plan_path
            },
            "search_results": [],
            "crawl_results": [],
            "validation_data": {}
        }
        self.search_count = 0
        self.url_count = 0
        
    def load_plan(self) -> Dict[str, Any]:
        """Load the data gathering plan from JSON"""
        print(f"Loading data gathering plan from: {self.plan_path}")
        try:
            with open(self.plan_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    json_content = content[start:end].strip()
                else:
                    json_content = content
                
                plan = json.loads(json_content)
                print(f"Successfully loaded plan with {len(plan.get('firecrawl_searches', []))} search groups")
                return plan
        except Exception as e:
            print(f"Error loading plan: {e}")
            return {}
    
    def execute_search(self, query: str, purpose: str = "", num_results: int = 5) -> List[Dict[str, Any]]:
        """Execute a search query using Firecrawl"""
        self.search_count += 1
        print(f"\n🔍 Search #{self.search_count}: {query[:80]}...")
        if purpose:
            print(f"   Purpose: {purpose}")
        
        try:
            print(f"   ⏳ Executing Firecrawl search...")
            start_time = time.time()
            
            # Execute search with Firecrawl
            search_response = self.firecrawl_app.search(
                query=query,
                timeout=30000,
                limit=num_results,
                scrape_options={'formats': ['markdown']}
            )
            
            elapsed = time.time() - start_time
            print(f"   ⏱️  Search completed in {elapsed:.2f} seconds")
            
            # Format results
            formatted_results = format_response(query, search_response)
            
            print(f"   ✅ Found {len(formatted_results)} results")
            
            # Write to repository immediately
            print(f"   💾 Saving to repository...")
            write_to_repository(formatted_results)
            
            # Save intermediate search results
            self.save_intermediate_results()
            
            return formatted_results
            
        except Exception as e:
            print(f"   ❌ Error searching: {e}")
            return []
    
    def crawl_url(self, url: str, data_type: str = "", max_depth: int = 2) -> Dict[str, Any]:
        """Crawl a specific URL using Firecrawl's crawl function"""
        self.url_count += 1
        print(f"\n🕷️ URL #{self.url_count} - Crawling: {url[:80]}...")
        if data_type:
            print(f"   Data type: {data_type}")
        print(f"   Max depth: {max_depth}")
        
        try:
            # Use Firecrawl's crawl function for deeper exploration
            crawl_response = self.firecrawl_app.crawl_url(
                url=url,
                params={
                    'crawlerOptions': {
                        'maxDepth': max_depth,
                        'limit': 10,  # Limit pages per crawl
                        'excludes': ['*.pdf', '*.jpg', '*.png', '*.gif'],
                        'includes': ['*outbreak*', '*disease*', '*health*', '*cases*', '*surveillance*']
                    },
                    'pageOptions': {
                        'onlyMainContent': True,
                        'includeHtml': False
                    },
                    'timeout': 60000
                }
            )
            
            # Check if crawl was successful
            if crawl_response and 'success' in crawl_response:
                if crawl_response['success']:
                    crawl_id = crawl_response.get('id')
                    print(f"   ⏳ Crawl initiated with ID: {crawl_id}")
                    
                    # Wait for crawl to complete (with timeout)
                    max_wait = 120  # 2 minutes max
                    wait_interval = 5
                    elapsed = 0
                    
                    while elapsed < max_wait:
                        time.sleep(wait_interval)
                        elapsed += wait_interval
                        
                        # Check crawl status
                        status = self.firecrawl_app.check_crawl_status(crawl_id)
                        
                        if status.get('status') == 'completed':
                            print(f"   ✅ Crawl completed")
                            
                            # Get crawled data
                            crawl_data = {
                                'url': url,
                                'data_type': data_type,
                                'crawl_id': crawl_id,
                                'pages_crawled': status.get('total', 0),
                                'data': status.get('data', []),
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                            }
                            
                            # Write to repository
                            if crawl_data['data']:
                                write_to_repository(crawl_data['data'])
                            
                            return crawl_data
                        
                        elif status.get('status') == 'failed':
                            print(f"   ❌ Crawl failed: {status.get('error', 'Unknown error')}")
                            break
                        
                        else:
                            print(f"   ⏳ Status: {status.get('status', 'checking')} ({elapsed}s elapsed)")
                    
                    if elapsed >= max_wait:
                        print(f"   ⚠️ Crawl timeout after {max_wait} seconds")
            
            # If crawl fails, fall back to single page scrape
            print(f"   ↩️ Falling back to single page scrape")
            return self.scrape_single_url(url, data_type)
            
        except Exception as e:
            print(f"   ❌ Error crawling: {e}")
            # Fall back to single page scrape
            return self.scrape_single_url(url, data_type)
    
    def scrape_single_url(self, url: str, data_type: str = "") -> Dict[str, Any]:
        """Scrape a single URL using Firecrawl"""
        try:
            print(f"   📄 Scraping single page...")
            start_time = time.time()
            # Scrape single page
            scrape_response = self.firecrawl_app.scrape_url(
                url=url,
                params={
                    'pageOptions': {
                        'onlyMainContent': True,
                        'includeHtml': False
                    },
                    'timeout': 30000
                }
            )
            
            if scrape_response and 'success' in scrape_response and scrape_response['success']:
                elapsed = time.time() - start_time
                print(f"   ✅ Single page scraped successfully in {elapsed:.2f} seconds")
                
                result = {
                    'url': url,
                    'data_type': data_type,
                    'content': scrape_response.get('markdown', ''),
                    'metadata': scrape_response.get('metadata', {}),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                }
                
                # Write to repository
                print(f"   💾 Saving to repository...")
                write_to_repository([result])
                
                # Save intermediate results
                self.save_intermediate_results()
                
                return result
            else:
                print(f"   ❌ Failed to scrape page")
                return {}
                
        except Exception as e:
            print(f"   ❌ Error scraping single page: {e}")
            return {}
    
    def save_intermediate_results(self):
        """Save intermediate results after each operation"""
        try:
            # Save current results to a temporary file
            temp_file = f"validation_results_temp_{self.search_count + self.url_count}.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
            print(f"   📝 Intermediate results saved to {temp_file}")
        except Exception as e:
            print(f"   ⚠️ Could not save intermediate results: {e}")
    
    def process_searches(self, plan: Dict[str, Any]):
        """Process all search queries from the plan"""
        searches = plan.get('firecrawl_searches', [])
        
        total_queries = sum(len(sg.get('search_queries', [])) for sg in searches)
        print(f"\n{'='*60}")
        print(f"EXECUTING SEARCH QUERIES")
        print(f"Total queries to execute: {total_queries}")
        print(f"{'='*60}")
        
        for search_group in searches:
            outbreak = search_group.get('outbreak', 'Unknown')
            queries = search_group.get('search_queries', [])
            
            print(f"\n📌 Outbreak: {outbreak}")
            print(f"   Queries to execute: {len(queries)}")
            print(f"   Progress: {self.search_count}/{total_queries} searches completed")
            
            group_results = {
                'outbreak': outbreak,
                'queries': []
            }
            
            for query_info in queries:
                query = query_info.get('query', '')
                purpose = query_info.get('purpose', '')
                priority = query_info.get('priority', 'medium')
                
                # Skip low priority queries if we have many
                if priority == 'low' and len(queries) > 10:
                    print(f"   ⏭️ Skipping low priority query: {query[:50]}...")
                    continue
                
                # Execute search
                results = self.execute_search(query, purpose, num_results=5)
                
                group_results['queries'].append({
                    'query': query,
                    'purpose': purpose,
                    'priority': priority,
                    'results_count': len(results),
                    'results': results[:3]  # Store first 3 results
                })
                
                # Rate limiting
                time.sleep(2)
            
            self.results['search_results'].append(group_results)
    
    def process_urls(self, plan: Dict[str, Any]):
        """Process URLs to crawl from the plan"""
        url_groups = plan.get('urls_to_scrape', [])
        
        total_urls = sum(len(ug.get('urls', [])) for ug in url_groups)
        print(f"\n{'='*60}")
        print(f"CRAWLING URLS")
        print(f"Total URLs to process: {total_urls}")
        print(f"{'='*60}")
        
        for url_group in url_groups:
            outbreak = url_group.get('outbreak', 'Unknown')
            urls = url_group.get('urls', [])
            
            print(f"\n📌 Outbreak: {outbreak}")
            print(f"   URLs to crawl: {len(urls)}")
            print(f"   Progress: {self.url_count}/{total_urls} URLs processed")
            
            group_results = {
                'outbreak': outbreak,
                'urls': []
            }
            
            for url_info in urls:
                url = url_info.get('url', '')
                source_type = url_info.get('source_type', '')
                data_type = url_info.get('data_type', '')
                validates = url_info.get('validates', '')
                
                # Determine if we should do deep crawl based on source type
                use_deep_crawl = source_type in ['CDC', 'WHO', 'Government']
                max_depth = 3 if use_deep_crawl else 1
                
                print(f"\n   📍 Processing URL {self.url_count + 1}/{total_urls}")
                print(f"   Source: {source_type}")
                print(f"   Validates: {validates}")
                
                # Crawl or scrape based on configuration
                if use_deep_crawl:
                    result = self.crawl_url(url, data_type, max_depth)
                else:
                    result = self.scrape_single_url(url, data_type)
                
                if result:
                    group_results['urls'].append({
                        'url': url,
                        'source_type': source_type,
                        'data_type': data_type,
                        'validates': validates,
                        'success': True,
                        'pages_crawled': result.get('pages_crawled', 1)
                    })
                else:
                    group_results['urls'].append({
                        'url': url,
                        'source_type': source_type,
                        'success': False
                    })
                
                # Rate limiting
                time.sleep(3)
            
            self.results['crawl_results'].append(group_results)
    
    def save_results(self):
        """Save all results to files"""
        # Add completion metadata
        self.results['metadata']['execution_end'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Calculate statistics
        total_searches = sum(len(g['queries']) for g in self.results['search_results'])
        total_urls = sum(len(g['urls']) for g in self.results['crawl_results'])
        successful_urls = sum(
            sum(1 for u in g['urls'] if u.get('success', False)) 
            for g in self.results['crawl_results']
        )
        
        self.results['statistics'] = {
            'total_searches_executed': total_searches,
            'total_urls_processed': total_urls,
            'successful_urls': successful_urls,
            'success_rate': f"{(successful_urls/total_urls*100):.1f}%" if total_urls > 0 else "0%"
        }
        
        # Save JSON results
        output_file = "validation_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a markdown summary report"""
        report = f"""# Firecrawl Validation Results

**Generated:** {self.results['metadata']['execution_end']}
**Plan Source:** {self.results['metadata']['plan_source']}

## Execution Statistics

- **Total Searches Executed:** {self.results['statistics']['total_searches_executed']}
- **Total URLs Processed:** {self.results['statistics']['total_urls_processed']}
- **Successful URLs:** {self.results['statistics']['successful_urls']}
- **Success Rate:** {self.results['statistics']['success_rate']}

## Search Results by Outbreak

"""
        
        for group in self.results['search_results']:
            report += f"\n### {group['outbreak']}\n\n"
            report += f"Executed {len(group['queries'])} search queries:\n\n"
            
            for query in group['queries'][:5]:  # Show first 5
                report += f"- **Query:** {query['query'][:100]}...\n"
                report += f"  - Purpose: {query['purpose']}\n"
                report += f"  - Results: {query['results_count']} found\n\n"
        
        report += "\n## Crawl Results by Outbreak\n"
        
        for group in self.results['crawl_results']:
            report += f"\n### {group['outbreak']}\n\n"
            successful = sum(1 for u in group['urls'] if u.get('success', False))
            report += f"Processed {len(group['urls'])} URLs ({successful} successful):\n\n"
            
            for url_result in group['urls'][:5]:  # Show first 5
                status = "✅" if url_result.get('success') else "❌"
                report += f"- {status} {url_result.get('source_type', 'Unknown')}: {url_result['url'][:80]}...\n"
                if url_result.get('validates'):
                    report += f"  - Validates: {url_result['validates']}\n"
        
        report += """

## Next Steps

1. Review collected data in the outbreak_data directory
2. Analyze content for hypothesis validation
3. Compare findings across sources
4. Update outbreak assessments based on evidence
5. Generate final validation report

## Data Location

All scraped and crawled data has been saved to the `outbreak_data/` directory with timestamps.
"""
        
        # Save report
        with open("validation_summary.md", 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 Summary report saved to: validation_summary.md")
    
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("FIRECRAWL VALIDATION AGENT")
        print("Executing Data Collection for Hypothesis Validation")
        print("=" * 60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Load the plan
        plan = self.load_plan()
        if not plan:
            print("Failed to load data gathering plan")
            return
        
        # Process searches
        if 'firecrawl_searches' in plan:
            self.process_searches(plan)
        else:
            print("No search queries found in plan")
        
        # Process URLs
        if 'urls_to_scrape' in plan:
            self.process_urls(plan)
        else:
            print("No URLs found in plan")
        
        # Save results
        self.save_results()
        
        print("\n" + "=" * 60)
        print("VALIDATION DATA COLLECTION COMPLETE")
        print("=" * 60)
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"\nTotal operations:")
        print(f"  - Searches executed: {self.search_count}")
        print(f"  - URLs processed: {self.url_count}")
        print(f"\nResults saved to:")
        print(f"  - validation_results.json (detailed results)")
        print(f"  - validation_summary.md (summary report)")
        print(f"  - outbreak_data/ (all scraped content)")
        print(f"  - validation_results_temp_*.json (intermediate results)")


def main():
    # Check if a custom plan path is provided
    plan_path = "data_gathering_plan.json"
    if len(sys.argv) > 1:
        plan_path = sys.argv[1]
    
    agent = FirecrawlValidationAgent(plan_path=plan_path)
    agent.run()


if __name__ == "__main__":
    main()