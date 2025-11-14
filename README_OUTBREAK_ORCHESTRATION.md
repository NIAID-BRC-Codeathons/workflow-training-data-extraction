# Outbreak Analysis Orchestration System

## Overview

The Outbreak Analysis Orchestration System is a comprehensive, multi-agent pipeline for detecting, validating, and assessing potential disease outbreaks. It employs a rigorous, evidence-based approach that challenges assumptions, tests alternative hypotheses, and validates threats through systematic data collection from authoritative sources.

## Key Features

- **Multi-stage validation**: 5 specialized agents working in sequence
- **Devil's advocate approach**: Systematic challenging of outbreak assumptions
- **Evidence-based assessment**: Data-driven validation of hypotheses
- **Automated data collection**: Firecrawl integration for web scraping
- **Confidence scoring**: Transparent assessment of evidence strength
- **Risk prioritization**: Resource allocation based on validated threats

## System Architecture

```
┌─────────────────────┐
│  Outbreak Catalog   │
│    (CSV Data)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 1. Outbreak Flagger │ ──► potential_outbreaks.md
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Devil's Advocate │ ──► devils_advocate_analysis.md
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. Data Gatherer    │ ──► data_gathering_plan.json
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Firecrawl Agent  │ ──► validation_results.json
└──────────┬──────────┘     outbreak_data/*.json
           │
           ▼
┌─────────────────────┐
│ 5. Validation Agent │ ──► final_outbreak_validation_report.md
└─────────────────────┘
```

## Agents

### 1. Outbreak Flagger (`outbreak_flagger_argo.py`)
Analyzes outbreak catalog data to identify potential disease outbreaks.

**Input**: `outbreak_data/catalog.csv`  
**Output**: `potential_outbreaks.md`  
**Function**: 
- Processes outbreak data entries
- Identifies disease patterns
- Generates initial hypotheses
- Suggests investigation URLs

### 2. Devil's Advocate Analyzer (`devils_advocate_analyzer.py`)
Challenges conventional outbreak interpretations with alternative explanations.

**Input**: `potential_outbreaks.md`  
**Output**: `devils_advocate_analysis.md`  
**Function**:
- Proposes non-outbreak explanations
- Identifies potential biases and artifacts
- Creates validation tasks
- Questions assumptions systematically

### 3. Data Gatherer Agent (`data_gatherer_agent.py`)
Plans comprehensive data collection strategy for hypothesis validation.

**Input**: `devils_advocate_analysis.md`  
**Output**: `data_gathering_plan.json`  
**Function**:
- Generates 5-10 search queries per outbreak
- Identifies 10-15 URLs to scrape per outbreak
- Prioritizes data sources
- Defines validation requirements

### 4. Firecrawl Validation Agent (`firecrawl_validation_agent.py`)
Executes web searches and crawls to collect validation data.

**Input**: `data_gathering_plan.json`  
**Output**: `validation_results.json`, `outbreak_data/*.json`  
**Function**:
- Executes Firecrawl searches
- Performs deep crawls on authoritative sources
- Saves intermediate results
- Stores all scraped content

### 5. Hypothesis Validation Agent (`hypothesis_validation_agent.py`)
Validates all hypotheses against collected evidence for final assessment.

**Input**: All prior reports and crawled data  
**Output**: `final_outbreak_validation_report.md`  
**Function**:
- Evaluates evidence strength
- Tests original vs. alternative hypotheses
- Assigns confidence levels
- Provides risk assessments

## Installation

### Prerequisites

- Python 3.8+
- Firecrawl API key
- ARGO LLM access

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd outbreak-orchestration
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
# Create .env file
echo "FIRECRAWL_API_KEY=your_api_key_here" > .env
```

4. Set up ARGO credentials in `scripts/ARGO.py`

## Usage

### Running the Complete Pipeline

```bash
python outbreak_analysis_orchestrator.py
```

This runs all 5 agents in sequence, generating a complete outbreak validation report.

### Running Individual Agents

```bash
# Stage 1: Identify outbreaks
python outbreak_flagger_argo.py

# Stage 2: Generate alternative hypotheses
python devils_advocate_analyzer.py

# Stage 3: Plan data collection
python data_gatherer_agent.py

# Stage 4: Collect validation data
python firecrawl_validation_agent.py

# Stage 5: Validate hypotheses
python hypothesis_validation_agent.py
```

### Custom Input Files

Most agents accept custom input paths:

```bash
# Use custom outbreak report
python devils_advocate_analyzer.py custom_report.md

# Use custom analysis for data gathering
python data_gatherer_agent.py custom_analysis.md

# Use custom plan for validation
python firecrawl_validation_agent.py custom_plan.json
```

## Output Files

| File | Description |
|------|-------------|
| `potential_outbreaks.md` | Initial outbreak analysis report |
| `devils_advocate_analysis.md` | Alternative hypotheses and validation tasks |
| `data_gathering_plan.json` | Structured data collection plan |
| `data_gathering_plan.md` | Human-readable collection plan |
| `validation_results.json` | Firecrawl execution results |
| `validation_summary.md` | Data collection summary |
| `outbreak_data/*.json` | All scraped content |
| `final_outbreak_validation_report.md` | Final evidence-based assessment |
| `validation_summary.json` | Final validation metadata |
| `pipeline_summary.md` | Orchestration execution summary |

## Evidence Assessment Levels

### Evidence Strength
- **STRONG**: Multiple consistent sources, high laboratory confirmation
- **MODERATE**: Some consistent sources, moderate confirmation
- **WEAK**: Limited sources, low confirmation
- **INSUFFICIENT**: Not enough data for assessment

### Confidence Levels
- **HIGH**: Strong evidence, alternative hypotheses refuted
- **MEDIUM**: Moderate evidence, some alternatives possible
- **LOW**: Weak evidence, alternatives equally likely

### Risk Levels
- **CRITICAL**: Immediate action required
- **HIGH**: Urgent attention needed
- **MODERATE**: Enhanced monitoring recommended
- **LOW**: Standard surveillance sufficient
- **MINIMAL**: No immediate concern

## Example Output

### Final Validation Report Structure

```markdown
# Final Outbreak Validation Report

## Executive Summary
High-level findings and risk assessment

## Validation Results by Outbreak
### [Outbreak Name]
- Evidence Assessment
- Original Hypotheses Validation
- Alternative Hypotheses Validation
- Data Quality Assessment
- Final Assessment

## Comparative Analysis
- Confirmed vs. Alternative Explanations
- Data Gaps and Uncertainties

## Final Recommendations
- Immediate Actions
- Resource Allocation
- Surveillance Enhancement
- Further Investigation Needs
```

## Configuration

### Timeout Settings

Edit `outbreak_analysis_orchestrator.py`:

```python
# Default: 5 minutes per agent
timeout=300  # seconds
```

### Firecrawl Settings

Edit `firecrawl_validation_agent.py`:

```python
# Search settings
num_results = 5  # Results per search
max_depth = 3    # Crawl depth for authoritative sources

# Rate limiting
time.sleep(2)    # Delay between searches
time.sleep(3)    # Delay between crawls
```

### ARGO Model Selection

Each agent can use different models:

```python
self.argo = ArgoWrapper(model="gpt4o")  # or "claude-3", etc.
```

## Troubleshooting

### Common Issues

1. **Firecrawl timeout**: Increase timeout or reduce number of searches
2. **ARGO rate limits**: Add delays between agent calls
3. **Memory issues**: Process smaller batches of data
4. **Missing dependencies**: Run `pip install -r requirements.txt`

### Debug Mode

Enable verbose logging:

```python
# In any agent file
DEBUG = True  # Add at top of file
```

## Data Flow

1. **Catalog Data** → Outbreak identification
2. **Outbreak Report** → Alternative hypothesis generation
3. **Hypotheses** → Data collection planning
4. **Collection Plan** → Web scraping execution
5. **Scraped Data** → Hypothesis validation
6. **Validation** → Final risk assessment

## Best Practices

1. **Regular Updates**: Keep outbreak catalog current
2. **Source Verification**: Prioritize authoritative sources
3. **Hypothesis Testing**: Test both original and alternative explanations
4. **Evidence Documentation**: Save all scraped data for audit
5. **Confidence Transparency**: Always report uncertainty levels

## Contributing

### Adding New Agents

1. Create agent file following the pattern:
```python
class YourAgent:
    def __init__(self, input_path):
        self.argo = ArgoWrapper(model="gpt4o")
    
    def run(self):
        # Agent logic
        pass
```

2. Add to orchestrator pipeline in `outbreak_analysis_orchestrator.py`

### Improving Existing Agents

- Enhance prompts in agent files
- Add validation logic
- Improve error handling
- Optimize API usage

## License

[Your License Here]

## Support

For issues or questions:
- Create an issue in the repository
- Contact: [your-email@example.com]

## Acknowledgments

- ARGO LLM for analysis capabilities
- Firecrawl for web scraping
- Public health organizations for data sources

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Production Ready