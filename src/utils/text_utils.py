"""
src/utils/text_utils.py
=======================
Generic text utility functions used across the STA pipeline.
"""

import re


def clean_basic_text(value):
    """
    Clean text without changing its semantic meaning.

    Steps:
        1. Convert value to string.
        2. Strip leading/trailing spaces.
        3. Normalize repeated whitespace.
        4. Remove simple wrapping quotes.
        5. Strip again.

    Used for:
        - cleaned cell values
        - prompt values
        - KG queries
        - short text cleanup
    """

    if value is None:
        return ""

    text = str(value).strip()

    # Normalize repeated spaces, tabs, and newlines.
    text = re.sub(r"\s+", " ", text)

    # Remove simple wrapping quotes.
    text = text.strip('"').strip("'").strip()

    return text


def clean_html_text(value):
    """
    Remove simple HTML/XML tags and apply basic text cleaning.
    """

    text = clean_basic_text(value)

    # Remove simple HTML/XML-like tags.
    text = re.sub(r"<[^>]+>", "", text)

    return clean_basic_text(text)


def normalize_for_matching(value):
    """
    Normalize text for exact matching, deduplication, and cache keys.
    """

    return clean_basic_text(value).lower()


def format_values_as_bullets(values):
    """
    Format a list of values as bullet points for prompts.
    """

    useful_values = []

    for value in values:
        text = clean_basic_text(value)

        if text != "":
            useful_values.append(text)

    if not useful_values:
        return "- No useful values"

    return "\n".join(f"- {value}" for value in useful_values)


def clean_short_label(answer, max_words=5, fallback="Unknown"):
    """
    Clean a short LLM label answer.

    Useful for:
        - topic detection labels
        - short semantic labels
    """

    if answer is None:
        return fallback

    text = clean_basic_text(answer)

    if text == "":
        return fallback

    # Use only the first line.
    text = text.splitlines()[0].strip()

    # Remove quotes.
    text = text.replace('"', "").replace("'", "")

    # Remove common answer prefixes.
    text = re.sub(
        r"^(topic|label|answer)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = clean_basic_text(text)

    # Remove final punctuation.
    while text.endswith((".", ":", ";", ",")):
        text = text[:-1].strip()

    if text == "":
        return fallback

    # Avoid storing explanations as labels.
    if len(text.split()) > max_words:
        return fallback

    return text


def parse_candidate_number(answer, candidate_count):
    """
    Parse an LLM answer expected to contain a candidate number.

    Returns:
        Integer candidate number, or 0 if invalid.
    """

    if answer is None:
        return 0

    text = clean_basic_text(answer)

    if text == "":
        return 0

    first_line = text.splitlines()[0].strip()

    match = re.search(r"\d+", first_line)

    if not match:
        return 0

    number = int(match.group())

    if number < 0 or number > candidate_count:
        return 0

    return number