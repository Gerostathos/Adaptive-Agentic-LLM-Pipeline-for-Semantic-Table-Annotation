"""
src/utils/label_parser.py
=========================

Minimal helper for connecting clean LLM answers with KG candidates. The prompt
is expected to return one final label, and this file only checks whether that
label exactly corresponds to one candidate label.
"""

from Code.src.utils.text_utils import clean_basic_text


def get_first_answer_line(answer):
    """
    Extract the first non-empty line from an LLM response.

    Parameters:
        answer: Raw LLM response.

    Returns:
        First cleaned answer line, or an empty string.
    """

    if answer is None:
        return ""

    text = clean_basic_text(answer)

    if text == "" or text.startswith("ERROR:"):
        return ""

    for line in text.splitlines():
        line = clean_basic_text(line)

        if line:
            return line.strip().strip('"').strip("'")

    return ""


def match_label_to_candidate(label, candidates):
    """
    Match the returned LLM label to a KG candidate label.

    Parameters:
        label: Clean label returned by the LLM.
        candidates: Candidate dictionaries with a label field.

    Returns:
        Matching candidate dictionary, or None.
    """

    label_clean = clean_basic_text(label).lower().strip()

    if label_clean == "":
        return None

    for candidate in candidates:
        candidate_label = candidate.get("label", "")
        candidate_clean = clean_basic_text(candidate_label).lower().strip()

        if label_clean == candidate_clean:
            return candidate

    return None


def parse_candidate_or_label_response(answer, candidates, max_words=4):
    """
    Interpret the LLM response as one final semantic label.

    Parameters:
        answer: Raw LLM response.
        candidates: KG candidate dictionaries.
        max_words: Kept for compatibility with CEA and CTA calls.

    Returns:
        mode, selected_candidate, final_label
    """

    label = get_first_answer_line(answer)

    if label == "":
        return "none", None, ""

    matched_candidate = match_label_to_candidate(
        label=label,
        candidates=candidates,
    )

    if matched_candidate is not None:
        return "kg", matched_candidate, matched_candidate.get("label", label)

    return "llm", None, label