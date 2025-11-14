#!/usr/bin/env python3
"""
Data Gatherer Agent
Reads the devil's advocate analysis report and generates a list of Firecrawl searches 
and URLs to scrape for validating hypotheses.
"""

import sys
import os
from datetime import datetime

# Add scripts directory to path to import ARGO
sys.path.append('scripts')
from ARGO import ArgoWrapper


class DataGathererAgent:
    def __init__(self, analysis_path="devils_advocate_analysis.md"):
        self.analysis_path = analysis_path
        self.argo = ArgoWrapper(model="gpt4o")
        
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("DATA GATHERER AGENT")
        print("Generating Firecrawl Searches and URLs for Hypothesis Validation")
        print("=" * 60)
        
        # Read the devil's advocate analysis
        print(f"Reading devil's advocate analysis from: {self.analysis_path}")
        try:
            with open(self.analysis_path, 'r', encoding='utf-8') as f:
                analysis_content = f.read()
            print("Successfully read analysis report")
        except Exception as e:
            print(f"Error reading analysis: {e}")
            return
        
        # System prompt for data gathering
        system_prompt = """You are a data gathering specialist tasked with creating comprehensive Firecrawl search queries and URL lists to validate outbreak hypotheses. Your role is to:

1. Analyze the devil's advocate report and its alternative hypotheses
2. Generate specific Firecrawl search queries to gather validation data
3. Identify authoritative URLs that should be scraped for evidence
4. Ensure data collection covers both original and alternative hypotheses

Focus on gathering data that can:
- Validate or refute outbreak claims
- Test alternative explanations
- Provide baseline comparisons
- Reveal reporting biases or data artifacts
- Confirm laboratory results and testing protocols
- Track media coverage timelines
- Verify official health statistics

Prioritize authoritative sources:
- CDC, WHO, and national health agencies
- ProMED and HealthMap
- Academic journals and preprint servers
- Official government health departments
- Laboratory and research institution reports
- Epidemiological surveillance databases"""

        # User prompt with the analysis
        user_prompt = f"""Based on this devil's advocate analysis, generate comprehensive Firecrawl searches and URLs to gather data for hypothesis validation.

DEVIL'S ADVOCATE ANALYSIS:
{analysis_content}

Generate a structured data gathering plan in the following JSON format:

```json
{{
  "metadata": {{
    "generated": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "purpose": "Hypothesis validation data gathering",
    "source_analysis": "{self.analysis_path}"
  }},
  "firecrawl_searches": [
    {{
      "outbreak": "Outbreak name/disease",
      "search_queries": [
        {{
          "query": "Specific search query text",
          "purpose": "What hypothesis this validates",
          "expected_data": "What information we expect to find",
          "priority": "high/medium/low"
        }}
      ]
    }}
  ],
  "urls_to_scrape": [
    {{
      "outbreak": "Outbreak name/disease",
      "urls": [
        {{
          "url": "Full URL to scrape",
          "source_type": "CDC/WHO/ProMED/News/Academic/Government",
          "data_type": "What specific data this provides",
          "validates": "Which hypothesis this helps validate",
          "scraping_notes": "Any special considerations for scraping"
        }}
      ]
    }}
  ],
  "validation_data_requirements": {{
    "baseline_data": [
      "List of baseline/historical data needed for comparison"
    ],
    "control_data": [
      "List of control population or region data needed"
    ],
    "temporal_data": [
      "Time-series data requirements"
    ],
    "laboratory_data": [
      "Testing and diagnostic data requirements"
    ]
  }},
  "scraping_strategy": {{
    "priority_order": [
      "Ordered list of which sources to scrape first"
    ],
    "frequency": "How often to re-scrape for updates",
    "depth": "How deep to crawl linked pages",
    "filters": "Any content filters to apply"
  }}
}}
```

For each outbreak mentioned in the analysis:

1. **Search Queries** (5-10 per outbreak):
   - Queries to find outbreak confirmation/refutation
   - Queries to test alternative hypotheses
   - Queries for baseline and historical data
   - Queries for control regions/populations
   - Include location, date ranges, and specific terms

2. **URLs to Scrape** (10-15 per outbreak):
   - Official health agency pages (CDC, WHO, local health departments)
   - ProMED outbreak reports
   - Academic publications and preprints
   - Laboratory and testing facility reports
   - News aggregators for media timeline analysis
   - Government statistics databases
   - Environmental and demographic data sources

3. **Validation Requirements**:
   - Specify exact data types needed
   - Define comparison metrics
   - List control data sources

Make the output immediately actionable for Firecrawl implementation."""

        print("Generating data gathering plan with ARGO...")
        
        try:
            # Call ARGO LLM to generate data gathering plan
            response = self.argo.invoke(
                prompt_system=system_prompt,
                prompt_user=user_prompt,
                temperature=0.2,  # Low temperature for consistent, structured output
                top_p=0.95
            )
            
            if response and 'response' in response:
                gathering_plan = response['response']
                
                # Save the data gathering plan
                output_file = "data_gathering_plan.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(gathering_plan)
                
                print(f"\nData gathering plan saved to: {output_file}")
                
                # Also save as markdown for readability
                md_output_file = "data_gathering_plan.md"
                md_content = f"""# Data Gathering Plan for Hypothesis Validation

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Source Analysis:** {self.analysis_path}

## Firecrawl Implementation Plan

{gathering_plan}

## Implementation Instructions

1. **Firecrawl Setup**:
   - Configure Firecrawl with the search queries from this plan
   - Set appropriate rate limits for each domain
   - Enable JavaScript rendering for dynamic content

2. **Execution Priority**:
   - Start with high-priority searches
   - Scrape official health agency URLs first
   - Follow with academic and news sources

3. **Data Processing**:
   - Extract structured data from scraped content
   - Compare with baseline data
   - Look for patterns that support or refute hypotheses

4. **Validation Criteria**:
   - Document which hypotheses are supported/refuted by each data source
   - Track data quality and reliability scores
   - Note any conflicting information between sources
"""
                
                with open(md_output_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                print(f"Markdown version saved to: {md_output_file}")
                
                print("\n" + "=" * 60)
                print("Data Gathering Plan Complete!")
                print("=" * 60)
                print(f"\nNext Steps:")
                print(f"1. Review the data gathering plan in {output_file}")
                print(f"2. Configure Firecrawl with the search queries")
                print(f"3. Execute URL scraping in priority order")
                print(f"4. Process gathered data to validate hypotheses")
                
            else:
                print("Error: Invalid response from ARGO")
                
        except Exception as e:
            print(f"Error calling ARGO: {e}")


def main():
    # Check if a custom analysis path is provided
    analysis_path = "devils_advocate_analysis.md"
    if len(sys.argv) > 1:
        analysis_path = sys.argv[1]
    
    agent = DataGathererAgent(analysis_path=analysis_path)
    agent.run()


if __name__ == "__main__":
    main()