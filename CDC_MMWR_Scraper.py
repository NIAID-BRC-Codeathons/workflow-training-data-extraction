#!/usr/bin/env python3
"""
CDC MMWR Scraper
Scrapes data from the CDC Morbidity and Mortality Weekly Report (MMWR) website
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import subprocess
import sys

# Ensure beautifulsoup4 is installed
try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

import requests

class CDCMMWRScraper:
    """Scraper for CDC MMWR reports"""

    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.all_results: List[Dict[str, Any]] = []

    def get_date_range(self, months_back: int = 6) -> tuple:
        """Get the date range for filtering"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        return start_date, end_date

    def fetch_report(self, url: str) -> Optional[str]:
        """Fetch the report content from a given URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to fetch {url}: Status code {response.status_code}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    def parse_report(self, html_content: str) -> Dict[str, Any]:
        """Parse the HTML content of a report"""
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.find('title').get_text(strip=True)
        content = soup.get_text(separator=' ', strip=True)
        return {
            "title": title,
            "content": content,
            "scraped_date": datetime.now().isoformat()
        }

    def scrape_reports(self, months_back: int = 6) -> List[Dict[str, Any]]:
        """Main scraping function"""
        start_date, end_date = self.get_date_range(months_back)
        print(f"Scraping CDC MMWR reports from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Example URLs for 2025 reports
        report_urls = [
            "https://www.cdc.gov/mmwr/volumes/74/wr/mm7401a1.htm",
            "https://www.cdc.gov/mmwr/volumes/74/wr/mm7402a1.htm"
        ]

        for url in report_urls:
            if url in self.visited_urls:
                continue

            html_content = self.fetch_report(url)
            if html_content:
                report_data = self.parse_report(html_content)
                self.all_results.append(report_data)
                self.visited_urls.add(url)

        return self.all_results

    def generate_report(self, output_file: str = "cdc_mmwr_report.json"):
        """Generate a report from the scraped data"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {output_file}")

def main():
    """Main execution function"""
    scraper = CDCMMWRScraper()
    scraper.scrape_reports()
    scraper.generate_report()

if __name__ == "__main__":
    main()