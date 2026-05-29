"""
LLM Judge service using xAI Grok for strict German tenancy law analysis.
Only flags clauses when there is high confidence in illegal pattern matching.

Uses OpenAI Structured Outputs (response_format=json_schema) for reliable parsing.
xAI's API is fully compatible with this pattern.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


# ====================================================================
# Structured output schema (OpenAI Structured Outputs / JSON Schema)
# ====================================================================
class ClauseJudgment(BaseModel):
    """Structured schema for the LLM judge response."""

    flag: bool = Field(
        description="Whether the clause matches a known illegal pattern with high confidence"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM self-reported confidence (0.0-1.0) in the judgment",
    )
    exact_quote: Optional[str] = Field(
        None,
        description="Exact problematic text verbatim from the contract section, or null if not flagged",
    )
    legal_citation: Optional[str] = Field(
        None,
        description="BGB paragraph or court ruling citation, e.g. 'BGB § 551', or null",
    )
    reason: str = Field(
        description="Brief reason in German why this clause is or isn't a problem"
    )
    ocr_error: bool = Field(
        description="True if the OCR text is garbled/unreadable and needs manual review"
    )
    matched_pattern: Optional[str] = Field(
        None,
        description="Which known invalid pattern from the provided list this matches, or null",
    )


# ====================================================================
# Prompts
# ====================================================================
STRICT_JUDGE_SYSTEM_PROMPT = (
    "You are a strict German tenancy law expert (Fachanwalt für Mietrecht). "
    "Your task is to analyze rental contract clauses for potential illegal or unfair clauses. "
    "You are extremely conservative: only flag a clause if it matches a known illegal pattern with high confidence. "
    "If the OCR text is garbled, unreadable, or clearly corrupted, set ocr_error to true. "
    "Always quote the exact original text from the clause."
)

STRICT_JUDGE_USER_PROMPT_TEMPLATE = """Analyze the following rental contract clause (section) from a German Mietvertrag.

**Contract Section Text:**
```
{section_text}
```

**Top matching known invalid clause patterns (for context):**
{patterns_context}

**Exact BGB legal text excerpts (for reference):**
{bgb_context}

Rules:
- Only flag if you are highly confident (>0.8 confidence) that it matches an illegal pattern.
- If confidence is below 0.8, set flag to false.
- If OCR quality is poor and text is garbled, set ocr_error to true.
- Be precise with exact_quote — copy verbatim from the section text.
- legal_citation must reference specific BGB paragraphs (e.g. BGB § 551, BGB § 573c).
- matched_pattern should specify which of the provided patterns this matches, or null.
- reason should be a brief German explanation.
"""


# ====================================================================
# Default fallback (used when API key missing or error occurs)
# ====================================================================
def _fallback_result(reason: str) -> Dict[str, Any]:
    return {
        "flag": False,
        "confidence": 0.0,
        "exact_quote": None,
        "legal_citation": None,
        "reason": reason,
        "ocr_error": False,
        "matched_pattern": None,
    }


# ====================================================================
# Main judge function
# ====================================================================
def judge_section(
    section_text: str,
    top_patterns: List[Dict[str, Any]],
    bgb_excerpts: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a contract section to xAI Grok for strict legal judgment.
    Uses OpenAI Structured Outputs (response_format=json_schema) for reliable JSON parsing.

    Args:
        section_text: The contract section text to analyze.
        top_patterns: Top-3 relevant invalid clause patterns with metadata.
        bgb_excerpts: Relevant BGB legal text excerpts.
        api_key: xAI API key (defaults to settings.XAI_API_KEY).
        model: Model name (defaults to settings.XAI_MODEL).

    Returns:
        Dict with keys: flag, confidence, exact_quote, legal_citation, reason, ocr_error, matched_pattern
    """
    api_key = api_key or settings.XAI_API_KEY
    model = model or settings.XAI_MODEL

    if not api_key:
        logger.warning("No XAI_API_KEY configured; skipping LLM judge")
        return _fallback_result("LLM unavailable – no API key configured")

    # Build patterns context string
    patterns_lines = []
    for i, p in enumerate(top_patterns, 1):
        patterns_lines.append(
            f"{i}. Topic: {p.get('topic', '?')}\n"
            f"   Pattern: {p.get('clause_pattern', '?')}\n"
            f"   Why invalid: {p.get('why_invalid', '?')}\n"
            f"   Legal basis: {p.get('legal_basis', p.get('bgb_citation', '?'))}\n"
            f"   Risk level: {p.get('risk_level', '?')}"
        )
    patterns_context = (
        "\n\n".join(patterns_lines) if patterns_lines else "No relevant patterns found."
    )

    # Build BGB context string
    bgb_lines = []
    for i, bgb in enumerate(bgb_excerpts, 1):
        bgb_lines.append(
            f"{i}. {bgb.get('citation', bgb.get('document_title', '?'))}\n"
            f"   Text: {bgb.get('text', bgb.get('bgb_text_excerpt', '?'))}"
        )
    bgb_context = (
        "\n\n".join(bgb_lines) if bgb_lines else "No exact BGB text available."
    )

    # Build the user prompt
    user_prompt = STRICT_JUDGE_USER_PROMPT_TEMPLATE.format(
        section_text=section_text[:3000],
        patterns_context=patterns_context,
        bgb_context=bgb_context,
    )

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        # Prepare the JSON schema from the Pydantic model
        schema = ClauseJudgment.model_json_schema()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": STRICT_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            # Use OpenAI Structured Outputs (JSON Schema mode)
            # Fully compatible with xAI's API
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "clause_judgment",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0.1,
            max_tokens=500,
        )

        # Extract the content
        content = response.choices[0].message.content.strip()

        # Parse via Pydantic for validation
        parsed = ClauseJudgment.model_validate_json(content)

        result = {
            "flag": parsed.flag,
            "confidence": parsed.confidence,
            "exact_quote": parsed.exact_quote,
            "legal_citation": parsed.legal_citation,
            "reason": parsed.reason,
            "ocr_error": parsed.ocr_error,
            "matched_pattern": parsed.matched_pattern,
        }

        logger.info(
            "LLM judge result: flag=%s, confidence=%.2f, ocr_error=%s",
            result["flag"],
            result["confidence"],
            result["ocr_error"],
        )

        return result

    except Exception as e:
        logger.error(f"LLM judge error: {e}")
        return _fallback_result(f"LLM judge error: {str(e)}")
