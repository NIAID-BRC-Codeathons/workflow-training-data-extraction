#!/usr/bin/env python3
"""
Outbreak Flagger using ARGO LLM
Analyzes outbreak catalog and uses LLM to generate a comprehensive outbreak report
"""

import sys
import os
import csv
from datetime import datetime

# Add scripts directory to path to import ARGO
sys.path.append('scripts')
from ARGO import ArgoWrapper

class OutbreakFlaggerARGO:
    def __init__(self, catalog_path="outbreak_data/catalog.csv"):
        self.catalog_path = catalog_path
        self.argo = ArgoWrapper(model="gpt4o")
        self.catalog_data = []
        
    def read_catalog(self):
        """Read the catalog CSV file"""
        print("Reading catalog...")
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('filename') and row.get('description'):
                    # Skip test files and empty descriptions
                    if not row['filename'].startswith('test_') and 'no entries' not in row['description'].lower():
                        self.catalog_data.append(row)
        print(f"Found {len(self.catalog_data)} valid catalog entries")
        return self.catalog_data
    
    def generate_report_with_llm(self):
        """Use ARGO LLM to generate the complete markdown report"""
        print("Generating comprehensive outbreak report with LLM...")
        
        # Prepare the catalog data for the LLM
        catalog_entries = []
        for i, entry in enumerate(self.catalog_data, 1):
            catalog_entries.append(f"Entry {i}:\nFile: {entry['filename']}\nDescription: {entry['description']}")
        
        catalog_text = "\n\n".join(catalog_entries)
        
        # System prompt
        system_prompt = """You are an expert epidemiologist and outbreak analyst tasked with creating a comprehensive outbreak analysis report. You will analyze outbreak data catalog entries and produce a detailed markdown report identifying potential disease outbreaks.

Your report should be professional, thorough, and actionable for public health officials. Consider factors like geographic spread, case counts, mortality rates, vaccination status, emergence of variants, and unusual disease patterns.

Prioritize outbreaks by risk level based on:
- Severity (mortality, hospitalizations)
- Spread potential (geographic distribution, transmission rate)
- Public health impact (vulnerable populations, healthcare capacity)
- Novel or concerning characteristics"""

        # User prompt
        user_prompt = f"""Analyze the following outbreak data catalog with {len(self.catalog_data)} entries and generate a comprehensive markdown report identifying all potential outbreaks that require investigation.

CATALOG DATA:
{catalog_text}

Generate a complete markdown report with the following structure:

# Potential Outbreak Analysis Report

Include:
- Header with generation date ({datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}) and metadata
- Executive summary
- Detailed analysis of each identified outbreak including:
  - Location, Date, Disease
  - Supporting data from the catalog
  - Epidemiological hypotheses explaining the outbreak
  - Specific URLs to crawl for verification and monitoring
- Risk assessment and prioritization
- Geographic distribution analysis
- Trend analysis and patterns
- Recommendations for immediate action
- Data gaps and limitations

For each outbreak, provide:
1. Clear identification (disease, location, timeframe)
2. All relevant data points from the descriptions
3. 3-5 hypotheses explaining the outbreak
4. 5-10 specific URLs for investigation including:
   - CDC/WHO disease-specific pages
   - ProMED searches
   - Local health department sites
   - News searches
   - Academic/research resources

Conclude with actionable next steps and recommendations.

Make the report comprehensive, well-structured, and ready for immediate use by outbreak response teams."""

        try:
            # Call ARGO LLM to generate the complete report
            response = self.argo.invoke(
                prompt_system=system_prompt,
                prompt_user=user_prompt,
                temperature=0.1,  # Low temperature for factual, consistent output
                top_p=0.95
            )
            
            if response and 'response' in response:
                return response['response']
            else:
                print("Error: Invalid response from ARGO")
                return None
                
        except Exception as e:
            print(f"Error calling ARGO: {e}")
            return None
    
    def save_report(self, report_content):
        """Save the generated report to file"""
        if not report_content:
            print("No report content to save")
            return False
            
        output_file = "potential_outbreaks.md"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Report successfully saved to: {output_file}")
            return True
        except Exception as e:
            print(f"Error saving report: {e}")
            return False
    
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("OUTBREAK FLAGGER - ARGO LLM Analysis")
        print("=" * 60)
        
        # Read catalog
        self.read_catalog()
        
        if not self.catalog_data:
            print("No valid catalog entries found")
            return
        
        # Generate report with LLM
        report = self.generate_report_with_llm()
        
        if report:
            # Save the report
            if self.save_report(report):
                print("\n" + "=" * 60)
                print("Analysis complete!")
                print("Report saved to: potential_outbreaks.md")
                print("=" * 60)
                
                # Print summary statistics
                print(f"\nSummary:")
                print(f"- Catalog entries analyzed: {len(self.catalog_data)}")
                print(f"- Report generated: potential_outbreaks.md")
                print(f"- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("Failed to generate report")


def main():
    flagger = OutbreakFlaggerARGO()
    flagger.run()


if __name__ == "__main__":
    main()