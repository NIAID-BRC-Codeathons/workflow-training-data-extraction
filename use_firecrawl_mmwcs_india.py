import os
import json
from dotenv import load_dotenv
from firecrawl import Firecrawl
from datetime import datetime
from collections import Counter

# Call .env to get API key
load_dotenv()
firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Use Firecrawl to crawl the website and find PDF links
crawl_results = firecrawl.crawl(
    url="https://idsp.mohfw.gov.in/index4.php?lang=1&level=0&linkid=406&lid=3689"
)

# Extract data from the found PDF URLs
pdf_urls = [result['url'] for result in crawl_results if 'url' in result]
res = firecrawl.extract(
    urls=pdf_urls,
    prompt="Go through each page of the PDF and extract the disease risk, date identified, location, week, and number of cases",
)

# Function to categorize and analyze extracted data
def categorize_and_analyze(data):
    categorized = {
        "disease_risks": [],
        "locations": [],
        "dates_identified": [],
        "weeks": [],
        "cases": []
    }
    
    for item in data:
        # Assuming each item in the tuple is a dictionary
        if isinstance(item, dict):
            categorized["disease_risks"].append(item.get("disease_risk", "unknown"))
            categorized["locations"].append(item.get("location", "unknown"))
            categorized["dates_identified"].append(item.get("date_identified", "unknown"))
            categorized["weeks"].append(item.get("week", "unknown"))
            categorized["cases"].append(item.get("cases", 0))
    
    return categorized

# Function to generate JSON report
def generate_json_report(categorized_data, output_file="mmwcs_india_report.json"):
    report = {
        "report_metadata": {
            "generated_date": datetime.now().isoformat(),
            "total_entries": len(categorized_data["disease_risks"])
        },
        "statistics": {
            "disease_risks_count": Counter(categorized_data["disease_risks"]),
            "locations_count": Counter(categorized_data["locations"]),
            "weeks_count": Counter(categorized_data["weeks"])
        },
        "detailed_entries": categorized_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Report saved to: {output_file}")

# Categorize and analyze the extracted data
categorized_data = categorize_and_analyze(res)

# Generate and save the JSON report
generate_json_report(categorized_data)

# Print the extracted data
print(res)