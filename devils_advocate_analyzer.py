#!/usr/bin/env python3
"""
Devil's Advocate Analyzer
Takes factual outbreak reports and generates alternative hypotheses that could explain the data,
along with specific validation tasks to test these hypotheses.
"""

import sys
import os
from datetime import datetime

# Add scripts directory to path to import ARGO
sys.path.append('scripts')
from ARGO import ArgoWrapper


class DevilsAdvocateAnalyzer:
    def __init__(self, report_path="potential_outbreaks.md"):
        self.report_path = report_path
        self.argo = ArgoWrapper(model="gpt4o")
        
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("DEVIL'S ADVOCATE ANALYZER")
        print("Challenging Outbreak Assumptions Through Alternative Hypotheses")
        print("=" * 60)
        
        # Read the outbreak report
        print(f"Reading outbreak report from: {self.report_path}")
        try:
            with open(self.report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            print("Successfully read outbreak report")
        except Exception as e:
            print(f"Error reading report: {e}")
            return
        
        # System prompt for devil's advocate analysis
        system_prompt = """You are a skeptical epidemiologist and data scientist acting as a "devil's advocate" to challenge conventional outbreak interpretations. Your role is to:

1. Question assumptions in the original hypotheses
2. Propose alternative explanations that could account for the observed data
3. Identify potential confounding factors, biases, or data artifacts
4. Suggest specific validation tasks to test both original and alternative hypotheses

For each outbreak, consider alternative explanations such as:
- Data quality issues (reporting artifacts, surveillance bias, testing changes)
- Seasonal patterns or cyclical trends being misinterpreted
- Changes in diagnostic criteria or reporting requirements
- Population dynamics (migration, demographic shifts)
- Environmental or climatic factors
- Socioeconomic changes affecting healthcare access
- Media attention causing reporting bias
- Laboratory contamination or false positives
- Misclassification or misdiagnosis
- Political or economic incentives affecting reporting

Be thorough, scientific, and constructive in your skepticism. The goal is to strengthen outbreak investigation through rigorous hypothesis testing."""

        # User prompt with the full report
        user_prompt = f"""Analyze this outbreak report as a devil's advocate and generate alternative hypotheses that could explain the observed data patterns, along with specific validation tasks.

OUTBREAK REPORT:
{report_content}

Generate a comprehensive markdown report with the following structure:

# Devil's Advocate Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

For EACH identified outbreak in the report, provide:

## [Outbreak Name]

### Alternative Hypotheses
List 3-5 alternative explanations that could account for the observed data WITHOUT it being a true disease outbreak:
- Each hypothesis should challenge the conventional interpretation
- Consider data artifacts, reporting biases, or non-disease factors
- Make each hypothesis specific and testable

### Validation Tasks
List 5-7 specific tasks to validate or refute both the original and alternative hypotheses:
- Be precise about what data to collect
- Specify analytical methods to use
- Include control comparisons
- Define success/failure criteria

### Critical Data Gaps
- What key information is missing?
- What data would definitively prove/disprove the outbreak?

### Priority Actions
Rank the top 3 most important validation steps

## Summary and Recommendations

### Quick Validation Checklist
Create a prioritized checklist of immediate actions (within 24-48 hours) that could quickly validate or refute the outbreak hypotheses.

### Resource Allocation Guidance
Based on the alternative hypotheses, provide guidance on:
- When to escalate vs. when to monitor
- Resource allocation priorities
- Risk assessment considering all hypotheses

Remember: The goal is not to dismiss real outbreaks but to ensure rigorous validation through systematic hypothesis testing. Be constructive and actionable in your analysis."""

        print("Generating devil's advocate analysis with ARGO...")
        
        try:
            # Call ARGO LLM to generate alternative analysis
            response = self.argo.invoke(
                prompt_system=system_prompt,
                prompt_user=user_prompt,
                temperature=0.3,  # Moderate temperature for creative but grounded alternatives
                top_p=0.95
            )
            
            if response and 'response' in response:
                analysis_content = response['response']
                
                # Save the analysis
                output_file = "devils_advocate_analysis.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(analysis_content)
                
                print(f"\nAnalysis successfully saved to: {output_file}")
                print("\n" + "=" * 60)
                print("Devil's Advocate Analysis Complete!")
                print("=" * 60)
                print(f"\nNext Steps:")
                print(f"1. Review alternative hypotheses in {output_file}")
                print(f"2. Prioritize validation tasks based on resources")
                print(f"3. Execute quick validation checks first")
                print(f"4. Update outbreak assessment based on findings")
                
            else:
                print("Error: Invalid response from ARGO")
                
        except Exception as e:
            print(f"Error calling ARGO: {e}")


def main():
    # Check if a custom report path is provided
    report_path = "potential_outbreaks.md"
    if len(sys.argv) > 1:
        report_path = sys.argv[1]
    
    analyzer = DevilsAdvocateAnalyzer(report_path=report_path)
    analyzer.run()


if __name__ == "__main__":
    main()