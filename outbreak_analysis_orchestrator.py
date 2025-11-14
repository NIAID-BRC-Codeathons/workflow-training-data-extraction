#!/usr/bin/env python3
"""
Outbreak Analysis Orchestrator
Coordinates the execution of outbreak analysis agents in sequence:
1. Outbreak Flagger (generates initial report)
2. Devil's Advocate Analyzer (challenges hypotheses)
3. Data Gatherer Agent (generates data collection plan)
"""

import sys
import os
from datetime import datetime
import subprocess
import time


class OutbreakAnalysisOrchestrator:
    def __init__(self):
        self.start_time = datetime.now()
        self.agents = [
            {
                "name": "Outbreak Flagger",
                "script": "outbreak_flagger_argo.py",
                "output": "potential_outbreaks.md",
                "description": "Analyzes outbreak catalog and generates initial outbreak report"
            },
            {
                "name": "Devil's Advocate Analyzer",
                "script": "devils_advocate_analyzer.py",
                "input": "potential_outbreaks.md",
                "output": "devils_advocate_analysis.md",
                "description": "Challenges outbreak hypotheses with alternative explanations"
            },
            {
                "name": "Data Gatherer Agent",
                "script": "data_gatherer_agent.py",
                "input": "devils_advocate_analysis.md",
                "output": "data_gathering_plan.json",
                "description": "Generates Firecrawl searches and URLs for hypothesis validation"
            },
            {
                "name": "Firecrawl Validation Agent",
                "script": "firecrawl_validation_agent.py",
                "input": "data_gathering_plan.json",
                "output": "validation_results.json",
                "description": "Executes Firecrawl searches and crawls to collect validation data"
            },
            {
                "name": "Hypothesis Validation Agent",
                "script": "hypothesis_validation_agent.py",
                "input": "validation_results.json",
                "output": "final_outbreak_validation_report.md",
                "description": "Validates hypotheses against collected evidence for final assessment"
            }
        ]
        
    def print_header(self):
        """Print orchestrator header"""
        print("=" * 70)
        print("OUTBREAK ANALYSIS ORCHESTRATOR")
        print("Automated Multi-Agent Outbreak Investigation Pipeline")
        print("=" * 70)
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("-" * 70)
        
    def run_agent(self, agent_info):
        """Run a single agent"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running: {agent_info['name']}")
        print(f"Description: {agent_info['description']}")
        
        # Check if input file exists (if required)
        if 'input' in agent_info:
            if not os.path.exists(agent_info['input']):
                print(f"ERROR: Required input file '{agent_info['input']}' not found")
                return False
            print(f"Input: {agent_info['input']}")
        
        print(f"Script: {agent_info['script']}")
        print("-" * 50)
        
        try:
            # Run the agent script
            result = subprocess.run(
                [sys.executable, agent_info['script']],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("Errors/Warnings:", result.stderr)
            
            # Check if output file was created
            if 'output' in agent_info:
                if os.path.exists(agent_info['output']):
                    print(f"✓ Output generated: {agent_info['output']}")
                    return True
                else:
                    print(f"✗ Expected output file not found: {agent_info['output']}")
                    return False
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"ERROR: Agent timed out after 30 minutes")
            return False
        except Exception as e:
            print(f"ERROR: Failed to run agent: {e}")
            return False
    
    def generate_summary_report(self):
        """Generate a summary of the orchestration run"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        summary = f"""
# Outbreak Analysis Pipeline Summary

**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Duration:** {duration}

## Pipeline Execution

| Agent | Status | Output |
|-------|--------|--------|
"""
        
        for agent in self.agents:
            output = agent.get('output', 'N/A')
            exists = "✓" if output == 'N/A' or os.path.exists(output) else "✗"
            summary += f"| {agent['name']} | {exists} | {output} |\n"
        
        summary += """

## Generated Files

1. **potential_outbreaks.md** - Initial outbreak analysis report
2. **devils_advocate_analysis.md** - Alternative hypotheses and validation tasks
3. **data_gathering_plan.json** - Firecrawl searches and URLs for data collection
4. **data_gathering_plan.md** - Human-readable data gathering plan
5. **validation_results.json** - Results from Firecrawl validation
6. **validation_summary.md** - Summary of validation data collection
7. **outbreak_data/** - Directory containing all scraped content
8. **final_outbreak_validation_report.md** - Final evidence-based assessment
9. **validation_summary.json** - Summary metadata for final validation

## Next Steps

1. Review the devil's advocate analysis for alternative explanations
2. Review validation results in validation_summary.md
3. Analyze collected data in outbreak_data/ directory
4. Compare findings across sources to validate/refute hypotheses
5. Update outbreak assessments based on evidence
6. Allocate resources based on validated threats

## Pipeline Components

### 1. Outbreak Flagger (`outbreak_flagger_argo.py`)
- Reads outbreak data catalog
- Uses ARGO LLM to identify potential outbreaks
- Generates initial hypotheses and investigation URLs

### 2. Devil's Advocate Analyzer (`devils_advocate_analyzer.py`)
- Challenges conventional outbreak interpretations
- Proposes alternative explanations (data artifacts, biases, etc.)
- Creates validation tasks to test all hypotheses

### 3. Data Gatherer Agent (`data_gatherer_agent.py`)
- Analyzes validation requirements
- Generates Firecrawl search queries
- Identifies specific URLs to scrape
- Prioritizes data collection tasks

### 4. Firecrawl Validation Agent (`firecrawl_validation_agent.py`)
- Executes search queries using Firecrawl API
- Crawls URLs with deep crawling for authoritative sources
- Collects validation data for hypothesis testing
- Saves results to outbreak_data directory

### 5. Hypothesis Validation Agent (`hypothesis_validation_agent.py`)
- Reads all prior reports and crawled data
- Validates original and alternative hypotheses against evidence
- Generates final evidence-based assessment
- Provides confidence levels and recommendations
"""
        
        # Save summary
        with open("pipeline_summary.md", 'w') as f:
            f.write(summary)
        
        print("\n" + "=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        print(summary)
        
    def run(self):
        """Run the complete orchestration pipeline"""
        self.print_header()
        
        success_count = 0
        failed_agents = []
        
        for i, agent in enumerate(self.agents, 1):
            print(f"\n{'=' * 70}")
            print(f"STAGE {i}/{len(self.agents)}: {agent['name'].upper()}")
            print("=" * 70)
            
            success = self.run_agent(agent)
            
            if success:
                success_count += 1
                print(f"\n✓ {agent['name']} completed successfully")
            else:
                failed_agents.append(agent['name'])
                print(f"\n✗ {agent['name']} failed")
                
                # Ask if user wants to continue despite failure
                if i < len(self.agents):
                    print("\nWARNING: Agent failed. Continuing with next agent...")
                    # In a real implementation, you might want to handle this differently
        
        # Generate summary report
        self.generate_summary_report()
        
        # Final status
        print("\n" + "=" * 70)
        print("ORCHESTRATION COMPLETE")
        print("=" * 70)
        print(f"Successful agents: {success_count}/{len(self.agents)}")
        if failed_agents:
            print(f"Failed agents: {', '.join(failed_agents)}")
        print(f"Total duration: {datetime.now() - self.start_time}")
        print("=" * 70)
        
        return success_count == len(self.agents)


def main():
    orchestrator = OutbreakAnalysisOrchestrator()
    success = orchestrator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()