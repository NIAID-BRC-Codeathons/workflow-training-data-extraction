"""
Tool Detector for Bioinformatics Software

Detects bioinformatics tools mentioned in scientific paper methods sections
using both regex patterns and LLM analysis.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path


@dataclass
class DetectedTool:
    """Represents a detected bioinformatics tool"""
    name: str
    version: Optional[str] = None
    confidence: float = 0.0
    context: str = ""  # Sentence/paragraph where tool was mentioned
    uri: Optional[str] = None  # bio.tools or container URI
    container: Optional[str] = None  # Docker/BioContainers image
    conda_package: Optional[str] = None
    parameters: Dict[str, str] = field(default_factory=dict)
    detection_method: str = "unknown"  # "regex" or "llm" or "both"


class ToolDetector:
    """Detect bioinformatics tools from paper text"""

    # Common bioinformatics tools with aliases
    TOOL_PATTERNS = {
        # Sequence analysis
        "BLAST": ["blast", "blastn", "blastp", "blastx", "tblastn"],
        "DIAMOND": ["diamond"],
        "HMMER": ["hmmer", "hmmsearch", "hmmbuild"],
        "Bowtie2": ["bowtie2", "bowtie"],
        "BWA": ["bwa", "bwa-mem"],

        # Quality control
        "FastQC": ["fastqc", "fast-qc"],
        "MultiQC": ["multiqc", "multi-qc"],
        "Trimmomatic": ["trimmomatic"],
        "Cutadapt": ["cutadapt"],

        # RNA-seq
        "STAR": ["star aligner", "star"],
        "HISAT2": ["hisat2", "hisat"],
        "Salmon": ["salmon"],
        "Kallisto": ["kallisto"],
        "DESeq2": ["deseq2", "deseq"],
        "edgeR": ["edger", "edge-r"],
        "featureCounts": ["featurecounts", "feature-counts"],

        # Assembly
        "SPAdes": ["spades"],
        "Trinity": ["trinity"],
        "MEGAHIT": ["megahit"],

        # Variant calling
        "GATK": ["gatk", "genome analysis toolkit"],
        "FreeBayes": ["freebayes"],
        "BCFtools": ["bcftools"],
        "SAMtools": ["samtools"],
        "VCFtools": ["vcftools"],

        # Alignment
        "MAFFT": ["mafft"],
        "MUSCLE": ["muscle"],
        "Clustal": ["clustal", "clustalw", "clustal omega"],

        # Statistical/Programming
        "R": ["r version", "r language", "\\br\\b"],
        "Python": ["python"],
        "Perl": ["perl"],
        "Bioconductor": ["bioconductor"],
        "ggplot2": ["ggplot2", "ggplot"],
        "pandas": ["pandas"],
        "NumPy": ["numpy"],
        "SciPy": ["scipy"],

        # Databases
        "NCBI": ["ncbi", "genbank"],
        "UniProt": ["uniprot"],
        "Pfam": ["pfam"],
        "RefSeq": ["refseq"],
    }

    # Container registries mapping
    CONTAINER_REGISTRY = {
        "BLAST": "docker://ncbi/blast:latest",
        "FastQC": "docker://biocontainers/fastqc:v0.11.9",
        "STAR": "docker://quay.io/biocontainers/star:2.7.10a",
        "SAMtools": "docker://biocontainers/samtools:1.15",
        "BWA": "docker://biocontainers/bwa:0.7.17",
        "Bowtie2": "docker://biocontainers/bowtie2:2.4.5",
        "Trimmomatic": "docker://biocontainers/trimmomatic:0.39",
        "SPAdes": "docker://quay.io/biocontainers/spades:3.15.5",
        "GATK": "docker://broadinstitute/gatk:latest",
    }

    # Bio.tools URIs
    BIOTOOLS_URI = {
        "BLAST": "bio.tools/blast",
        "FastQC": "bio.tools/fastqc",
        "STAR": "bio.tools/star",
        "SAMtools": "bio.tools/samtools",
        "BWA": "bio.tools/bwa",
        "Bowtie2": "bio.tools/bowtie2",
        "GATK": "bio.tools/gatk",
        "DESeq2": "bio.tools/deseq2",
    }

    def __init__(self, use_llm: bool = True, sophia_client=None):
        """
        Initialize tool detector

        Args:
            use_llm: Whether to use LLM for tool detection
            sophia_client: Optional SophiaClient instance for LLM-based detection
        """
        self.use_llm = use_llm
        self.sophia_client = sophia_client
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.compiled_patterns = {}

        for tool_name, aliases in self.TOOL_PATTERNS.items():
            # Create case-insensitive pattern matching any alias
            pattern_str = r'\b(' + '|'.join(re.escape(alias) for alias in aliases) + r')\b'
            self.compiled_patterns[tool_name] = re.compile(pattern_str, re.IGNORECASE)

    def detect_tools_regex(self, text: str) -> List[DetectedTool]:
        """
        Detect tools using regex pattern matching

        Args:
            text: Text to search for tool mentions

        Returns:
            List of DetectedTool objects
        """
        detected = []
        text_lower = text.lower()

        for tool_name, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)

            for match in matches:
                # Get context (surrounding text)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()

                # Try to extract version
                version = self._extract_version(context, match.group(1))

                # Try to extract parameters
                parameters = self._extract_parameters(context, tool_name)

                tool = DetectedTool(
                    name=tool_name,
                    version=version,
                    confidence=0.8,  # High confidence for regex matches
                    context=context,
                    uri=self.BIOTOOLS_URI.get(tool_name),
                    container=self.CONTAINER_REGISTRY.get(tool_name),
                    conda_package=f"bioconda::{tool_name.lower()}",
                    parameters=parameters,
                    detection_method="regex"
                )

                detected.append(tool)

        # Deduplicate tools (same tool mentioned multiple times)
        return self._deduplicate_tools(detected)

    def _extract_version(self, context: str, tool_mention: str) -> Optional[str]:
        """
        Extract tool version from context

        Looks for patterns like:
        - "FastQC v0.11.9"
        - "STAR (version 2.7.10)"
        - "samtools 1.15"
        """
        # Version patterns
        version_patterns = [
            rf"{re.escape(tool_mention)}\s+v?(\d+\.\d+(?:\.\d+)?)",
            rf"{re.escape(tool_mention)}\s+\(version\s+(\d+\.\d+(?:\.\d+)?)\)",
            rf"version\s+(\d+\.\d+(?:\.\d+)?)\s+of\s+{re.escape(tool_mention)}",
        ]

        context_lower = context.lower()
        tool_lower = tool_mention.lower()

        for pattern in version_patterns:
            match = re.search(pattern, context_lower)
            if match:
                return match.group(1)

        return None

    def _extract_parameters(self, context: str, tool_name: str) -> Dict[str, str]:
        """
        Extract tool parameters from context

        Looks for command-line flags and parameters
        """
        parameters = {}

        # Common parameter patterns
        # e.g., "--threads 8", "-p 0.001", "--min-quality 30"
        param_pattern = r'(?:^|\s)(--?\w+[-\w]*)\s+([^\s,;]+)'
        matches = re.finditer(param_pattern, context)

        for match in matches:
            param_name = match.group(1)
            param_value = match.group(2)
            parameters[param_name] = param_value

        return parameters

    def _deduplicate_tools(self, tools: List[DetectedTool]) -> List[DetectedTool]:
        """
        Deduplicate tools - keep highest confidence mention

        Args:
            tools: List of detected tools

        Returns:
            Deduplicated list
        """
        tool_dict = {}

        for tool in tools:
            key = tool.name

            if key not in tool_dict or tool.confidence > tool_dict[key].confidence:
                # Merge parameters if tool already exists
                if key in tool_dict:
                    # Combine parameters
                    existing_params = tool_dict[key].parameters
                    tool.parameters = {**existing_params, **tool.parameters}

                tool_dict[key] = tool

        return list(tool_dict.values())

    def detect_tools_llm(self, text: str) -> List[DetectedTool]:
        """
        Detect tools using LLM analysis

        Args:
            text: Text to analyze

        Returns:
            List of DetectedTool objects
        """
        if not self.use_llm or not self.sophia_client:
            return []

        try:
            from sophia_client import ChatMessage

            system_prompt = """You are a bioinformatics expert. Identify SPECIFIC SOFTWARE TOOLS ONLY from the methods text.

Look for:
- Software/program names (e.g., FastQC, STAR, BEAST, IQ-TREE, MAFFT, SPAdes, BWA, GATK, SAMtools)
- Programming languages/packages (e.g., R, Python, Bioconductor, NumPy)
- Databases (e.g., GenBank, NCBI, GISAID, UniProt)
- Analysis platforms (e.g., Galaxy, Nextflow, Snakemake)

DO NOT include:
- Generic methods (e.g., "phylogenetic reconstruction", "sequence alignment")
- Techniques (e.g., "PCR", "RNA extraction")
- Statistical methods without software (e.g., "maximum likelihood")
- Methodologies (e.g., "association index calculation")

Examples:
✓ "BEAST v2.6.7" → name: "BEAST", version: "2.6.7"
✓ "IQ-TREE with 1000 bootstrap" → name: "IQ-TREE", parameters: {"bootstrap": "1000"}
✓ "R version 4.1.2" → name: "R", version: "4.1.2"
✗ "phylogenetic analysis" → NOT a software tool
✗ "Bayesian inference" → NOT a software tool

Respond ONLY with valid JSON array (no other text):
[
  {"name": "BEAST", "version": "2.6.7", "parameters": {}, "confidence": "high"},
  {"name": "IQ-TREE", "version": null, "parameters": {"bootstrap": "1000"}, "confidence": "high"}
]

If no software tools found, return: []"""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Methods text:\n\n{text[:5000]}")  # Limit length
            ]

            response = self.sophia_client.chat_completion(
                messages,
                temperature=0.3,  # Lower temperature for more factual output
                max_tokens=2000
            )

            # Parse JSON response
            import json
            import re

            try:
                content = response.content.strip()

                # Remove markdown code blocks if present
                if '```json' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    content = content[start:end].strip()
                elif content.startswith('```'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1])

                # Try to extract just the JSON array if there's extra text
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)

                tools_data = json.loads(content)

                detected = []
                for tool_data in tools_data:
                    confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                    confidence = confidence_map.get(tool_data.get("confidence", "medium"), 0.6)

                    tool = DetectedTool(
                        name=tool_data["name"],
                        version=tool_data.get("version"),
                        confidence=confidence,
                        context=text[:200],  # Use beginning of text as context
                        uri=self.BIOTOOLS_URI.get(tool_data["name"]),
                        container=self.CONTAINER_REGISTRY.get(tool_data["name"]),
                        parameters=tool_data.get("parameters", {}),
                        detection_method="llm"
                    )
                    detected.append(tool)

                return detected

            except json.JSONDecodeError as e:
                # Try one more time - extract first complete JSON array
                try:
                    json_match = re.search(r'\[\s*\{.*?\}\s*\]', response.content, re.DOTALL)
                    if json_match:
                        tools_data = json.loads(json_match.group(0))
                        detected = []
                        for tool_data in tools_data:
                            confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                            confidence = confidence_map.get(tool_data.get("confidence", "medium"), 0.6)
                            tool = DetectedTool(
                                name=tool_data["name"],
                                version=tool_data.get("version"),
                                confidence=confidence,
                                context=text[:200],
                                uri=self.BIOTOOLS_URI.get(tool_data["name"]),
                                container=self.CONTAINER_REGISTRY.get(tool_data["name"]),
                                parameters=tool_data.get("parameters", {}),
                                detection_method="llm"
                            )
                            detected.append(tool)
                        return detected
                except:
                    pass

                print(f"Warning: Could not parse LLM response as JSON: {e}")
                print(f"Response was: {response.content[:300]}...")
                return []

        except Exception as e:
            print(f"Warning: LLM tool detection failed: {e}")
            return []

    def detect_tools(self, text: str) -> List[DetectedTool]:
        """
        Detect tools using both regex and LLM (if enabled)

        Args:
            text: Text to analyze

        Returns:
            Combined list of detected tools
        """
        # Regex detection
        regex_tools = self.detect_tools_regex(text)

        # LLM detection
        llm_tools = self.detect_tools_llm(text) if self.use_llm else []

        # Merge results
        all_tools = {}

        # Add regex tools
        for tool in regex_tools:
            all_tools[tool.name] = tool

        # Merge LLM tools
        for tool in llm_tools:
            if tool.name in all_tools:
                # Tool detected by both methods - increase confidence
                existing = all_tools[tool.name]
                existing.confidence = min(0.95, (existing.confidence + tool.confidence) / 2 + 0.1)
                existing.detection_method = "both"

                # Merge parameters
                existing.parameters = {**existing.parameters, **tool.parameters}

                # Use LLM version if regex didn't find one
                if not existing.version and tool.version:
                    existing.version = tool.version
            else:
                # New tool from LLM
                all_tools[tool.name] = tool

        # Sort by confidence
        sorted_tools = sorted(all_tools.values(), key=lambda t: t.confidence, reverse=True)

        return sorted_tools

    def enrich_tool_metadata(self, tool: DetectedTool) -> DetectedTool:
        """
        Enrich tool with additional metadata (URIs, containers)

        Args:
            tool: Tool to enrich

        Returns:
            Enriched tool
        """
        # Add bio.tools URI if not present
        if not tool.uri and tool.name in self.BIOTOOLS_URI:
            tool.uri = self.BIOTOOLS_URI[tool.name]

        # Add container if not present
        if not tool.container and tool.name in self.CONTAINER_REGISTRY:
            tool.container = self.CONTAINER_REGISTRY[tool.name]

        # Add conda package
        if not tool.conda_package:
            tool.conda_package = f"bioconda::{tool.name.lower()}"

        return tool

    def tools_to_dict(self, tools: List[DetectedTool]) -> List[Dict]:
        """
        Convert tools to dictionary format for JSON serialization

        Args:
            tools: List of DetectedTool objects

        Returns:
            List of dictionaries
        """
        return [
            {
                "name": tool.name,
                "version": tool.version or "unspecified",
                "confidence": tool.confidence,
                "uri": tool.uri,
                "container": tool.container,
                "conda_package": tool.conda_package,
                "parameters": tool.parameters,
                "detection_method": tool.detection_method,
                "context_snippet": tool.context[:100] + "..." if len(tool.context) > 100 else tool.context
            }
            for tool in tools
        ]


# Standalone usage
if __name__ == "__main__":
    import sys

    # Example usage
    methods_text = """
    RNA-seq reads were quality-checked using FastQC v0.11.9 with default parameters.
    Adapter sequences were trimmed using Trimmomatic (version 0.39) with the following
    settings: ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 LEADING:3 TRAILING:3 MINLEN:36.
    Cleaned reads were aligned to the reference genome using STAR aligner (version 2.7.10a)
    with --outFilterMultimapNmax 20 --alignSJoverhangMin 8.
    Read counts were generated using featureCounts from the Subread package.
    Differential expression analysis was performed using DESeq2 (version 1.34.0) in R.
    """

    detector = ToolDetector(use_llm=False)  # LLM disabled for this example
    tools = detector.detect_tools(methods_text)

    print(f"Detected {len(tools)} tools:\n")
    for tool in tools:
        print(f"  - {tool.name}")
        if tool.version:
            print(f"    Version: {tool.version}")
        print(f"    Confidence: {tool.confidence:.2f}")
        print(f"    Container: {tool.container or 'Not found'}")
        if tool.parameters:
            print(f"    Parameters: {tool.parameters}")
        print()
