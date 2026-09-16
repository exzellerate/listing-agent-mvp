"""
Logic shared by every provider implementation.

extract_json_from_text() is ported verbatim from the fallback chain that
lived duplicated in services/claude_analyzer.py (single-image and batch
paths) — Phase 2 of the Gemini rollout plan replaces both copies with calls
to this function. Kept provider-agnostic since Gemini's plain-text JSON
output (when not using its native response_schema mode) needs the same
recovery.
"""
import json
import logging
import re
import time
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


def extract_json_from_text(response_text: str, debug_dir: str = "/tmp") -> Tuple[Dict[str, Any], str]:
    """Extract and parse a JSON object out of an LLM's plain-text response.

    Models are asked to return JSON but often wrap it in markdown code
    fences or add explanatory text around it. This tries, in order:
      1. A ```json ... ``` code fence
      2. Brace-counting to find the first balanced {...} object
      3. Recovery on parse failure: strip trailing commas, close unbalanced
         braces/brackets, escape stray control characters inside strings
      4. Last resort: flatten all whitespace control characters

    Returns:
        (parsed_dict, extraction_strategy) — strategy is one of
        "no_extraction_needed", "json_code_block", "brace_counting",
        raised as a suffix "+recovered"/"+aggressive_recovery" if the first
        json.loads attempt failed.

    Raises:
        json.JSONDecodeError if every recovery strategy fails.
    """
    text = response_text
    extraction_strategy = None

    if "```json" in text:
        json_start = text.find("```json") + 7
        json_end = text.find("```", json_start)
        if json_end > json_start:
            text = text[json_start:json_end].strip()
            extraction_strategy = "json_code_block"

    if not text.strip().startswith("{"):
        first_brace = text.find("{")
        if first_brace != -1:
            brace_count = 0
            last_brace = -1
            for i in range(first_brace, len(text)):
                if text[i] == "{":
                    brace_count += 1
                elif text[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        last_brace = i
                        break
            if last_brace > first_brace:
                text = text[first_brace:last_brace + 1].strip()
                extraction_strategy = "brace_counting"
    elif extraction_strategy is None:
        extraction_strategy = "no_extraction_needed"

    try:
        return json.loads(text), extraction_strategy or "no_extraction_needed"
    except json.JSONDecodeError as first_error:
        logger.warning(
            f"First JSON parse failed at position {first_error.pos}: {first_error.msg} "
            f"(strategy: {extraction_strategy}); attempting recovery..."
        )
        try:
            with open(f"{debug_dir}/ai_provider_response_debug_{int(time.time())}.json", "w") as f:
                f.write(text)
        except Exception:
            pass

        recovered = re.sub(r",(\s*[}\]])", r"\1", text)
        recovered = re.sub(r",\s*$", "", recovered)

        open_braces, close_braces = recovered.count("{"), recovered.count("}")
        open_brackets, close_brackets = recovered.count("["), recovered.count("]")
        if open_braces > close_braces:
            recovered += "}" * (open_braces - close_braces)
        if open_brackets > close_brackets:
            recovered += "]" * (open_brackets - close_brackets)

        def _escape_string_content(match: "re.Match") -> str:
            quote = match.group(0)[0]
            content = match.group(0)[1:-1]
            content = (
                content.replace("\\", "\\\\")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
                .replace("\b", "\\b")
                .replace("\f", "\\f")
            )
            return f"{quote}{content}{quote}"

        recovered = re.sub(r'"(?:[^"\\]|\\.)*"', _escape_string_content, recovered)
        recovered = recovered.replace("\x00", "")

        try:
            result = json.loads(recovered)
            return result, f"{extraction_strategy}+recovered"
        except json.JSONDecodeError as second_error:
            logger.warning(f"Recovery failed at position {second_error.pos}: {second_error.msg}; trying aggressive cleanup")
            aggressive = recovered.replace("\n", " ").replace("\r", " ").replace("\t", " ")
            result = json.loads(aggressive)  # let this raise if it still fails
            return result, f"{extraction_strategy}+aggressive_recovery"
