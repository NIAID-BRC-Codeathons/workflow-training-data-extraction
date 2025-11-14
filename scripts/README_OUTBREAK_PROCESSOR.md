# Outbreak Data Processor

Analyzes outbreak data files using Argo LLM to identify patterns and rank relevance.

## Usage

```bash
python scripts/process_outbreak_data.py
```

## What it does

- Reads files from `outbreak_data/` using `catalog.csv`
- Analyzes each file with LLM for outbreak indicators
- Ranks files by relevance (0-10 scale)
- Saves results to `outbreak_data/analysis_results.json`

## Output

- Relevance scores
- Outbreak indicators
- Urgent concerns
- Recommendations

Results are printed to console and saved as JSON.