#!/usr/bin/env python3
"""
Process outbreak data files and adjust knowledge using ArgoClient.
Reads files from outbreak_data directory using catalog.csv and ranks them by relevance.
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from ARGO import ArgoWrapper

class OutbreakDataProcessor:
    """Process outbreak data files and analyze them using LLM."""
    
    def __init__(self, catalog_path: str = "outbreak_data/catalog.csv", 
                 data_dir: str = "outbreak_data",
                 initial_prompt_path: str = "scripts/initial_prompt.md"):
        """
        Initialize the processor.
        
        Args:
            catalog_path: Path to the catalog CSV file
            data_dir: Directory containing the data files
            initial_prompt_path: Path to the initial prompt markdown file
        """
        self.catalog_path = Path(catalog_path)
        self.data_dir = Path(data_dir)
        self.initial_prompt_path = Path(initial_prompt_path)
        
        # Initialize ArgoWrapper
        self.argo = ArgoWrapper(model="gpt4o", user="outbreak_processor")
        
        # Load initial prompt for context
        self.initial_context = self._load_initial_prompt()
        
        # Store analysis results
        self.analysis_results = []
        
    def _load_initial_prompt(self) -> str:
        """Load the initial prompt from markdown file."""
        try:
            with open(self.initial_prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Initial prompt file not found at {self.initial_prompt_path}")
            return ""
    
    def load_catalog(self) -> List[Dict[str, str]]:
        """Load the catalog of data files."""
        catalog_entries = []
        
        if not self.catalog_path.exists():
            print(f"Error: Catalog file not found at {self.catalog_path}")
            return catalog_entries
        
        with open(self.catalog_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['filename']:  # Only add entries with filenames
                    catalog_entries.append({
                        'filename': row['filename'],
                        'description': row.get('description', '')
                    })
        
        return catalog_entries
    
    def load_data_file(self, filename: str) -> Any:
        """Load a data file from the outbreak_data directory."""
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            print(f"Warning: File {filename} not found in {self.data_dir}")
            return None
        
        # Determine file type and load accordingly
        if filename.endswith('.json'):
            with open(file_path, 'r') as f:
                return json.load(f)
        elif filename.endswith('.csv'):
            data = []
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data
        elif filename.endswith('.txt'):
            with open(file_path, 'r') as f:
                return f.read()
        else:
            # Try to read as text
            try:
                with open(file_path, 'r') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                return None
    
    def analyze_outbreak_data(self, data: Any, filename: str, description: str) -> Dict[str, Any]:
        """
        Analyze outbreak data using the LLM.
        
        Args:
            data: The loaded data
            filename: Name of the file
            description: Description from catalog
            
        Returns:
            Analysis results including relevance score and insights
        """
        # Prepare the system prompt with outbreak context
        system_prompt = f"""You are an epidemiologist analyzing outbreak data. 
        
Context about outbreak definitions:
{self.initial_context[:2000]}  # Use first 2000 chars to avoid token limits

Your task is to:
1. Analyze the provided data for outbreak indicators
2. Identify key patterns, trends, and anomalies
3. Rank the relevance of this data for outbreak detection (0-10 scale)
4. Provide actionable insights
5. Identify any urgent concerns

Respond in JSON format with the following structure:
{{
    "relevance_score": <0-10>,
    "outbreak_indicators": ["list of identified indicators"],
    "key_patterns": ["list of patterns found"],
    "urgent_concerns": ["list of urgent items if any"],
    "summary": "brief summary of findings",
    "recommendations": ["list of recommended actions"]
}}"""

        # Prepare user prompt with data
        data_str = str(data)
        if len(data_str) > 5000:  # Truncate if too long
            data_str = data_str[:5000] + "... [truncated]"
        
        user_prompt = f"""Analyze this outbreak data:

Filename: {filename}
Description: {description}

Data:
{data_str}

Please provide your analysis in the specified JSON format."""

        try:
            # Call the LLM
            response = self.argo.invoke(
                prompt_system=system_prompt,
                prompt_user=user_prompt,
                temperature=0.1,  # Low temperature for consistent analysis
                top_p=0.95
            )
            
            # Extract the response text
            if isinstance(response, dict) and 'response' in response:
                response_text = response['response']
            else:
                response_text = str(response)
            
            # Try to parse JSON from response
            try:
                # Find JSON in the response (it might be wrapped in markdown)
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Fallback: create a basic analysis
                    analysis = {
                        "relevance_score": 5,
                        "outbreak_indicators": ["Unable to parse LLM response"],
                        "key_patterns": [],
                        "urgent_concerns": [],
                        "summary": response_text[:200],
                        "recommendations": []
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, create a basic structure
                analysis = {
                    "relevance_score": 5,
                    "outbreak_indicators": ["Analysis completed but JSON parsing failed"],
                    "key_patterns": [],
                    "urgent_concerns": [],
                    "summary": response_text[:200],
                    "recommendations": []
                }
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing {filename}: {e}")
            return {
                "relevance_score": 0,
                "outbreak_indicators": [],
                "key_patterns": [],
                "urgent_concerns": [f"Analysis failed: {str(e)}"],
                "summary": "Analysis could not be completed",
                "recommendations": []
            }
    
    def process_all_files(self) -> List[Dict[str, Any]]:
        """Process all files in the catalog."""
        catalog = self.load_catalog()
        
        if not catalog:
            print("No files found in catalog")
            return []
        
        print(f"Processing {len(catalog)} files from catalog...")
        
        for entry in catalog:
            filename = entry['filename']
            description = entry['description']
            
            print(f"\nProcessing: {filename}")
            print(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
            
            # Load the data
            data = self.load_data_file(filename)
            
            if data is None:
                print(f"Skipping {filename} - could not load data")
                continue
            
            # Analyze the data
            print(f"Analyzing {filename}...")
            analysis = self.analyze_outbreak_data(data, filename, description)
            
            # Store results
            result = {
                "filename": filename,
                "description": description,
                "analysis": analysis,
                "processed_at": datetime.now().isoformat()
            }
            self.analysis_results.append(result)
            
            # Print summary
            print(f"Relevance Score: {analysis.get('relevance_score', 'N/A')}/10")
            print(f"Summary: {analysis.get('summary', 'N/A')[:200]}")
            
            if analysis.get('urgent_concerns'):
                print(f"⚠️  URGENT CONCERNS: {', '.join(analysis['urgent_concerns'])}")
        
        return self.analysis_results
    
    def rank_by_relevance(self) -> List[Dict[str, Any]]:
        """Rank all analyzed files by their relevance score."""
        ranked = sorted(
            self.analysis_results,
            key=lambda x: x['analysis'].get('relevance_score', 0),
            reverse=True
        )
        return ranked
    
    def save_results(self, output_path: str = "outbreak_data/analysis_results.json"):
        """Save analysis results to a JSON file."""
        output_path = Path(output_path)
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare output with ranking
        output = {
            "processing_timestamp": datetime.now().isoformat(),
            "total_files_processed": len(self.analysis_results),
            "ranked_results": self.rank_by_relevance(),
            "initial_context_used": self.initial_context[:500] + "..." if len(self.initial_context) > 500 else self.initial_context
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nResults saved to {output_path}")
    
    def print_summary(self):
        """Print a summary of the analysis."""
        print("\n" + "="*60)
        print("OUTBREAK DATA ANALYSIS SUMMARY")
        print("="*60)
        
        if not self.analysis_results:
            print("No results to summarize")
            return
        
        ranked = self.rank_by_relevance()
        
        print(f"\nTotal files analyzed: {len(ranked)}")
        print("\nTop 5 Most Relevant Files:")
        print("-"*40)
        
        for i, result in enumerate(ranked[:5], 1):
            print(f"\n{i}. {result['filename']}")
            print(f"   Relevance Score: {result['analysis'].get('relevance_score', 'N/A')}/10")
            print(f"   Summary: {result['analysis'].get('summary', 'N/A')[:150]}...")
            
            indicators = result['analysis'].get('outbreak_indicators', [])
            if indicators:
                print(f"   Key Indicators: {', '.join(indicators[:3])}")
            
            urgent = result['analysis'].get('urgent_concerns', [])
            if urgent:
                print(f"   ⚠️  URGENT: {', '.join(urgent)}")
        
        # Check for any urgent concerns across all files
        all_urgent = []
        for result in ranked:
            urgent = result['analysis'].get('urgent_concerns', [])
            if urgent:
                all_urgent.extend([(result['filename'], concern) for concern in urgent])
        
        if all_urgent:
            print("\n" + "="*40)
            print("⚠️  ALL URGENT CONCERNS:")
            print("-"*40)
            for filename, concern in all_urgent:
                print(f"  • {filename}: {concern}")


def main():
    """Main execution function."""
    print("Starting Outbreak Data Processing...")
    print("="*60)
    
    # Initialize processor
    processor = OutbreakDataProcessor()
    
    # Process all files
    results = processor.process_all_files()
    
    if results:
        # Print summary
        processor.print_summary()
        
        # Save results
        processor.save_results()
        
        print("\n✅ Processing complete!")
    else:
        print("\n❌ No files were successfully processed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())