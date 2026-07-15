"""
src/tools/levenshtein_reuse.py
=============================
Annotation reuse utilities for Cell Entity Annotation.
"""

from Code.src.config import LEVENSHTEIN_REUSE_RATIO
from Code.src.utils.text_utils import clean_basic_text, normalize_for_matching
from Code.src.preprocessing.value_enrichment import get_preferred_lookup_value


def levenshtein_distance(text_a, text_b):
    """
    Compute Levenshtein edit distance between two strings.

    The distance is the minimum number of insertions, deletions, or substitutions
    needed to transform one string into the other.
    """

    text_a = str(text_a)
    text_b = str(text_b)

    if text_a == text_b:
        return 0

    if len(text_a) == 0:
        return len(text_b)

    if len(text_b) == 0:
        return len(text_a)

    previous_row = list(range(len(text_b) + 1))

    for index_a, char_a in enumerate(text_a, start=1):
        current_row = [index_a]

        for index_b, char_b in enumerate(text_b, start=1):
            insert_cost = current_row[index_b - 1] + 1
            delete_cost = previous_row[index_b] + 1
            substitute_cost = previous_row[index_b - 1]

            if char_a != char_b:
                substitute_cost += 1

            current_row.append(
                min(insert_cost, delete_cost, substitute_cost)
            )

        previous_row = current_row

    return previous_row[-1]


def is_reusable_match(value_a, value_b, ratio=LEVENSHTEIN_REUSE_RATIO):
    """
    Decide whether two values are similar enough for annotation reuse.

    Reuse rule:
        distance <= ratio * min_length
    """

    value_a = normalize_for_matching(value_a)
    value_b = normalize_for_matching(value_b)

    if value_a == "" or value_b == "":
        return False

    min_length = min(len(value_a), len(value_b))

    if min_length == 0:
        return False

    distance = levenshtein_distance(value_a, value_b)
    threshold = ratio * min_length

    return distance <= threshold


def has_final_annotation(cell):
    """
    Check whether a cell already has a final annotation.
    """

    final_annotation = cell.notes.get("final_cell_annotation")

    if final_annotation:
        return True

    if cell.selected_entity is not None:
        return True

    return False


def find_reusable_annotation(target_cell, annotated_cells, ratio=LEVENSHTEIN_REUSE_RATIO):
    """
    Find a reusable annotation for a target cell.

    Parameters:
        target_cell: CellData object currently being annotated.
        annotated_cells: List of previously annotated cells.
        ratio: Levenshtein threshold ratio.

    Returns:
        Dictionary with reusable annotation info, or None.
    """

    target_value = clean_basic_text(get_preferred_lookup_value(target_cell))

    if target_value == "":
        return None

    for annotated_cell in annotated_cells:
        if not has_final_annotation(annotated_cell):
            continue

        annotated_value = clean_basic_text(
            get_preferred_lookup_value(annotated_cell)
        )

        if annotated_value == "":
            continue

        if is_reusable_match(
            value_a=target_value,
            value_b=annotated_value,
            ratio=ratio,
        ):
            return {
                "matched_value": annotated_value,
                "selected_entity": annotated_cell.selected_entity,
                "final_annotation": annotated_cell.notes.get("final_cell_annotation"),
                "source_cell": {
                    "row_index": annotated_cell.row_index,
                    "col_index": annotated_cell.col_index,
                },
            }

    return None


def apply_reused_annotation(target_cell, reuse_result):
    """
    Apply a reused annotation to a target cell.
    """

    target_cell.selected_entity = reuse_result.get("selected_entity")

    final_annotation = reuse_result.get("final_annotation")

    if final_annotation:
        target_cell.notes["final_cell_annotation"] = final_annotation

    target_cell.notes["cea_reuse_applied"] = True
    target_cell.notes["cea_reuse_matched_value"] = reuse_result.get("matched_value", "")
    target_cell.notes["cea_reuse_source_cell"] = reuse_result.get("source_cell", {})

    return target_cell
