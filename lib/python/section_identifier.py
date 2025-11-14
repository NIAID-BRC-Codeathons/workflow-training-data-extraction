"""
Section Identifier for Scientific Papers

Identifies and extracts specific sections from scientific papers using
both heuristic methods and LLM-based analysis.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SectionType(Enum):
    """Standard scientific paper sections"""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    DATA_AVAILABILITY = "data_availability"
    ACKNOWLEDGMENTS = "acknowledgments"
    SUPPLEMENTARY = "supplementary"
    UNKNOWN = "unknown"


@dataclass
class PaperSection:
    """Represents an identified section of a paper"""
    section_type: SectionType
    title: str
    content: str
    start_pos: int
    end_pos: int
    confidence: float = 0.0


class SectionIdentifier:
    """Identify sections in scientific papers"""

    # Common section heading patterns
    SECTION_PATTERNS = {
        SectionType.ABSTRACT: [
            r'^abstract\b',
            r'^summary\b',
        ],
        SectionType.INTRODUCTION: [
            r'^introduction\b',
            r'^background\b',
        ],
        SectionType.METHODS: [
            r'^methods?\b',
            r'^materials?\s+and\s+methods?\b',
            r'^experimental\s+procedures?\b',
            r'^methodology\b',
        ],
        SectionType.RESULTS: [
            r'^results?\b',
            r'^findings?\b',
        ],
        SectionType.DISCUSSION: [
            r'^discussion\b',
            r'^results?\s+and\s+discussion\b',
        ],
        SectionType.CONCLUSION: [
            r'^conclusions?\b',
            r'^concluding\s+remarks?\b',
        ],
        SectionType.REFERENCES: [
            r'^references?\b',
            r'^bibliography\b',
            r'^works?\s+cited\b',
        ],
        SectionType.DATA_AVAILABILITY: [
            r'^data\s+availability\b',
            r'^data\s+access\b',
            r'^availability\s+of\s+data\b',
        ],
        SectionType.ACKNOWLEDGMENTS: [
            r'^acknowledgments?\b',
            r'^acknowledgements?\b',
        ],
    }

    def __init__(self, use_llm: bool = True, sophia_client=None):
        """
        Initialize section identifier

        Args:
            use_llm: Whether to use LLM for section identification
            sophia_client: Optional SophiaClient for LLM-based identification
        """
        self.use_llm = use_llm
        self.sophia_client = sophia_client
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for section headers"""
        self.compiled_patterns = {}

        for section_type, patterns in self.SECTION_PATTERNS.items():
            compiled = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]
            self.compiled_patterns[section_type] = compiled

    def identify_sections_heuristic(self, text: str) -> Dict[SectionType, PaperSection]:
        """
        Identify sections using heuristic pattern matching

        Args:
            text: Full paper text

        Returns:
            Dictionary mapping section types to PaperSection objects
        """
        sections = {}
        lines = text.split('\n')

        # Find all potential section headers
        potential_headers = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip very short or very long lines
            if len(line_stripped) < 3 or len(line_stripped) > 100:
                continue

            # Check if line matches any section pattern
            for section_type, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(line_stripped):
                        # Validate: skip false positives
                        # Skip if line starts with a number (likely a reference)
                        if re.match(r'^\d+\.?\s', line_stripped):
                            continue

                        # Skip if line contains reference indicators
                        reference_indicators = ['FOIA', 'Report', '©', 'doi:', 'http://', 'https://']
                        if any(indicator in line_stripped for indicator in reference_indicators):
                            continue

                        # For Methods/Results, prefer standalone headers (just the word)
                        if section_type in [SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION]:
                            # Accept if it's just the section name (possibly with minimal extra words)
                            words = line_stripped.split()
                            if len(words) > 5:  # Too many words, likely not a header
                                continue

                        # Calculate position in original text
                        pos = sum(len(l) + 1 for l in lines[:i])
                        potential_headers.append({
                            'type': section_type,
                            'title': line_stripped,
                            'line_num': i,
                            'pos': pos
                        })
                        break

        # Sort headers by position
        potential_headers.sort(key=lambda x: x['pos'])

        # Extract content between headers
        for i, header in enumerate(potential_headers):
            section_type = header['type']
            start_line = header['line_num'] + 1

            # Find end (next header or end of document)
            if i + 1 < len(potential_headers):
                end_line = potential_headers[i + 1]['line_num']
            else:
                end_line = len(lines)

            # Extract content
            content_lines = lines[start_line:end_line]
            content = '\n'.join(content_lines).strip()

            # Skip very short sections
            if len(content) < 50:
                continue

            start_pos = sum(len(l) + 1 for l in lines[:start_line])
            end_pos = sum(len(l) + 1 for l in lines[:end_line])

            # Higher confidence for clean, standalone section headers
            title_words = header['title'].split()
            if len(title_words) <= 3 and section_type in [SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION, SectionType.INTRODUCTION]:
                confidence = 0.9  # High confidence for clean headers like "Methods" or "Results and Discussion"
            else:
                confidence = 0.7  # Moderate confidence for heuristic

            section = PaperSection(
                section_type=section_type,
                title=header['title'],
                content=content,
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=confidence
            )

            # Keep only the first occurrence of each section type
            if section_type not in sections:
                sections[section_type] = section

        return sections

    def _identify_sections_in_window(self, text: str, window_start: int) -> List[Dict]:
        """
        Identify section headers in a text window using LLM

        Args:
            text: Text window to analyze
            window_start: Character position where this window starts in full document

        Returns:
            List of detected sections with their positions
        """
        from sophia_client import ChatMessage
        import json

        system_prompt = """You are a scientific paper analyzer. Find SECTION HEADERS ONLY in the given text.

A section header is typically:
- A standalone line (not mid-sentence)
- Often at the start of a line
- Followed by content describing that section
- NOT part of a reference citation or figure caption

Examples of section headers:
  "Methods"  (followed by "Dataset collection...")
  "Results and Discussion"
  "Materials and Methods"

NOT section headers:
  "...Depopulation Methods and Impact..." (mid-sentence in a reference)
  "...Figure 3 Methods..." (figure caption)

Respond ONLY with valid JSON (no other text). List each SECTION HEADER found:
[
  {"section": "Introduction", "char_pos": 123, "preview": "first 20 words of section content..."},
  {"section": "Methods", "char_pos": 5678, "preview": "first 20 words of section content..."}
]

Section types: Abstract, Introduction, Methods, Materials and Methods, Results, Discussion, Conclusion, References, Data Availability, Acknowledgments

If no section headers found, return: []"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"Text to analyze:\n\n{text}")
        ]

        try:
            response = self.sophia_client.chat_completion(
                messages,
                temperature=0.1,  # Low temp for factual extraction
                max_tokens=1000
            )

            # Try to parse JSON, handling common formatting issues
            content = response.content.strip()

            # Remove markdown code blocks if present
            if '```json' in content:
                # Extract JSON from code block
                start = content.find('```json') + 7
                end = content.find('```', start)
                content = content[start:end].strip()
            elif content.startswith('```'):
                # Extract JSON from code block
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1])  # Remove first and last lines

            # Try to extract just the JSON array if there's extra text
            # Look for [ ... ] pattern
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            sections_found = json.loads(content)

            # Adjust positions relative to full document
            for section in sections_found:
                section['char_pos'] += window_start

            return sections_found

        except json.JSONDecodeError as e:
            # Try one more time - extract first complete JSON array
            try:
                import re
                json_match = re.search(r'\[\s*\{.*?\}\s*\]', response.content, re.DOTALL)
                if json_match:
                    sections_found = json.loads(json_match.group(0))
                    for section in sections_found:
                        section['char_pos'] += window_start
                    return sections_found
            except:
                pass

            print(f"Warning: Could not parse LLM response as JSON in window at {window_start}: {e}")
            print(f"Response was: {response.content[:200]}...")
            return []
        except Exception as e:
            print(f"Warning: Window analysis failed at {window_start}: {e}")
            return []

    def identify_sections_llm(self, text: str) -> Dict[SectionType, PaperSection]:
        """
        Identify sections using LLM analysis with sliding window approach

        Args:
            text: Full paper text

        Returns:
            Dictionary mapping section types to PaperSection objects
        """
        if not self.use_llm or not self.sophia_client:
            return {}

        try:
            from sophia_client import ChatMessage

            # Use sliding window for large documents
            window_size = 10000  # 10K characters per window
            overlap = 2000       # 2K character overlap

            all_sections_found = []

            if len(text) <= window_size:
                # Small document, process all at once
                all_sections_found = self._identify_sections_in_window(text, 0)
            else:
                # Large document, use sliding windows
                print(f"Processing {len(text):,} chars with sliding windows ({window_size} chars, {overlap} overlap)...")

                pos = 0
                window_num = 0
                while pos < len(text):
                    window_end = min(pos + window_size, len(text))
                    window_text = text[pos:window_end]

                    window_num += 1
                    print(f"  Window {window_num}: chars {pos:,} - {window_end:,}")

                    sections_in_window = self._identify_sections_in_window(window_text, pos)
                    all_sections_found.extend(sections_in_window)

                    # Move to next window with overlap
                    pos += (window_size - overlap)

                    if pos >= len(text):
                        break

            # Deduplicate sections found in overlapping windows
            sections_dict = {}

            for section_data in all_sections_found:
                section_name = section_data.get('section', '')
                section_type = self._map_section_name(section_name)

                if section_type == SectionType.UNKNOWN:
                    continue

                char_pos = section_data.get('char_pos', 0)
                preview = section_data.get('preview', '')

                # If we already have this section type, use heuristics to pick the best one
                if section_type in sections_dict:
                    existing_preview = sections_dict[section_type].get('preview', '')
                    existing_pos = sections_dict[section_type]['char_pos']

                    # Prefer sections with longer previews (indicates more content)
                    # OR sections that appear later for Methods/Results/Discussion
                    # (these are typically detailed sections that come after intro)
                    if section_type in [SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION]:
                        # For main content sections, prefer the one with more substantial content
                        # Indicated by longer preview
                        if len(preview) > len(existing_preview):
                            sections_dict[section_type] = section_data
                        elif len(preview) == len(existing_preview) and char_pos > existing_pos:
                            # If previews similar length, prefer later position
                            sections_dict[section_type] = section_data
                    else:
                        # For front matter (abstract, intro), keep earlier position
                        if char_pos < existing_pos:
                            sections_dict[section_type] = section_data
                else:
                    sections_dict[section_type] = section_data

            # Convert to PaperSection objects
            sections = {}

            for section_type, section_data in sections_dict.items():
                start_pos = section_data['char_pos']
                preview = section_data.get('preview', '')

                # Find actual section start using preview
                # For main content sections, search more broadly since LLM position estimates can be off
                if section_type in [SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION]:
                    search_start = max(0, start_pos - 5000)  # Search 5K chars before
                    search_end = min(len(text), start_pos + 10000)  # and 10K after
                else:
                    search_start = max(0, start_pos - 200)
                    search_end = min(len(text), start_pos + 500)

                # Search for preview text AND validate it's after a section header
                if preview:
                    preview_words = ' '.join(preview.split()[:5])  # First 5 words
                    content_start = text.find(preview_words, search_start, search_end)
                    if content_start == -1:
                        # Try searching the entire document for this unique preview
                        content_start = text.find(preview_words)
                        if content_start == -1:
                            content_start = start_pos

                    # Validate: for Methods/Results/Discussion, ensure there's a section header nearby
                    if section_type in [SectionType.METHODS, SectionType.RESULTS, SectionType.DISCUSSION]:
                        # Look backwards up to 200 chars for the section header
                        header_search_start = max(0, content_start - 200)
                        header_region = text[header_search_start:content_start]

                        # Check if section type name appears as standalone header
                        section_name = section_type.value.title()  # "Methods", "Results", "Discussion"
                        import re
                        # Match section header: word boundary, section name, followed by newline or end
                        header_pattern = rf'\b{section_name}\b'
                        if not re.search(header_pattern, header_region, re.IGNORECASE):
                            # No header found nearby - likely a false positive
                            # Try to find the section header in the document
                            alt_header_pos = text.find(f'\n{section_name}\n', content_start - 5000, content_start + 5000)
                            if alt_header_pos != -1:
                                content_start = alt_header_pos + 1  # After the newline
                else:
                    content_start = start_pos

                # Estimate section end (find next section or use heuristic length)
                # For now, use a conservative 5000 chars
                content_end = min(len(text), content_start + 5000)

                # Try to find next section to get better boundary
                next_section_pos = len(text)
                for other_type, other_data in sections_dict.items():
                    if other_type != section_type:
                        other_pos = other_data['char_pos']
                        if other_pos > content_start and other_pos < next_section_pos:
                            next_section_pos = other_pos

                if next_section_pos < content_end:
                    content_end = next_section_pos

                content = text[content_start:content_end].strip()

                # Get section title from the text
                title_end = min(100, len(content))
                title_text = content[:title_end]
                first_line = title_text.split('\n')[0].strip()

                section = PaperSection(
                    section_type=section_type,
                    title=first_line if len(first_line) < 100 else section_data.get('section', section_type.value),
                    content=content,
                    start_pos=content_start,
                    end_pos=content_end,
                    confidence=0.85  # High confidence for LLM
                )

                sections[section_type] = section

            return sections

        except Exception as e:
            print(f"Warning: LLM section identification failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _map_section_name(self, name: str) -> SectionType:
        """Map section name to SectionType enum"""
        name_lower = name.lower().strip()

        mapping = {
            'abstract': SectionType.ABSTRACT,
            'introduction': SectionType.INTRODUCTION,
            'background': SectionType.INTRODUCTION,
            'methods': SectionType.METHODS,
            'materials': SectionType.METHODS,
            'methodology': SectionType.METHODS,
            'results': SectionType.RESULTS,
            'findings': SectionType.RESULTS,
            'discussion': SectionType.DISCUSSION,
            'conclusion': SectionType.CONCLUSION,
            'conclusions': SectionType.CONCLUSION,
            'references': SectionType.REFERENCES,
            'data availability': SectionType.DATA_AVAILABILITY,
            'data_availability': SectionType.DATA_AVAILABILITY,
            'acknowledgments': SectionType.ACKNOWLEDGMENTS,
            'acknowledgements': SectionType.ACKNOWLEDGMENTS,
        }

        return mapping.get(name_lower, SectionType.UNKNOWN)

    def identify_sections(self, text: str) -> Dict[SectionType, PaperSection]:
        """
        Identify sections using both heuristic and LLM methods

        Args:
            text: Full paper text

        Returns:
            Dictionary of identified sections
        """
        # Heuristic identification
        heuristic_sections = self.identify_sections_heuristic(text)

        # LLM identification
        llm_sections = self.identify_sections_llm(text) if self.use_llm else {}

        # Merge results - prefer LLM if confidence is higher
        merged = {}

        for section_type in set(list(heuristic_sections.keys()) + list(llm_sections.keys())):
            heur_section = heuristic_sections.get(section_type)
            llm_section = llm_sections.get(section_type)

            if heur_section and llm_section:
                # Both detected - use one with higher confidence
                if llm_section.confidence > heur_section.confidence:
                    merged[section_type] = llm_section
                else:
                    merged[section_type] = heur_section
            elif heur_section:
                merged[section_type] = heur_section
            elif llm_section:
                merged[section_type] = llm_section

        return merged

    def get_section(self, sections: Dict[SectionType, PaperSection],
                   section_type: SectionType) -> Optional[str]:
        """
        Get content of a specific section

        Args:
            sections: Dictionary of sections
            section_type: Type of section to retrieve

        Returns:
            Section content or None if not found
        """
        section = sections.get(section_type)
        return section.content if section else None

    def get_methods_section(self, text: str) -> Optional[str]:
        """
        Convenience method to get methods section

        Args:
            text: Full paper text

        Returns:
            Methods section content or None
        """
        sections = self.identify_sections(text)
        return self.get_section(sections, SectionType.METHODS)

    def get_results_section(self, text: str) -> Optional[str]:
        """
        Convenience method to get results section

        Args:
            text: Full paper text

        Returns:
            Results section content or None
        """
        sections = self.identify_sections(text)
        return self.get_section(sections, SectionType.RESULTS)


# Standalone usage
if __name__ == "__main__":
    # Example usage
    paper_text = """
    Title: Analysis of Gene Expression

    Abstract
    This study analyzes gene expression patterns in response to treatment.

    Introduction
    Gene expression is a fundamental biological process. Previous studies have shown...

    Materials and Methods
    RNA extraction was performed using TRIzol reagent. Samples were sequenced on
    Illumina NovaSeq platform. Quality control was performed using FastQC.

    Results
    We identified 1,234 differentially expressed genes with FDR < 0.05.

    Discussion
    Our findings suggest that treatment affects multiple pathways...

    References
    1. Smith et al. (2020) Nature
    """

    identifier = SectionIdentifier(use_llm=False)
    sections = identifier.identify_sections(paper_text)

    print(f"Identified {len(sections)} sections:\n")
    for section_type, section in sections.items():
        print(f"{section_type.value.upper()}:")
        print(f"  Title: {section.title}")
        print(f"  Length: {len(section.content)} chars")
        print(f"  Confidence: {section.confidence:.2f}")
        print(f"  Preview: {section.content[:100]}...")
        print()
