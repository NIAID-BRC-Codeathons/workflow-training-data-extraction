#!/usr/bin/env python3
"""
Q2A Assembler - Combine extracted components into Q2A training data format

This module assembles the final Q2A JSON document by combining:
- Paper sections (from section_identifier.py)
- Detected tools (from tool_detector.py)
- Workflow steps (from workflow_extractor.py)
- Pedagogical hints and gaps

The Q2A format is designed for training LLMs to understand and generate
bioinformatics workflows from scientific papers.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
import json
from pathlib import Path

from section_identifier import PaperSection, SectionType
from tool_detector import DetectedTool
from workflow_extractor import WorkflowStep, StepType


class QuestionType(Enum):
    """Types of questions in Q2A format"""
    RESEARCH_OBJECTIVE = "research_objective"
    HYPOTHESIS = "hypothesis"
    WORKFLOW = "workflow"
    TOOL_USAGE = "tool_usage"
    PARAMETER = "parameter"
    DATA_TRANSFORMATION = "data_transformation"
    RESULT_INTERPRETATION = "result_interpretation"


class GapType(Enum):
    """Types of information gaps"""
    MISSING_VERSION = "missing_version"
    MISSING_PARAMETER = "missing_parameter"
    MISSING_FILE_PATH = "missing_file_path"
    MISSING_CONTAINER = "missing_container"
    MISSING_INPUT = "missing_input"
    MISSING_OUTPUT = "missing_output"
    AMBIGUOUS_STEP = "ambiguous_step"
    UNCLEAR_DEPENDENCY = "unclear_dependency"


@dataclass
class InformationGap:
    """Represents missing or unclear information"""
    gap_type: GapType
    description: str
    affected_step: Optional[int] = None
    affected_tool: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    suggested_resolution: Optional[str] = None


@dataclass
class PedagogicalHint:
    """Hints for understanding workflow steps"""
    hint_type: str  # explanation, warning, best_practice, alternative
    content: str
    related_step: Optional[int] = None
    related_tool: Optional[str] = None


@dataclass
class Q2APair:
    """Question-Answer pair in Q2A format"""
    question_id: str
    question_type: QuestionType
    question: str
    answer: str
    context: Dict[str, Any]
    confidence: float
    hints: List[PedagogicalHint]
    gaps: List[InformationGap]
    source_section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "question_id": self.question_id,
            "question_type": self.question_type.value,
            "question": self.question,
            "answer": self.answer,
            "context": self.context,
            "confidence": self.confidence,
            "hints": [
                {
                    "type": h.hint_type,
                    "content": h.content,
                    "related_step": h.related_step,
                    "related_tool": h.related_tool
                }
                for h in self.hints
            ],
            "gaps": [
                {
                    "type": g.gap_type.value,
                    "description": g.description,
                    "affected_step": g.affected_step,
                    "affected_tool": g.affected_tool,
                    "severity": g.severity,
                    "suggested_resolution": g.suggested_resolution
                }
                for g in self.gaps
            ],
            "source_section": self.source_section
        }


@dataclass
class Q2ADocument:
    """Complete Q2A training document"""
    document_id: str
    paper_metadata: Dict[str, Any]
    qa_pairs: List[Q2APair]
    workflow_summary: Dict[str, Any]
    tools_summary: List[Dict[str, Any]]
    overall_gaps: List[InformationGap]
    extraction_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "document_id": self.document_id,
            "paper_metadata": self.paper_metadata,
            "qa_pairs": [qa.to_dict() for qa in self.qa_pairs],
            "workflow_summary": self.workflow_summary,
            "tools_summary": self.tools_summary,
            "overall_gaps": [
                {
                    "type": g.gap_type.value,
                    "description": g.description,
                    "affected_step": g.affected_step,
                    "affected_tool": g.affected_tool,
                    "severity": g.severity,
                    "suggested_resolution": g.suggested_resolution
                }
                for g in self.overall_gaps
            ],
            "extraction_metadata": self.extraction_metadata
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, output_path: Path):
        """Save to JSON file"""
        with open(output_path, 'w') as f:
            f.write(self.to_json())


class Q2AAssembler:
    """Assemble Q2A documents from extracted components"""

    def __init__(self, paper_id: str, pdf_paths: List[Path]):
        """
        Initialize assembler

        Args:
            paper_id: Unique identifier for the paper
            pdf_paths: List of PDF paths (main paper + supplementary)
        """
        self.paper_id = paper_id
        self.pdf_paths = pdf_paths

    def assemble(
        self,
        sections: Dict[SectionType, PaperSection],
        tools: List[DetectedTool],
        workflow_steps: List[WorkflowStep],
        paper_metadata: Optional[Dict[str, Any]] = None
    ) -> Q2ADocument:
        """
        Assemble complete Q2A document

        Args:
            sections: Extracted paper sections
            tools: Detected tools
            workflow_steps: Extracted workflow steps
            paper_metadata: Optional metadata (title, authors, DOI, etc.)

        Returns:
            Complete Q2A document
        """
        # Default metadata
        if paper_metadata is None:
            paper_metadata = {}

        paper_metadata.update({
            "paper_id": self.paper_id,
            "source_pdfs": [str(p) for p in self.pdf_paths],
            "sections_found": [st.value for st in sections.keys()]
        })

        # Generate Q&A pairs
        qa_pairs = []

        # 1. Research objective questions (from Introduction/Abstract)
        qa_pairs.extend(self._generate_objective_questions(sections))

        # 2. Workflow questions (from Methods + workflow steps)
        qa_pairs.extend(self._generate_workflow_questions(sections, workflow_steps, tools))

        # 3. Tool usage questions
        qa_pairs.extend(self._generate_tool_questions(tools, workflow_steps))

        # 4. Parameter questions
        qa_pairs.extend(self._generate_parameter_questions(workflow_steps, tools))

        # 5. Data transformation questions
        qa_pairs.extend(self._generate_data_transformation_questions(workflow_steps))

        # Workflow summary
        workflow_summary = self._create_workflow_summary(workflow_steps)

        # Tools summary
        tools_summary = self._create_tools_summary(tools)

        # Detect overall gaps
        overall_gaps = self._detect_overall_gaps(tools, workflow_steps)

        # Extraction metadata
        extraction_metadata = {
            "num_sections": len(sections),
            "num_tools": len(tools),
            "num_workflow_steps": len(workflow_steps),
            "num_qa_pairs": len(qa_pairs),
            "avg_confidence": sum(qa.confidence for qa in qa_pairs) / len(qa_pairs) if qa_pairs else 0.0
        }

        return Q2ADocument(
            document_id=self.paper_id,
            paper_metadata=paper_metadata,
            qa_pairs=qa_pairs,
            workflow_summary=workflow_summary,
            tools_summary=tools_summary,
            overall_gaps=overall_gaps,
            extraction_metadata=extraction_metadata
        )

    def _generate_objective_questions(
        self,
        sections: Dict[SectionType, PaperSection]
    ) -> List[Q2APair]:
        """Generate questions about research objectives"""
        qa_pairs = []

        # Get introduction or abstract
        intro = sections.get(SectionType.INTRODUCTION)
        abstract = sections.get(SectionType.ABSTRACT)

        source_section = intro or abstract
        if not source_section:
            return qa_pairs

        # Extract first 500 chars as context
        context_text = source_section.content[:500].strip()

        # Q1: What is the main research objective?
        qa_pairs.append(Q2APair(
            question_id=f"{self.paper_id}_obj_01",
            question_type=QuestionType.RESEARCH_OBJECTIVE,
            question="What is the main research objective of this study?",
            answer=f"Based on the {source_section.title}, the study aims to: {context_text}",
            context={"section": source_section.title, "text": context_text},
            confidence=source_section.confidence,
            hints=[
                PedagogicalHint(
                    hint_type="explanation",
                    content="Research objectives define the goals and scope of the computational analysis"
                )
            ],
            gaps=[],
            source_section=source_section.title
        ))

        return qa_pairs

    def _generate_workflow_questions(
        self,
        sections: Dict[SectionType, PaperSection],
        workflow_steps: List[WorkflowStep],
        tools: List[DetectedTool]
    ) -> List[Q2APair]:
        """Generate questions about the overall workflow"""
        qa_pairs = []

        if not workflow_steps:
            return qa_pairs

        methods = sections.get(SectionType.METHODS)

        # Q: Describe the computational workflow
        workflow_description = "\n".join([
            f"Step {step.step_number}: {step.name} ({step.step_type.value})"
            for step in workflow_steps
        ])

        # Detect gaps in workflow
        gaps = []
        for step in workflow_steps:
            if not step.tools:
                gaps.append(InformationGap(
                    gap_type=GapType.AMBIGUOUS_STEP,
                    description=f"No specific tools identified for step {step.step_number}",
                    affected_step=step.step_number,
                    severity="medium"
                ))

            if not step.input_data:
                gaps.append(InformationGap(
                    gap_type=GapType.MISSING_INPUT,
                    description=f"Input data not specified for step {step.step_number}",
                    affected_step=step.step_number,
                    severity="low"
                ))

        qa_pairs.append(Q2APair(
            question_id=f"{self.paper_id}_wf_01",
            question_type=QuestionType.WORKFLOW,
            question="Describe the complete computational workflow used in this study.",
            answer=f"The workflow consists of {len(workflow_steps)} main steps:\n\n{workflow_description}",
            context={
                "num_steps": len(workflow_steps),
                "num_tools": len(tools),
                "step_types": [step.step_type.value for step in workflow_steps]
            },
            confidence=sum(step.confidence for step in workflow_steps) / len(workflow_steps),
            hints=[
                PedagogicalHint(
                    hint_type="explanation",
                    content="Bioinformatics workflows typically follow a pattern: data acquisition → quality control → preprocessing → analysis → interpretation"
                )
            ],
            gaps=gaps,
            source_section=methods.title if methods else "Methods"
        ))

        return qa_pairs

    def _generate_tool_questions(
        self,
        tools: List[DetectedTool],
        workflow_steps: List[WorkflowStep]
    ) -> List[Q2APair]:
        """Generate questions about specific tools"""
        qa_pairs = []

        for i, tool in enumerate(tools[:5], 1):  # Top 5 tools
            # Find which step uses this tool
            step_nums = []
            for step in workflow_steps:
                if any(t.name == tool.name for t in step.tools):
                    step_nums.append(step.step_number)

            # Detect gaps
            gaps = []
            if not tool.version:
                gaps.append(InformationGap(
                    gap_type=GapType.MISSING_VERSION,
                    description=f"Version not specified for {tool.name}",
                    affected_tool=tool.name,
                    severity="medium",
                    suggested_resolution="Check Methods section or tool documentation"
                ))

            if not tool.container:
                gaps.append(InformationGap(
                    gap_type=GapType.MISSING_CONTAINER,
                    description=f"Container not specified for {tool.name}",
                    affected_tool=tool.name,
                    severity="low",
                    suggested_resolution="Check BioContainers or Docker Hub"
                ))

            version_str = f"version {tool.version}" if tool.version else "unspecified version"

            qa_pairs.append(Q2APair(
                question_id=f"{self.paper_id}_tool_{i:02d}",
                question_type=QuestionType.TOOL_USAGE,
                question=f"What is {tool.name} and how is it used in this workflow?",
                answer=f"{tool.name} ({version_str}) is used in step(s) {step_nums if step_nums else 'unspecified'}. Context: {tool.context[:200]}",
                context={
                    "tool_name": tool.name,
                    "version": tool.version,
                    "detection_method": tool.detection_method,
                    "confidence": tool.confidence,
                    "steps": step_nums,
                    "container": tool.container,
                    "uri": tool.uri
                },
                confidence=tool.confidence,
                hints=[
                    PedagogicalHint(
                        hint_type="explanation",
                        content=f"Tool category: {tool.category if hasattr(tool, 'category') else 'bioinformatics'}"
                    )
                ],
                gaps=gaps,
                source_section="Methods"
            ))

        return qa_pairs

    def _generate_parameter_questions(
        self,
        workflow_steps: List[WorkflowStep],
        tools: List[DetectedTool]
    ) -> List[Q2APair]:
        """Generate questions about parameters"""
        qa_pairs = []

        for step in workflow_steps:
            if not step.parameters:
                continue

            # Only create questions for steps with significant parameters
            if len(step.parameters) < 2:
                continue

            gaps = []
            if len(step.parameters) < 3:
                gaps.append(InformationGap(
                    gap_type=GapType.MISSING_PARAMETER,
                    description=f"Some parameters may not be explicitly stated for {step.name}",
                    affected_step=step.step_number,
                    severity="low"
                ))

            params_str = ", ".join([f"{k}={v}" for k, v in list(step.parameters.items())[:5]])

            qa_pairs.append(Q2APair(
                question_id=f"{self.paper_id}_param_{step.step_number:02d}",
                question_type=QuestionType.PARAMETER,
                question=f"What parameters are used in the '{step.name}' step?",
                answer=f"The following parameters are used: {params_str}",
                context={
                    "step": step.step_number,
                    "step_name": step.name,
                    "parameters": step.parameters,
                    "tools": [t.name for t in step.tools]
                },
                confidence=step.confidence,
                hints=[
                    PedagogicalHint(
                        hint_type="best_practice",
                        content="Document all parameters for reproducibility"
                    )
                ],
                gaps=gaps,
                source_section="Methods"
            ))

        return qa_pairs

    def _generate_data_transformation_questions(
        self,
        workflow_steps: List[WorkflowStep]
    ) -> List[Q2APair]:
        """Generate questions about data transformations"""
        qa_pairs = []

        for step in workflow_steps:
            if not step.input_data or not step.output_data:
                continue

            gaps = []
            if not step.tools:
                gaps.append(InformationGap(
                    gap_type=GapType.AMBIGUOUS_STEP,
                    description=f"Tools not specified for transformation in step {step.step_number}",
                    affected_step=step.step_number,
                    severity="medium"
                ))

            input_str = ", ".join(step.input_data)
            output_str = ", ".join(step.output_data)

            qa_pairs.append(Q2APair(
                question_id=f"{self.paper_id}_trans_{step.step_number:02d}",
                question_type=QuestionType.DATA_TRANSFORMATION,
                question=f"How is data transformed in the '{step.name}' step?",
                answer=f"This step takes {input_str} as input and produces {output_str} as output using {[t.name for t in step.tools] if step.tools else 'unspecified tools'}.",
                context={
                    "step": step.step_number,
                    "step_type": step.step_type.value,
                    "input": step.input_data,
                    "output": step.output_data,
                    "tools": [t.name for t in step.tools]
                },
                confidence=step.confidence,
                hints=[
                    PedagogicalHint(
                        hint_type="explanation",
                        content="Understanding data transformations is key to reproducing workflows"
                    )
                ],
                gaps=gaps,
                source_section="Methods"
            ))

        return qa_pairs

    def _create_workflow_summary(
        self,
        workflow_steps: List[WorkflowStep]
    ) -> Dict[str, Any]:
        """Create workflow summary"""
        if not workflow_steps:
            return {}

        # Count step types
        step_type_counts = {}
        for step in workflow_steps:
            step_type = step.step_type.value
            step_type_counts[step_type] = step_type_counts.get(step_type, 0) + 1

        return {
            "total_steps": len(workflow_steps),
            "step_types": step_type_counts,
            "avg_confidence": sum(s.confidence for s in workflow_steps) / len(workflow_steps),
            "steps": [
                {
                    "number": s.step_number,
                    "name": s.name,
                    "type": s.step_type.value,
                    "num_tools": len(s.tools),
                    "num_parameters": len(s.parameters) if s.parameters else 0
                }
                for s in workflow_steps
            ]
        }

    def _create_tools_summary(
        self,
        tools: List[DetectedTool]
    ) -> List[Dict[str, Any]]:
        """Create tools summary"""
        return [
            {
                "name": t.name,
                "version": t.version,
                "confidence": t.confidence,
                "detection_method": t.detection_method,
                "has_container": t.container is not None,
                "has_uri": t.uri is not None,
                "num_parameters": len(t.parameters) if t.parameters else 0
            }
            for t in tools
        ]

    def _detect_overall_gaps(
        self,
        tools: List[DetectedTool],
        workflow_steps: List[WorkflowStep]
    ) -> List[InformationGap]:
        """Detect overall information gaps"""
        gaps = []

        # Missing versions
        tools_without_version = [t for t in tools if not t.version]
        if tools_without_version:
            gaps.append(InformationGap(
                gap_type=GapType.MISSING_VERSION,
                description=f"{len(tools_without_version)} tools without version information: {', '.join(t.name for t in tools_without_version[:3])}",
                severity="medium",
                suggested_resolution="Check supplementary materials or contact authors"
            ))

        # Missing containers
        tools_without_container = [t for t in tools if not t.container]
        if len(tools_without_container) > len(tools) * 0.5:
            gaps.append(InformationGap(
                gap_type=GapType.MISSING_CONTAINER,
                description=f"{len(tools_without_container)} tools without container information",
                severity="low",
                suggested_resolution="Search BioContainers registry"
            ))

        # Steps without tools
        steps_without_tools = [s for s in workflow_steps if not s.tools]
        if steps_without_tools:
            gaps.append(InformationGap(
                gap_type=GapType.AMBIGUOUS_STEP,
                description=f"{len(steps_without_tools)} workflow steps without identified tools",
                severity="medium",
                suggested_resolution="Review Methods section for tool names or infer from step description"
            ))

        # Unclear dependencies
        steps_without_inputs = [s for s in workflow_steps if not s.input_data and s.step_number > 1]
        if steps_without_inputs:
            gaps.append(InformationGap(
                gap_type=GapType.UNCLEAR_DEPENDENCY,
                description=f"{len(steps_without_inputs)} steps with unclear input dependencies",
                severity="low",
                suggested_resolution="Analyze data flow from previous steps"
            ))

        return gaps


def main():
    """Example usage"""
    print("Q2A Assembler - Example Usage")
    print()
    print("This module is designed to be imported and used by paper_to_q2a.py")
    print()
    print("Basic usage:")
    print("  from q2a_assembler import Q2AAssembler")
    print("  assembler = Q2AAssembler(paper_id='paper_001', pdf_paths=[Path('paper.pdf')])")
    print("  q2a_doc = assembler.assemble(sections, tools, workflow_steps)")
    print("  q2a_doc.save(Path('output.json'))")


if __name__ == "__main__":
    main()
