#!/usr/bin/env python3
"""
Hypothesis Validation Agent
Takes crawled results and validates them against both original outbreak hypotheses 
and devil's advocate alternative hypotheses to generate a final assessment report.
"""

import sys
import os
import json
import glob
from datetime import datetime

# Add scripts directory to path to import ARGO
sys.path.append('scripts')
from ARGO import ArgoWrapper


class HypothesisValidationAgent:
    def __init__(self, 
                 outbreak_report_path="potential_outbreaks.md",
                 devils_advocate_path="devils_advocate_analysis.md", 
                 validation_results_path="validation_results.json",
                 crawled_data_dir="outbreak_data"):
        self.outbreak_report_path = outbreak_report_path
        self.devils_advocate_path = devils_advocate_path
        self.validation_results_path = validation_results_path
        self.crawled_data_dir = crawled_data_dir
        self.argo = ArgoWrapper(model="gpt4o")
        
    def gather_inputs(self):
        """Read all input files needed for validation"""
        inputs = {}
        
        # Read original outbreak report
        print(f"Reading original outbreak report from: {self.outbreak_report_path}")
        try:
            with open(self.outbreak_report_path, 'r', encoding='utf-8') as f:
                inputs['outbreak_report'] = f.read()
            print("✓ Successfully read outbreak report")
        except Exception as e:
            print(f"✗ Error reading outbreak report: {e}")
            return None
            
        # Read devil's advocate analysis
        print(f"Reading devil's advocate analysis from: {self.devils_advocate_path}")
        try:
            with open(self.devils_advocate_path, 'r', encoding='utf-8') as f:
                inputs['devils_advocate'] = f.read()
            print("✓ Successfully read devil's advocate analysis")
        except Exception as e:
            print(f"✗ Error reading devil's advocate analysis: {e}")
            return None
            
        # Read validation results if available
        if os.path.exists(self.validation_results_path):
            print(f"Reading validation results from: {self.validation_results_path}")
            try:
                with open(self.validation_results_path, 'r', encoding='utf-8') as f:
                    inputs['validation_results'] = json.load(f)
                print("✓ Successfully read validation results")
            except Exception as e:
                print(f"⚠ Could not read validation results: {e}")
                inputs['validation_results'] = None
        else:
            print("⚠ No validation results file found")
            inputs['validation_results'] = None
            
        # Read recent crawled data files
        print(f"Reading crawled data from: {self.crawled_data_dir}")
        try:
            # Get the most recent data files (last 50)
            data_files = sorted(glob.glob(os.path.join(self.crawled_data_dir, "data_*.json")))[-50:]
            crawled_data = []
            
            for file_path in data_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Extract key information from each file
                        if isinstance(data, list) and len(data) > 0:
                            for item in data[:2]:  # Take first 2 items from each file
                                if 'content' in item:
                                    crawled_data.append({
                                        'source': file_path.split('/')[-1],
                                        'snippet': item.get('snippet', '')[:500],
                                        'content_preview': item.get('content', '')[:1000]
                                    })
                except:
                    continue
                    
            inputs['crawled_data'] = crawled_data
            print(f"✓ Successfully read {len(crawled_data)} crawled data samples from {len(data_files)} files")
        except Exception as e:
            print(f"⚠ Error reading crawled data: {e}")
            inputs['crawled_data'] = []
            
        return inputs
    
    def validate_hypotheses(self, inputs):
        """Use ARGO to validate hypotheses against collected data"""
        print("\nValidating hypotheses with ARGO...")
        
        # Prepare crawled data summary
        crawled_summary = ""
        if inputs.get('crawled_data'):
            crawled_summary = "SAMPLE OF CRAWLED DATA:\n"
            for item in inputs['crawled_data'][:20]:  # Limit to 20 samples
                crawled_summary += f"\nSource: {item['source']}\n"
                crawled_summary += f"Content: {item['content_preview']}\n"
                crawled_summary += "-" * 50 + "\n"
        
        # System prompt for hypothesis validation
        system_prompt = """You are an expert epidemiologist and data analyst tasked with validating outbreak hypotheses against collected evidence. Your role is to:

1. Compare original outbreak hypotheses with alternative explanations
2. Evaluate collected data to determine which hypotheses are supported
3. Identify which alternative explanations can be ruled out
4. Assess the strength of evidence for each outbreak
5. Provide a final risk assessment and recommendations

Be objective, evidence-based, and transparent about uncertainty. Consider:
- Data quality and reliability
- Consistency across multiple sources
- Temporal and geographic patterns
- Laboratory confirmation rates
- Comparison with historical baselines
- Presence or absence of confounding factors

Rate evidence strength as: STRONG, MODERATE, WEAK, or INSUFFICIENT"""

        # User prompt with all inputs
        user_prompt = f"""Validate the outbreak hypotheses against the collected evidence and generate a comprehensive final assessment report.

ORIGINAL OUTBREAK REPORT:
{inputs['outbreak_report'][:5000]}  # Truncate for context limits

DEVIL'S ADVOCATE ALTERNATIVE HYPOTHESES:
{inputs['devils_advocate'][:5000]}  # Truncate for context limits

{crawled_summary}

Generate a final validation report with the following structure:

# Final Outbreak Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Analysis Type:** Evidence-Based Hypothesis Validation

## Executive Summary
Provide a high-level summary of findings and overall outbreak risk assessment.

## Validation Results by Outbreak

For EACH outbreak identified:

### [Outbreak Name]

#### Evidence Assessment
- **Data Sources Reviewed:** Number and types of sources
- **Evidence Strength:** STRONG/MODERATE/WEAK/INSUFFICIENT
- **Key Findings:** Bullet points of most important evidence

#### Original Hypotheses Validation
For each original hypothesis:
- Hypothesis: [State the hypothesis]
- Evidence: [Supporting or refuting evidence]
- Status: SUPPORTED/REFUTED/INCONCLUSIVE

#### Alternative Hypotheses Validation
For each alternative hypothesis from devil's advocate:
- Alternative: [State the alternative explanation]
- Evidence: [Supporting or refuting evidence]
- Status: SUPPORTED/REFUTED/INCONCLUSIVE

#### Data Quality Assessment
- Reporting consistency across sources
- Presence of data artifacts or biases
- Laboratory confirmation availability
- Temporal patterns analysis

#### Final Assessment
- **Most Likely Explanation:** [Based on evidence]
- **Confidence Level:** HIGH/MEDIUM/LOW
- **Risk Level:** CRITICAL/HIGH/MODERATE/LOW/MINIMAL

## Comparative Analysis

### Outbreaks Confirmed vs. Alternative Explanations
Table or summary comparing which outbreaks appear genuine vs. explained by alternatives

### Data Gaps and Uncertainties
- What critical data is still missing
- Which hypotheses remain unresolved
- Areas requiring further investigation

## Final Recommendations

### Immediate Actions
Priority actions based on validated threats

### Resource Allocation
Where to focus resources based on evidence

### Surveillance Enhancement
Areas requiring enhanced monitoring

### Further Investigation Needs
Specific data collection or studies needed

## Methodology Notes
Brief description of how evidence was evaluated and limitations

Remember: Be rigorous in distinguishing between correlation and causation, and transparent about the strength and limitations of available evidence."""

        try:
            # Call ARGO LLM to generate validation report
            response = self.argo.invoke(
                prompt_system=system_prompt,
                prompt_user=user_prompt,
                temperature=0.2,  # Low temperature for analytical consistency
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
    
    def save_final_report(self, report_content):
        """Save the final validation report"""
        if not report_content:
            print("No report content to save")
            return False
            
        output_file = "final_outbreak_validation_report.md"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"\nFinal report successfully saved to: {output_file}")
            
            # Also create a summary JSON for programmatic use
            summary = {
                "metadata": {
                    "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "type": "final_validation_report",
                    "sources": {
                        "outbreak_report": self.outbreak_report_path,
                        "devils_advocate": self.devils_advocate_path,
                        "validation_results": self.validation_results_path,
                        "crawled_data": self.crawled_data_dir
                    }
                },
                "report_location": output_file,
                "status": "completed"
            }
            
            with open("validation_summary.json", 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            print(f"Summary saved to: validation_summary.json")
            
            return True
            
        except Exception as e:
            print(f"Error saving report: {e}")
            return False
    
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("HYPOTHESIS VALIDATION AGENT")
        print("Final Evidence-Based Assessment of Outbreak Hypotheses")
        print("=" * 60)
        
        # Gather all inputs
        inputs = self.gather_inputs()
        if not inputs:
            print("Failed to gather necessary inputs")
            return
        
        # Validate hypotheses against evidence
        final_report = self.validate_hypotheses(inputs)
        
        if final_report:
            # Save the final report
            if self.save_final_report(final_report):
                print("\n" + "=" * 60)
                print("HYPOTHESIS VALIDATION COMPLETE")
                print("=" * 60)
                print("\nKey Outputs:")
                print("1. final_outbreak_validation_report.md - Comprehensive validation report")
                print("2. validation_summary.json - Summary metadata")
                
                print("\nNext Steps:")
                print("1. Review final assessments for each outbreak")
                print("2. Implement recommendations based on validated threats")
                print("3. Allocate resources according to evidence-based priorities")
                print("4. Continue monitoring for new data on unresolved hypotheses")
        else:
            print("Failed to generate validation report")


def main():
    # Allow custom paths via command line arguments
    outbreak_report = "potential_outbreaks.md"
    devils_advocate = "devils_advocate_analysis.md"
    validation_results = "validation_results.json"
    crawled_data = "outbreak_data"
    
    if len(sys.argv) > 1:
        outbreak_report = sys.argv[1]
    if len(sys.argv) > 2:
        devils_advocate = sys.argv[2]
    if len(sys.argv) > 3:
        validation_results = sys.argv[3]
    if len(sys.argv) > 4:
        crawled_data = sys.argv[4]
    
    agent = HypothesisValidationAgent(
        outbreak_report_path=outbreak_report,
        devils_advocate_path=devils_advocate,
        validation_results_path=validation_results,
        crawled_data_dir=crawled_data
    )
    agent.run()


if __name__ == "__main__":
    main()