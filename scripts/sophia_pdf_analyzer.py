#!/usr/bin/env python3
"""
Sophia PDF Analyzer

Processes PDF files using ALCF's Sophia inference endpoint:
1. Extracts text content from PDF pages
2. Extracts embedded images
3. Analyzes scientific text
4. Generates high-level research questions

Usage:
    python sophia_pdf_analyzer.py <pdf_file> [--output output.json] [--config config/sophia.json]

Requirements:
    pip install requests PyMuPDF pillow
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add lib/python to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "python"))

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

from sophia_client import SophiaClient, SophiaConfig, ChatMessage


@dataclass
class ExtractedImage:
    """Represents an extracted image from PDF"""
    page_num: int
    image_index: int
    file_path: str
    width: int
    height: int
    format: str


@dataclass
class PDFPage:
    """Represents a page in the PDF"""
    page_num: int
    text: str
    images: List[ExtractedImage]
    word_count: int


@dataclass
class PDFAnalysis:
    """Complete analysis of a PDF document"""
    pdf_path: str
    timestamp: str
    total_pages: int
    total_words: int
    total_images: int
    pages: List[PDFPage]
    full_text: str
    summary: str
    key_findings: List[str]
    questions: List[str]
    metadata: Dict[str, Any]


class SophiaPDFAnalyzer:
    """Analyzes PDF documents using Sophia inference endpoint"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize PDF analyzer

        Args:
            config_path: Optional path to sophia config file
        """
        print("Initializing Sophia PDF Analyzer...")
        self.client = SophiaClient(config_path=config_path)
        self.config = self.client.config

        # Create output directory
        self.output_dir = Path(self.config.pdf_processing.get("output_dir", "output"))
        self.output_dir.mkdir(exist_ok=True)

        print(f"Connected to: {self.config.base_url}")
        print(f"Using model: {self.config.default_model}")

    def extract_pdf_content(self, pdf_path: Path) -> List[PDFPage]:
        """
        Extract text and images from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PDFPage objects
        """
        print(f"\nExtracting content from: {pdf_path.name}")

        doc = fitz.open(pdf_path)
        pages = []

        # Create subdirectory for images from this PDF
        pdf_name = pdf_path.stem
        images_dir = self.output_dir / f"{pdf_name}_images"
        images_dir.mkdir(exist_ok=True)

        for page_num, page in enumerate(doc, start=1):
            print(f"  Processing page {page_num}/{len(doc)}...")

            # Extract text
            text = page.get_text()
            word_count = len(text.split())

            # Extract images
            extracted_images = []
            if self.config.pdf_processing.get("extract_images", True):
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)

                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Save image
                        image_filename = f"page{page_num}_img{img_index + 1}.{image_ext}"
                        image_path = images_dir / image_filename

                        with open(image_path, "wb") as img_file:
                            img_file.write(image_bytes)

                        # Get image dimensions
                        with Image.open(image_path) as pil_img:
                            width, height = pil_img.size

                        extracted_images.append(ExtractedImage(
                            page_num=page_num,
                            image_index=img_index + 1,
                            file_path=str(image_path),
                            width=width,
                            height=height,
                            format=image_ext
                        ))

                        print(f"    Extracted image: {image_filename} ({width}x{height})")

                    except Exception as e:
                        print(f"    Warning: Could not extract image {img_index + 1}: {e}")

            pages.append(PDFPage(
                page_num=page_num,
                text=text,
                images=extracted_images,
                word_count=word_count
            ))

        doc.close()

        total_words = sum(p.word_count for p in pages)
        total_images = sum(len(p.images) for p in pages)

        print(f"\nExtraction complete:")
        print(f"  Pages: {len(pages)}")
        print(f"  Words: {total_words:,}")
        print(f"  Images: {total_images}")

        return pages

    def analyze_document(self, pdf_path: Path, pages: List[PDFPage]) -> PDFAnalysis:
        """
        Analyze extracted PDF content using Sophia

        Args:
            pdf_path: Original PDF path
            pages: List of extracted PDFPage objects

        Returns:
            PDFAnalysis object with complete analysis
        """
        print("\n" + "=" * 80)
        print("ANALYZING DOCUMENT WITH SOPHIA")
        print("=" * 80)

        # Combine all text
        full_text = "\n\n".join([
            f"=== Page {p.page_num} ===\n{p.text}"
            for p in pages if p.text.strip()
        ])

        # Truncate if too long (to avoid token limits)
        max_chars = 50000  # Adjust based on model's context window
        if len(full_text) > max_chars:
            print(f"\nNote: Text truncated from {len(full_text):,} to {max_chars:,} characters")
            full_text = full_text[:max_chars] + "\n\n[Text truncated...]"

        # Generate summary
        print("\n1. Generating summary...")
        try:
            summary_response = self.client.analyze_text(
                full_text,
                analysis_type="summary",
                max_tokens=500
            )
            summary = summary_response.content
            print(f"   Generated summary ({len(summary)} characters)")
        except Exception as e:
            print(f"   Warning: Could not generate summary: {e}")
            summary = "Summary generation failed."

        # Extract key findings
        print("\n2. Extracting key findings...")
        try:
            findings_response = self.client.analyze_text(
                full_text,
                analysis_type="key_findings",
                max_tokens=800
            )

            # Parse findings into list
            findings_text = findings_response.content
            key_findings = []
            for line in findings_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                    # Remove list markers
                    for prefix in [f"{i}." for i in range(1, 20)] + [f"{i})" for i in range(1, 20)] + ['-', '*', '•']:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                            break
                    if line:
                        key_findings.append(line)

            print(f"   Extracted {len(key_findings)} key findings")
        except Exception as e:
            print(f"   Warning: Could not extract key findings: {e}")
            key_findings = []

        # Generate research questions
        print("\n3. Generating high-level research questions...")
        num_questions = self.config.pdf_processing.get("questions_to_generate", 5)
        try:
            questions = self.client.generate_questions(
                full_text,
                num_questions=num_questions,
                question_type="high-level scientific",
                max_tokens=1000
            )
            print(f"   Generated {len(questions)} questions")
        except Exception as e:
            print(f"   Warning: Could not generate questions: {e}")
            questions = []

        # Create metadata
        metadata = {
            "pdf_filename": pdf_path.name,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "model_used": self.config.default_model,
            "api_endpoint": self.config.base_url
        }

        return PDFAnalysis(
            pdf_path=str(pdf_path),
            timestamp=datetime.now().isoformat(),
            total_pages=len(pages),
            total_words=sum(p.word_count for p in pages),
            total_images=sum(len(p.images) for p in pages),
            pages=pages,
            full_text=full_text,
            summary=summary,
            key_findings=key_findings,
            questions=questions,
            metadata=metadata
        )

    def save_analysis(self, analysis: PDFAnalysis, output_path: Path):
        """
        Save analysis results to JSON file

        Args:
            analysis: PDFAnalysis object
            output_path: Path to output JSON file
        """
        # Convert to dict
        data = asdict(analysis)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nAnalysis saved to: {output_path}")

    def print_summary(self, analysis: PDFAnalysis):
        """Print analysis summary to console"""
        print("\n" + "=" * 80)
        print("ANALYSIS SUMMARY")
        print("=" * 80)

        print(f"\nDocument: {Path(analysis.pdf_path).name}")
        print(f"Pages: {analysis.total_pages}")
        print(f"Words: {analysis.total_words:,}")
        print(f"Images: {analysis.total_images}")

        print("\n--- Summary ---")
        print(analysis.summary)

        if analysis.key_findings:
            print("\n--- Key Findings ---")
            for i, finding in enumerate(analysis.key_findings, 1):
                print(f"{i}. {finding}")

        if analysis.questions:
            print("\n--- High-Level Research Questions ---")
            for i, question in enumerate(analysis.questions, 1):
                print(f"{i}. {question}")

        print("\n" + "=" * 80)

    def process_pdf(self, pdf_path: Path, output_path: Optional[Path] = None) -> PDFAnalysis:
        """
        Complete PDF processing pipeline

        Args:
            pdf_path: Path to PDF file
            output_path: Optional path to save JSON output

        Returns:
            PDFAnalysis object
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Extract content
        pages = self.extract_pdf_content(pdf_path)

        # Analyze with Sophia
        analysis = self.analyze_document(pdf_path, pages)

        # Print summary
        self.print_summary(analysis)

        # Save to file if output path provided
        if output_path:
            self.save_analysis(analysis, output_path)
        else:
            # Default output filename
            default_output = self.output_dir / f"{pdf_path.stem}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.save_analysis(analysis, default_output)

        return analysis


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze PDF documents using Sophia inference endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with environment variable
  export SOPHIA_ACCESS_TOKEN="your-token"
  python sophia_pdf_analyzer.py paper.pdf

  # Specify output file and config
  python sophia_pdf_analyzer.py paper.pdf --output analysis.json --config config/sophia.json

  # Process PDF and save to default location
  python sophia_pdf_analyzer.py research_paper.pdf
        """
    )

    parser.add_argument(
        "pdf_file",
        type=Path,
        help="Path to PDF file to analyze"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output JSON file path (default: output/<pdf_name>_analysis_<timestamp>.json)"
    )

    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("config/sophia.json"),
        help="Path to Sophia config file (default: config/sophia.json)"
    )

    args = parser.parse_args()

    # Validate PDF file
    if not args.pdf_file.exists():
        print(f"Error: PDF file not found: {args.pdf_file}")
        sys.exit(1)

    if not args.pdf_file.suffix.lower() == '.pdf':
        print(f"Error: File is not a PDF: {args.pdf_file}")
        sys.exit(1)

    try:
        # Initialize analyzer
        analyzer = SophiaPDFAnalyzer(config_path=args.config if args.config.exists() else None)

        # Process PDF
        analysis = analyzer.process_pdf(args.pdf_file, args.output)

        print("\nProcessing complete!")

    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("\nPlease ensure you have either:")
        print("  1. Set SOPHIA_ACCESS_TOKEN environment variable, or")
        print("  2. Added 'access_token' to config/sophia.json")
        sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
