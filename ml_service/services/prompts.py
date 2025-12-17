"""
Prompt templates for annotation suggestion generation.

Implements Section 3.2 of the methodology:
- Structured "annotation blocks" containing:
  - The original input
  - The label chosen
  - The annotated span
  - The annotator's style or explanation (if available)
"""

from typing import List, Dict, Any, Optional


                                       

NER_SYSTEM_PROMPT = """You are an expert annotation assistant for Named Entity Recognition (NER) tasks.
Your job is to identify and label named entities in text with precision and consistency.

Available labels: {labels}

For each entity you find, provide:
- The exact text span
- The label type
- Start and end character positions
- A brief rationale explaining why you chose this label

Be consistent with the annotation style shown in the examples."""


NER_USER_PROMPT = """Analyze the following text and identify all named entities.

{exemplar_blocks}

Text to annotate:
"{text}"

Return a JSON array of entities. Each entity should have:
- "text": the exact entity text
- "label": one of the available labels
- "start": character start position (0-indexed)
- "end": character end position
- "rationale": brief explanation of why this is labeled this way

Example output format:
[
  {{"text": "OpenAI", "label": "ORG", "start": 0, "end": 6, "rationale": "Technology company name"}}
]

If no entities found, return an empty array: []"""


                                                  

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert text classification assistant.
Your job is to classify text into appropriate categories with consistency.

Available categories: {labels}

Provide a classification with confidence score and rationale explaining your choice.
Be consistent with the classification style shown in the examples."""


CLASSIFICATION_USER_PROMPT = """Classify the following text into the most appropriate category.

{exemplar_blocks}

Text to classify:
"{text}"

Return a JSON object with:
- "label": the chosen category
- "confidence": a score from 0.0 to 1.0
- "rationale": explanation of why you chose this label

Example:
{{"label": "POSITIVE", "confidence": 0.85, "rationale": "Strong positive language and sentiment indicators"}}"""


                                                       

def format_annotation_block(
    original_input: str,
    label: str,
    span_text: str,
    span_start: int,
    span_end: int,
    rationale: Optional[str] = None,
    annotator_style: Optional[str] = None
) -> str:
    """
    Format a single annotation as a structured block.
    
    Implements the "annotation blocks" from Section 3.2:
    - The original input
    - The label chosen
    - The annotated span
    - The annotator's style or explanation (if available)
    """
    block_lines = [
        "---",
        f"Input: \"{original_input[:200]}{'...' if len(original_input) > 200 else ''}\"",
        f"Span: \"{span_text}\" (positions {span_start}-{span_end})",
        f"Label: {label}",
    ]
    
    if rationale:
        block_lines.append(f"Rationale: {rationale}")
    
    if annotator_style:
        block_lines.append(f"Style note: {annotator_style}")
    
    block_lines.append("---")
    
    return "\n".join(block_lines)


def format_exemplar_blocks(exemplars: List[Dict[str, Any]]) -> str:
    """
    Format multiple exemplars as structured annotation blocks.
    
    Args:
        exemplars: List of exemplar dicts with keys:
            - text: the annotated span text
            - label: the annotation label
            - span_start, span_end: positions
            - context: original document context (optional)
            - rationale: explanation (optional)
            - style: annotator style notes (optional)
    
    Returns:
        Formatted string with all annotation blocks
    """
    if not exemplars:
        return ""
    
    blocks = ["Here are examples of how similar text has been annotated:\n"]
    
    for i, ex in enumerate(exemplars, 1):
        block = format_annotation_block(
            original_input=ex.get("context", ex.get("text", "")),
            label=ex.get("label", ""),
            span_text=ex.get("text", ""),
            span_start=ex.get("span_start", 0),
            span_end=ex.get("span_end", 0),
            rationale=ex.get("rationale"),
            annotator_style=ex.get("style")
        )
        blocks.append(f"Example {i}:\n{block}\n")
    
    blocks.append("Follow the same annotation patterns and style shown above.\n")
    
    return "\n".join(blocks)


def build_ner_prompt(
    text: str,
    labels: List[str],
    exemplars: List[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    Build NER annotation prompt with structured exemplar blocks.
    
    Args:
        text: Text to annotate
        labels: Available label types
        exemplars: Retrieved similar annotations
        
    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = NER_SYSTEM_PROMPT.format(labels=", ".join(labels))
    
    exemplar_text = format_exemplar_blocks(exemplars) if exemplars else ""
    user = NER_USER_PROMPT.format(text=text, exemplar_blocks=exemplar_text)
    
    return system, user


def build_classification_prompt(
    text: str,
    labels: List[str],
    exemplars: List[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    Build classification prompt with structured exemplar blocks.
    
    Args:
        text: Text to classify
        labels: Available categories
        exemplars: Retrieved similar classifications
        
    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = CLASSIFICATION_SYSTEM_PROMPT.format(labels=", ".join(labels))
    
    exemplar_text = format_exemplar_blocks(exemplars) if exemplars else ""
    user = CLASSIFICATION_USER_PROMPT.format(text=text, exemplar_blocks=exemplar_text)
    
    return system, user
