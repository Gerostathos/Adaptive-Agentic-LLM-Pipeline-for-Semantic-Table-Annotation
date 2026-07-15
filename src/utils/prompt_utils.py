"""
src/utils/prompt_utils.py
=========================
Prompt formatting helpers used across the STA pipeline.
"""

from Code.src.utils.text_utils import clean_basic_text


def format_candidates_for_prompt(candidates, empty_message="0. No candidates available"):
    """
    Format KG candidates for LLM selection prompts.

    Parameters:
        candidates: List of candidate dictionaries.
        empty_message: Text returned when no candidates exist.

    Returns:
        A numbered candidate list as a string.
    """

    if not candidates:
        return empty_message

    lines = []

    for index, candidate in enumerate(candidates, start=1):
        label = clean_basic_text(candidate.get("label", ""))
        candidate_id = clean_basic_text(candidate.get("id", ""))
        description = clean_basic_text(candidate.get("description", ""))

        line = f"{index}. {label} ({candidate_id})"

        if description:
            line += f" - {description}"

        lines.append(line)

    return "\n".join(lines)