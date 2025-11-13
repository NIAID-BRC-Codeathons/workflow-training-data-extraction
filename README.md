# Extracting Training Data for Automated Workflow Generation

Creating structured question-answer training datasets from BRC resources and publications to train LLMs for bioinformatics workflow generation

## About This Project

This is a project from the **NIAID BRC AI Codeathon 2025**, taking place November 12-14, 2025 at Argonne National Laboratory.

**Event Website:** https://niaid-brc-codeathons.github.io/

**Project Details:** https://niaid-brc-codeathons.github.io/projects/workflow-training-data-extraction/

## Codeathon Goals

The NIAID Bioinformatics Resource Centers (BRCs) invite researchers, data scientists, and developers to a three-day AI Codeathon focused on improving Findability, Accessibility, Interoperability, and Reusability (FAIR-ness) of BRC data and tools using artificial intelligence (AI) and large language models (LLMs).

## Getting Started

### Sophia PDF Analyzer

AI-powered PDF analysis tool using ALCF's Sophia inference endpoint to extract text, images, and generate scientific insights from research papers.

#### Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements-sophia.txt
   ```

2. **Configure authentication**:
   ```bash
   # Option 1: Environment variable
   export SOPHIA_ACCESS_TOKEN="your-globus-access-token"

   # Option 2: Config file
   cp config/sophia.template.json config/sophia.json
   # Edit config/sophia.json and add your token
   ```

3. **Get a Globus access token**:
   ```bash
   # Download auth helper (if not already available)
   wget https://raw.githubusercontent.com/argonne-lcf/inference-endpoints/refs/heads/main/inference_auth_token.py

   # Authenticate
   python scripts/inference_auth_token.py authenticate
   export SOPHIA_ACCESS_TOKEN=$(python scripts/inference_auth_token.py get_access_token)
   ```

4. **Run the analyzer**:
   ```bash
   python scripts/sophia_pdf_analyzer.py your_paper.pdf
   ```

#### Documentation

- **Quick Start Guide**: [docs/SOPHIA_QUICKSTART.md](docs/SOPHIA_QUICKSTART.md)
- **Full Documentation**: [docs/SOPHIA_INTEGRATION.md](docs/SOPHIA_INTEGRATION.md)
- **PDF Extraction Comparison**: [docs/PDF_EXTRACTION_COMPARISON.md](docs/PDF_EXTRACTION_COMPARISON.md)
- **Llama-4-Scout Testing**: [docs/LLAMA4_SCOUT_TESTING.md](docs/LLAMA4_SCOUT_TESTING.md)

#### Features

- **PDF Content Extraction**: Automatic text and image extraction from multi-page PDFs
- **AI Analysis**: Document summarization and key findings identification
- **Question Generation**: Automatic generation of research questions
- **Multimodal Support**: Text analysis and vision capabilities
- **Flexible Authentication**: Environment variables or config file
- **Structured Output**: JSON output with complete analysis results
- **Method Comparison**: Compare PyMuPDF vs Sophia direct extraction

#### Comparing Extraction Methods

Compare two PDF extraction approaches:

```bash
# Compare PyMuPDF local extraction vs Sophia direct PDF processing
python scripts/compare_pdf_extraction.py paper.pdf --output comparison.json
```

See [PDF Extraction Comparison](docs/PDF_EXTRACTION_COMPARISON.md) for detailed analysis of both methods.

#### Testing Llama-4-Scout Multimodal Model

The **Llama-4-Scout-17B-16E-Instruct** model is now available with **native multimodal capabilities**:

- ✅ Text + Image processing
- ✅ 10 million token context window
- ✅ Document extraction and chart analysis
- ❓ Potential direct PDF support (needs testing)

Test if it supports PDF processing:

```bash
# Test Llama-4-Scout's PDF capabilities
python scripts/test_llama4_scout_pdf.py paper.pdf
```

See [Llama-4-Scout Testing Guide](docs/LLAMA4_SCOUT_TESTING.md) for detailed testing instructions and model capabilities.

## Team

*Team members: Add your team information here.*

## License

*To be determined by the team.*
