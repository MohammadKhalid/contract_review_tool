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
        description="Brief reason why this clause is or isn't a problem"
    )
    ocr_error: bool = Field(
        description="True if the OCR text is garbled/unreadable and needs manual review"
    )
    matched_pattern: Optional[str] = Field(
        None,
        description="Which known invalid pattern from the provided list this matches, or null",
    )


class BatchJudgmentOutput(BaseModel):
    """Wrapper for batch structured output: one judgment per input section, same order."""

    judgments: List[ClauseJudgment] = Field(
        description="List of judgments, exactly one per input section, in the same order as provided."
    )


# ====================================================================
# Prompts
# ====================================================================
def _get_system_prompt(lang: str) -> str:
    is_german = lang.lower().startswith("de")
    if is_german:
        return (
            "You are a strict German tenancy law expert (Fachanwalt für Mietrecht). "
            "Your task is to analyze rental contract clauses for potential illegal or unfair clauses. "
            "You are extremely conservative: only flag a clause if it matches a known illegal pattern with high confidence. "
            "If the OCR text is garbled, unreadable, or clearly corrupted, set ocr_error to true. "
            "Always quote the exact original text from the clause."
        )
    else:
        return (
            "You are a strict expert in German tenancy law (explaining clearly in English). "
            "Your task is to analyze rental contract clauses for potential illegal or unfair clauses. "
            "You are extremely conservative: only flag a clause if it matches a known illegal pattern with high confidence. "
            "If the OCR text is garbled, unreadable, or clearly corrupted, set ocr_error to true. "
            "Always quote the exact original text from the clause."
        )

STRICT_JUDGE_USER_PROMPT_TEMPLATE = """**Contract Section Text:**
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
- {reason_instruction}
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
    lang: str = "de",
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

    # Determine language for explanations
    is_german = lang.lower().startswith("de")
    reason_instruction = (
        "reason should be a brief German explanation."
        if is_german
        else "reason should be a brief English explanation."
    )

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

    # Build a language-appropriate intro for the user prompt
    intro = (
        "Analyze the following rental contract clause (section) from a German tenancy agreement."
        if not is_german
        else "Analyze the following rental contract clause (section) from a German Mietvertrag."
    )

    # Build the user prompt with the correct language instruction
    user_prompt = STRICT_JUDGE_USER_PROMPT_TEMPLATE.format(
        section_text=section_text[:3000],
        patterns_context=patterns_context,
        bgb_context=bgb_context,
        reason_instruction=reason_instruction,
    )

    # Prepend a language-appropriate intro
    user_prompt = f"{intro}\n\n{user_prompt}"

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        # Prepare the JSON schema from the Pydantic model
        schema = ClauseJudgment.model_json_schema()

        # Make the reason description language-appropriate (very important for structured outputs)
        if not is_german:
            schema["properties"]["reason"]["description"] = "Brief reason in English why this clause is or isn't a problem"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _get_system_prompt(lang)},
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


# ====================================================================
# Async version (for parallel execution)
# ====================================================================
async def judge_section_async(
    section_text: str,
    top_patterns: List[Dict[str, Any]],
    bgb_excerpts: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    lang: str = "de",
) -> Dict[str, Any]:
    """
    Async version of judge_section using AsyncOpenAI.
    Use this when calling many judgments concurrently.
    """
    api_key = api_key or settings.XAI_API_KEY
    model = model or settings.XAI_MODEL

    if not api_key:
        logger.warning("No XAI_API_KEY configured; skipping LLM judge")
        return _fallback_result("LLM unavailable – no API key configured")

    is_german = lang.lower().startswith("de")
    reason_instruction = (
        "reason should be a brief German explanation."
        if is_german
        else "reason should be a brief English explanation."
    )

    # Build contexts (same as sync version)
    patterns_lines = []
    for i, p in enumerate(top_patterns, 1):
        patterns_lines.append(
            f"{i}. Topic: {p.get('topic', '?')}\n"
            f"   Pattern: {p.get('clause_pattern', '?')}\n"
            f"   Why invalid: {p.get('why_invalid', '?')}\n"
            f"   Legal basis: {p.get('legal_basis', p.get('bgb_citation', '?'))}\n"
            f"   Risk level: {p.get('risk_level', '?')}"
        )
    patterns_context = "\n\n".join(patterns_lines) if patterns_lines else "No relevant patterns found."

    bgb_lines = []
    for i, bgb in enumerate(bgb_excerpts, 1):
        bgb_lines.append(
            f"{i}. {bgb.get('citation', bgb.get('document_title', '?'))}\n"
            f"   Text: {bgb.get('text', bgb.get('bgb_text_excerpt', '?'))}"
        )
    bgb_context = "\n\n".join(bgb_lines) if bgb_lines else "No exact BGB text available."

    intro = (
        "Analyze the following rental contract clause (section) from a German tenancy agreement."
        if not is_german
        else "Analyze the following rental contract clause (section) from a German Mietvertrag."
    )
    user_prompt = STRICT_JUDGE_USER_PROMPT_TEMPLATE.format(
        section_text=section_text[:3000],
        patterns_context=patterns_context,
        bgb_context=bgb_context,
        reason_instruction=reason_instruction,
    )
    user_prompt = f"{intro}\n\n{user_prompt}"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        schema = ClauseJudgment.model_json_schema()
        if not is_german:
            schema["properties"]["reason"]["description"] = "Brief reason in English why this clause is or isn't a problem"

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _get_system_prompt(lang)},
                {"role": "user", "content": user_prompt},
            ],
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

        content = response.choices[0].message.content.strip()
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
            "LLM judge result (async): flag=%s, confidence=%.2f, ocr_error=%s",
            result["flag"],
            result["confidence"],
            result["ocr_error"],
        )
        return result

    except Exception as e:
        logger.error(f"LLM judge error (async): {e}")
        return _fallback_result(f"LLM judge error: {str(e)}")


# ====================================================================
# Batch LLM judge (D: reduce round-trips by sending 2-4 clauses per call)
# ====================================================================
BATCH_JUDGE_USER_PROMPT_TEMPLATE = """You will receive {n} contract sections from a German rental agreement.
For EACH section, perform the same strict judgment as a single-section call.

**Sections to judge (in order):**

{sections_block}

**General Rules (apply to every section independently):**
- Only flag if you are highly confident (>0.8 confidence) that it matches an illegal pattern.
- If confidence is below 0.8, set flag to false for that section.
- If OCR quality is poor and text is garbled for a section, set ocr_error true for it.
- Be precise with exact_quote — copy verbatim from that section's text.
- legal_citation must reference specific BGB paragraphs (e.g. BGB § 551, BGB § 573c).
- matched_pattern should specify which of the provided patterns (if any) this matches, or null.
- {reason_instruction}

Return a JSON object with a "judgments" array containing exactly {n} judgment objects, in the exact same order as the input sections above.
"""


async def batch_judge_sections(
    sections: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    lang: str = "de",
) -> List[Dict[str, Any]]:
    """
    Batch version of judge_section_async.
    Sends multiple clauses (with their patterns + BGB context) in ONE LLM call.
    Dramatically reduces number of expensive LLM round-trips when many clauses need judging.

    Args:
        sections: List of dicts, each with keys:
            "text": str (the clause)
            "patterns": List[Dict] (top_patterns for this clause)
            "bgb": List[Dict] (bgb_excerpts for this clause)
        lang: "en" or "de"

    Returns:
        List of judgment dicts (same shape as judge_section_async), in input order.
    """
    if not sections:
        return []

    api_key = api_key or settings.XAI_API_KEY
    model = model or settings.XAI_MODEL

    if not api_key:
        logger.warning("No XAI_API_KEY configured; skipping batch LLM judge")
        return [_fallback_result("LLM unavailable – no API key configured") for _ in sections]

    n = len(sections)
    is_german = lang.lower().startswith("de")
    reason_instruction = (
        "reason should be a brief German explanation."
        if is_german
        else "reason should be a brief English explanation."
    )

    # Build the multi-section block
    blocks = []
    for i, sec in enumerate(sections, 1):
        clause_text = (sec.get("text") or "")[:3000]
        pats = sec.get("patterns") or []
        bgb_ex = sec.get("bgb") or []

        # Reuse the same context formatting logic as single
        patterns_lines = []
        for j, p in enumerate(pats, 1):
            patterns_lines.append(
                f"{j}. Topic: {p.get('topic', '?')}\n"
                f"   Pattern: {p.get('clause_pattern', '?')}\n"
                f"   Why invalid: {p.get('why_invalid', '?')}\n"
                f"   Legal basis: {p.get('legal_basis', p.get('bgb_citation', '?'))}\n"
                f"   Risk level: {p.get('risk_level', '?')}"
            )
        patterns_context = "\n\n".join(patterns_lines) if patterns_lines else "No relevant patterns found."

        bgb_lines = []
        for j, bgb in enumerate(bgb_ex, 1):
            bgb_lines.append(
                f"{j}. {bgb.get('citation', bgb.get('document_title', '?'))}\n"
                f"   Text: {bgb.get('text', bgb.get('bgb_text_excerpt', '?'))}"
            )
        bgb_context = "\n\n".join(bgb_lines) if bgb_lines else "No exact BGB text available."

        block = (
            f"=== Section {i} ===\n"
            f"**Contract Section Text:**\n```\n{clause_text}\n```\n\n"
            f"**Top matching known invalid clause patterns (for context):**\n{patterns_context}\n\n"
            f"**Exact BGB legal text excerpts (for reference):**\n{bgb_context}\n"
        )
        blocks.append(block)

    sections_block = "\n\n".join(blocks)

    intro = (
        "You are analyzing multiple rental contract clauses (sections) from a German tenancy agreement."
        if not is_german
        else "You are analyzing multiple rental contract clauses (sections) from a German Mietvertrag."
    )

    user_prompt = BATCH_JUDGE_USER_PROMPT_TEMPLATE.format(
        n=n,
        sections_block=sections_block,
        reason_instruction=reason_instruction,
    )
    user_prompt = f"{intro}\n\n{user_prompt}"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        # Schema for the batch wrapper
        schema = BatchJudgmentOutput.model_json_schema()
        if not is_german:
            # Adjust reason descriptions inside the array items (best effort)
            for prop in schema.get("properties", {}).get("judgments", {}).get("items", {}).get("properties", {}).values():
                if isinstance(prop, dict) and prop.get("description", "").startswith("Brief reason"):
                    prop["description"] = "Brief reason in English why this clause is or isn't a problem"

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _get_system_prompt(lang)},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "batch_clause_judgments",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0.1,
            max_tokens=2000,  # larger for multiple judgments
        )

        content = response.choices[0].message.content.strip()
        parsed = BatchJudgmentOutput.model_validate_json(content)

        results = []
        for j in parsed.judgments:
            results.append({
                "flag": j.flag,
                "confidence": j.confidence,
                "exact_quote": j.exact_quote,
                "legal_citation": j.legal_citation,
                "reason": j.reason,
                "ocr_error": j.ocr_error,
                "matched_pattern": j.matched_pattern,
            })

        # If LLM returned wrong count, pad/fallback gracefully
        while len(results) < n:
            results.append(_fallback_result("LLM returned fewer judgments than expected"))

        logger.info(
            "Batch LLM judge: n=%d, flagged=%d, ocr_errors=%d",
            n,
            sum(1 for r in results if r.get("flag")),
            sum(1 for r in results if r.get("ocr_error")),
        )
        return results[:n]

    except Exception as e:
        logger.error(f"Batch LLM judge error: {e}")
        return [_fallback_result(f"LLM batch judge error: {str(e)}") for _ in sections]
