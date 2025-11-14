"""
Workflow Extractor for Scientific Papers

Extracts structured workflow steps from Methods sections, identifying:
- Sequential analysis steps
- Input/output relationships
- Tool associations for each step
- Parameters and data transformations
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from tool_detector import DetectedTool, ToolDetector


class StepType(Enum):
    """Types of workflow steps"""
    DATA_ACQUISITION = "data_acquisition"
    QUALITY_CONTROL = "quality_control"
    PREPROCESSING = "preprocessing"
    ALIGNMENT = "alignment"
    ASSEMBLY = "assembly"
    ANALYSIS = "analysis"
    STATISTICAL = "statistical"
    VISUALIZATION = "visualization"
    VALIDATION = "validation"
    OTHER = "other"


@dataclass
class WorkflowStep:
    """Represents a single step in the analysis workflow"""
    step_number: int
    name: str
    description: str
    step_type: StepType
    input_data: List[str] = field(default_factory=list)  # Input from previous steps
    output_data: List[str] = field(default_factory=list)  # Output to next steps
    tools: List[DetectedTool] = field(default_factory=list)  # Tools used in this step
    parameters: Dict[str, str] = field(default_factory=dict)  # Step-specific parameters
    substeps: List[str] = field(default_factory=list)  # Detailed substeps
    confidence: float = 0.0
    source_text: str = ""  # Original text this step was extracted from


class WorkflowExtractor:
    """Extract workflow steps from Methods text"""

    # Keywords indicating workflow steps
    STEP_INDICATORS = [
        # Sequential indicators
        r'\b(first|initially|then|next|subsequently|finally|lastly)\b',
        r'\b(step\s+\d+|stage\s+\d+)\b',
        r'\b(followed\s+by|after|before)\b',

        # Process indicators
        r'\b(performed|conducted|analyzed|processed|extracted|sequenced)\b',
        r'\b(filtered|aligned|assembled|mapped|called|normalized)\b',
        r'\b(calculated|computed|generated|identified|detected)\b',
    ]

    # Keywords for step types
    STEP_TYPE_KEYWORDS = {
        StepType.DATA_ACQUISITION: [
            'collected', 'obtained', 'downloaded', 'retrieved', 'acquired',
            'sequenced', 'generated', 'recorded', 'measured'
        ],
        StepType.QUALITY_CONTROL: [
            'quality', 'qc', 'assessed', 'checked', 'validated', 'verified',
            'fastqc', 'multiqc', 'quality control', 'quality assessment'
        ],
        StepType.PREPROCESSING: [
            'trimmed', 'filtered', 'cleaned', 'removed', 'preprocessed',
            'adapter', 'trimming', 'filtering', 'normalization'
        ],
        StepType.ALIGNMENT: [
            'aligned', 'mapped', 'alignment', 'mapping', 'indexed',
            'bwa', 'bowtie', 'star', 'hisat', 'blast'
        ],
        StepType.ASSEMBLY: [
            'assembled', 'assembly', 'scaffolding', 'contigs', 'scaffolds',
            'spades', 'trinity', 'megahit', 'canu'
        ],
        StepType.ANALYSIS: [
            'analyzed', 'identified', 'detected', 'annotated', 'classified',
            'differential', 'expression', 'variant', 'calling'
        ],
        StepType.STATISTICAL: [
            'statistical', 'significance', 'p-value', 'correlation', 'regression',
            't-test', 'anova', 'fisher', 'wilcoxon', 'mann-whitney'
        ],
        StepType.VISUALIZATION: [
            'plotted', 'visualized', 'graphed', 'displayed', 'rendered',
            'figure', 'plot', 'graph', 'chart', 'heatmap'
        ],
        StepType.VALIDATION: [
            'validated', 'confirmed', 'verified', 'replicated', 'compared',
            'benchmarked', 'evaluated', 'assessed'
        ]
    }

    # Data type patterns
    DATA_PATTERNS = {
        'reads': r'\b(reads?|sequences?|fastq|fasta)\b',
        'genome': r'\b(genome|reference|assembly|scaffold)\b',
        'alignment': r'\b(bam|sam|alignment|mapping)\b',
        'variants': r'\b(vcf|variants?|snps?|indels?|mutations?)\b',
        'expression': r'\b(counts?|expression|fpkm|tpm|rpkm)\b',
        'annotation': r'\b(gff|gtf|bed|annotation)\b'
    }

    def __init__(self, use_llm: bool = True, sophia_client=None):
        """
        Initialize workflow extractor

        Args:
            use_llm: Whether to use LLM for step extraction
            sophia_client: Optional SophiaClient for LLM-based extraction
        """
        self.use_llm = use_llm
        self.sophia_client = sophia_client
        self.tool_detector = ToolDetector(use_llm=use_llm, sophia_client=sophia_client)

    def extract_workflow(self, methods_text: str, detected_tools: Optional[List[DetectedTool]] = None) -> List[WorkflowStep]:
        """
        Extract workflow steps from methods text

        Args:
            methods_text: Text from Methods section
            detected_tools: Optional list of already detected tools

        Returns:
            List of WorkflowStep objects in sequential order
        """
        # Detect tools if not provided
        if detected_tools is None:
            detected_tools = self.tool_detector.detect_tools(methods_text)

        # Extract steps using both methods
        heuristic_steps = self._extract_steps_heuristic(methods_text, detected_tools)

        if self.use_llm:
            llm_steps = self._extract_steps_llm(methods_text, detected_tools)
            steps = self._merge_steps(heuristic_steps, llm_steps)
        else:
            steps = heuristic_steps

        # Link steps (identify inputs/outputs)
        steps = self._link_steps(steps)

        # Sort by step number
        steps.sort(key=lambda s: s.step_number)

        return steps

    def _extract_steps_heuristic(self, text: str, tools: List[DetectedTool]) -> List[WorkflowStep]:
        """
        Extract steps using pattern matching

        Args:
            text: Methods text
            tools: Detected tools

        Returns:
            List of workflow steps
        """
        steps = []

        # Split into sentences
        sentences = self._split_into_sentences(text)

        # Group sentences into potential steps
        step_groups = self._group_sentences_into_steps(sentences)

        # Process each step group
        for i, group in enumerate(step_groups, 1):
            step_text = ' '.join(group)

            # Determine step type
            step_type = self._classify_step_type(step_text)

            # Extract step name
            step_name = self._extract_step_name(step_text, step_type)

            # Find associated tools
            step_tools = self._find_tools_in_text(step_text, tools)

            # Extract parameters
            parameters = self._extract_parameters(step_text)

            # Extract data types
            input_data, output_data = self._extract_data_types(step_text)

            # Create step
            step = WorkflowStep(
                step_number=i,
                name=step_name,
                description=step_text[:200],  # First 200 chars as description
                step_type=step_type,
                input_data=input_data,
                output_data=output_data,
                tools=step_tools,
                parameters=parameters,
                confidence=0.7,  # Moderate confidence for heuristic
                source_text=step_text
            )

            steps.append(step)

        return steps

    def _extract_steps_llm(self, text: str, tools: List[DetectedTool]) -> List[WorkflowStep]:
        """
        Extract steps using LLM

        Args:
            text: Methods text
            tools: Detected tools

        Returns:
            List of workflow steps
        """
        if not self.sophia_client:
            return []

        try:
            from sophia_client import ChatMessage
            import json

            system_prompt = """You are analyzing a scientific methods section to extract workflow steps.

For each distinct analysis step, provide:
1. Step name (brief, descriptive)
2. Step type (data_acquisition, quality_control, preprocessing, alignment, assembly, analysis, statistical, visualization, validation, other)
3. Description (what happens in this step)
4. Input data (what this step receives from previous steps)
5. Output data (what this step produces for next steps)
6. Parameters (key parameters mentioned)

Format as JSON array:
[
  {
    "name": "Quality Control",
    "type": "quality_control",
    "description": "Assess read quality using FastQC",
    "inputs": ["raw_reads"],
    "outputs": ["quality_report"],
    "parameters": {"min_quality": "30", "min_length": "50"}
  }
]

Focus on major computational/analysis steps. Ignore sample collection details."""

            # Limit text length for LLM
            text_for_llm = text[:5000] if len(text) > 5000 else text

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Methods text:\n\n{text_for_llm}")
            ]

            response = self.sophia_client.chat_completion(
                messages,
                temperature=0.3,
                max_tokens=2000
            )

            # Parse response
            steps_data = self._parse_llm_response(response.content)

            steps = []
            for i, step_data in enumerate(steps_data, 1):
                # Map type string to enum
                type_str = step_data.get('type', 'other')
                step_type = self._map_step_type(type_str)

                # Find associated tools
                step_name = step_data.get('name', f'Step {i}')
                step_tools = self._find_tools_for_step(step_name, step_data.get('description', ''), tools)

                step = WorkflowStep(
                    step_number=i,
                    name=step_name,
                    description=step_data.get('description', ''),
                    step_type=step_type,
                    input_data=step_data.get('inputs', []),
                    output_data=step_data.get('outputs', []),
                    tools=step_tools,
                    parameters=step_data.get('parameters', {}),
                    confidence=0.85,  # High confidence for LLM
                    source_text=step_data.get('description', '')
                )

                steps.append(step)

            return steps

        except Exception as e:
            print(f"Warning: LLM step extraction failed: {e}")
            return []

    def _parse_llm_response(self, response: str) -> List[Dict]:
        """Parse LLM JSON response"""
        import json
        import re

        try:
            # Clean response
            content = response.strip()

            # Remove markdown if present
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                content = content[start:end].strip()
            elif '```' in content:
                content = re.sub(r'```[^\n]*\n', '', content)
                content = re.sub(r'```', '', content)

            # Extract JSON array
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            return json.loads(content)

        except json.JSONDecodeError:
            print("Warning: Could not parse LLM response as JSON")
            return []

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _group_sentences_into_steps(self, sentences: List[str]) -> List[List[str]]:
        """Group sentences that likely belong to same step"""
        groups = []
        current_group = []

        for sentence in sentences:
            # Check if sentence starts a new step
            if self._is_step_boundary(sentence) and current_group:
                groups.append(current_group)
                current_group = [sentence]
            else:
                current_group.append(sentence)

        if current_group:
            groups.append(current_group)

        return groups

    def _is_step_boundary(self, sentence: str) -> bool:
        """Check if sentence likely starts a new step"""
        sentence_lower = sentence.lower()

        # Check for step indicators
        for pattern in self.STEP_INDICATORS[:5]:  # Check first 5 patterns
            if re.search(pattern, sentence_lower):
                return True

        return False

    def _classify_step_type(self, text: str) -> StepType:
        """Classify the type of workflow step"""
        text_lower = text.lower()

        # Count keyword matches for each type
        type_scores = {}

        for step_type, keywords in self.STEP_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                type_scores[step_type] = score

        # Return type with highest score
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]

        return StepType.OTHER

    def _extract_step_name(self, text: str, step_type: StepType) -> str:
        """Extract a concise name for the step"""
        # Try to extract first verb phrase
        verb_match = re.search(r'\b(performed?|conducted?|analyzed?|processed?|extracted?|' +
                              r'filtered?|aligned?|assembled?|calculated?|generated?)\s+(\w+)',
                              text, re.IGNORECASE)

        if verb_match:
            return f"{verb_match.group(1).capitalize()} {verb_match.group(2)}"

        # Fallback to step type
        return step_type.value.replace('_', ' ').title()

    def _find_tools_in_text(self, text: str, all_tools: List[DetectedTool]) -> List[DetectedTool]:
        """Find which tools are mentioned in this text"""
        found_tools = []
        text_lower = text.lower()

        for tool in all_tools:
            if tool.name.lower() in text_lower:
                found_tools.append(tool)

        return found_tools

    def _find_tools_for_step(self, step_name: str, description: str, all_tools: List[DetectedTool]) -> List[DetectedTool]:
        """Find tools associated with a step"""
        combined_text = f"{step_name} {description}".lower()
        return self._find_tools_in_text(combined_text, all_tools)

    def _extract_parameters(self, text: str) -> Dict[str, str]:
        """Extract parameters from step text"""
        parameters = {}

        # Common parameter patterns
        patterns = [
            r'(\w+)\s*=\s*([^\s,;]+)',  # param = value
            r'--(\w+)\s+([^\s,;]+)',     # --param value
            r'-(\w)\s+([^\s,;]+)',       # -p value
            r'(\w+):\s*([^\s,;]+)',      # param: value
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for param, value in matches:
                parameters[param] = value

        return parameters

    def _extract_data_types(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract input and output data types from text"""
        inputs = []
        outputs = []

        text_lower = text.lower()

        # Check for data type mentions
        for data_type, pattern in self.DATA_PATTERNS.items():
            if re.search(pattern, text_lower):
                # Try to determine if input or output
                if re.search(rf'(input|from|using|with)\s+.*{pattern}', text_lower):
                    inputs.append(data_type)
                elif re.search(rf'(output|produced?|generated?|resulted?)\s+.*{pattern}', text_lower):
                    outputs.append(data_type)
                else:
                    # Default to input for most data types
                    inputs.append(data_type)

        return inputs, outputs

    def _merge_steps(self, heuristic_steps: List[WorkflowStep], llm_steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Merge steps from heuristic and LLM extraction"""
        if not llm_steps:
            return heuristic_steps

        if not heuristic_steps:
            return llm_steps

        # For now, prefer LLM steps if confidence is higher
        # In future, could do more sophisticated merging
        return llm_steps if llm_steps else heuristic_steps

    def _link_steps(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """
        Link workflow steps by identifying data flow

        Args:
            steps: List of workflow steps

        Returns:
            Steps with updated input/output relationships
        """
        # Simple linking: assume outputs of step N are inputs to step N+1
        for i in range(len(steps) - 1):
            current_step = steps[i]
            next_step = steps[i + 1]

            # If next step has no inputs, use current step's outputs
            if not next_step.input_data and current_step.output_data:
                next_step.input_data = current_step.output_data.copy()

            # If current step has no outputs, infer from next step's inputs
            if not current_step.output_data and next_step.input_data:
                current_step.output_data = next_step.input_data.copy()

        return steps

    def _map_step_type(self, type_str: str) -> StepType:
        """Map string to StepType enum"""
        type_map = {
            'data_acquisition': StepType.DATA_ACQUISITION,
            'quality_control': StepType.QUALITY_CONTROL,
            'preprocessing': StepType.PREPROCESSING,
            'alignment': StepType.ALIGNMENT,
            'assembly': StepType.ASSEMBLY,
            'analysis': StepType.ANALYSIS,
            'statistical': StepType.STATISTICAL,
            'visualization': StepType.VISUALIZATION,
            'validation': StepType.VALIDATION,
        }
        return type_map.get(type_str.lower(), StepType.OTHER)

    def workflow_to_dict(self, steps: List[WorkflowStep]) -> List[Dict]:
        """
        Convert workflow steps to dictionary format for JSON serialization

        Args:
            steps: List of WorkflowStep objects

        Returns:
            List of dictionaries
        """
        return [
            {
                "step": step.step_number,
                "name": step.name,
                "type": step.step_type.value,
                "description": step.description,
                "inputs": step.input_data,
                "outputs": step.output_data,
                "tools": [tool.name for tool in step.tools],
                "parameters": step.parameters,
                "substeps": step.substeps,
                "confidence": step.confidence
            }
            for step in steps
        ]


# Standalone usage
if __name__ == "__main__":
    # Example usage
    methods_text = """
    RNA-seq reads were first quality-checked using FastQC v0.11.9.
    Low-quality bases and adapter sequences were trimmed using Trimmomatic
    with parameters LEADING:3 TRAILING:3 MINLEN:36.
    Cleaned reads were then aligned to the reference genome using STAR aligner
    version 2.7.10a with default parameters.
    Gene expression levels were quantified using featureCounts.
    Differential expression analysis was performed using DESeq2 in R.
    """

    extractor = WorkflowExtractor(use_llm=False)
    steps = extractor.extract_workflow(methods_text)

    print(f"Extracted {len(steps)} workflow steps:\n")
    for step in steps:
        print(f"Step {step.step_number}: {step.name}")
        print(f"  Type: {step.step_type.value}")
        print(f"  Tools: {[t.name for t in step.tools]}")
        print(f"  Inputs: {step.input_data}")
        print(f"  Outputs: {step.output_data}")
        print()