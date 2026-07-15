"""
src/pipeline/reporting_helpers.py
=================================

Reusable helpers for compact TXT report tables. The functions extract readable
rows from the table object while keeping raw prompts and long debug traces out
of the final report.
"""

from Code.src.config import LOG_SAMPLE_ROWS, LOG_MAX_CEA_CELLS
from Code.src.preprocessing.value_enrichment import get_preferred_lookup_value
from Code.src.utils.text_utils import clean_basic_text


EMPTY_VALUES = ["", None, {}, []]


def has_value(value):
    """
    Check whether a value should be counted as present.

    Parameters:
        value: Any note value.

    Returns:
        True when the value is not empty.
    """

    return value not in EMPTY_VALUES


def count_columns_with_note(table, note_name):
    """
    Count columns that contain a non-empty note value.

    Parameters:
        table: TableData object.
        note_name: Column note key.

    Returns:
        Number of columns with the requested note.
    """

    count = 0

    for column in table.columns:
        if has_value(column.notes.get(note_name, "")):
            count += 1

    return count


def count_cells_with_note(table, note_name):
    """
    Count cells that contain a non-empty note value.

    Parameters:
        table: TableData object.
        note_name: Cell note key.

    Returns:
        Number of cells with the requested note.
    """

    count = 0

    for cell in table.iter_cells():
        if has_value(cell.notes.get(note_name, "")):
            count += 1

    return count


def count_selected_types(table):
    """
    Count columns with a resolved CTA result.

    Parameters:
        table: TableData object.

    Returns:
        Number of columns with a final type label.
    """

    count = 0

    for column in table.columns:
        selected_type = column.selected_type or {}
        label = selected_type.get("label", "")

        if label and label != "Unknown":
            count += 1

    return count


def count_cea_reused_cells(table):
    """
    Count cells annotated through CEA reuse.

    Parameters:
        table: TableData object.

    Returns:
        Number of cells whose annotation was reused.
    """

    count = 0

    for cell in table.iter_cells():
        if cell.notes.get("cea_reuse_applied", False):
            count += 1

    return count


def join_values(values):
    """
    Format values as a short comma-separated string.

    Parameters:
        values: List of values.

    Returns:
        Comma-separated cleaned text.
    """

    return ", ".join(clean_basic_text(value) for value in values)


def table_value(cell, cleaned=True):
    """
    Return the raw or cleaned value of one cell.

    Parameters:
        cell: CellData object.
        cleaned: Whether to return the cleaned value.

    Returns:
        Cell value as cleaned text.
    """

    if cleaned:
        return clean_basic_text(cell.cleaned_value)

    return clean_basic_text(cell.raw_value)


def llm_answer_status(raw_answer, final_label):
    """
    Summarize whether an LLM selection produced a usable result.

    Parameters:
        raw_answer: Raw LLM response stored in notes.
        final_label: Final selected label.

    Returns:
        Compact status string.
    """

    raw_answer = clean_basic_text(raw_answer)
    final_label = clean_basic_text(final_label)

    if raw_answer == "":
        return "empty"

    if raw_answer.startswith("ERROR:"):
        return "error"

    if final_label == "" or final_label == "Unknown":
        return "unresolved"

    return "ok"


def build_table_sample_rows(table, cleaned=True, max_rows=LOG_SAMPLE_ROWS):
    """
    Build a compact sample of the table.

    Parameters:
        table: TableData object.
        cleaned: Whether to display cleaned or raw values.
        max_rows: Maximum rows included in the sample.

    Returns:
        Rows and fieldnames for the report table.
    """

    rows = []
    rows_to_log = min(max_rows, table.row_count())

    for row_index in range(rows_to_log):
        row_data = {"row": row_index}

        for cell in table.get_row_cells(row_index):
            column_name = table.get_column_name(cell.col_index)
            key = f"{cell.col_index}:{column_name}"
            row_data[key] = table_value(cell, cleaned=cleaned)

        rows.append(row_data)

    fieldnames = ["row"]

    for column in table.columns:
        fieldnames.append(
            f"{column.col_index}:{table.get_column_name(column.col_index)}"
        )

    return rows, fieldnames


def build_representative_rows(table):
    """
    Build rows showing representative values per column.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for representative value reporting.
    """

    rows = []

    for column in table.columns:
        values = column.notes.get("representative_values", [])

        rows.append(
            {
                "col": column.col_index,
                "raw_name": column.raw_name,
                "representative_values": join_values(values),
            }
        )

    return rows, ["col", "raw_name", "representative_values"]


def build_ner_rows(table):
    """
    Build rows showing the dominant NER hint per column.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for NER reporting.
    """

    rows = []

    for column in table.columns:
        rows.append(
            {
                "col": column.col_index,
                "raw_name": column.raw_name,
                "dominant_ner": column.notes.get("dominant_entity_type", "None")
                or "None",
            }
        )

    return rows, ["col", "raw_name", "dominant_ner"]


def enrichment_stats(enrichment_map):
    """
    Summarize value enrichment actions.

    Parameters:
        enrichment_map: Mapping from original values to enrichment results.

    Returns:
        Compact statistics string.
    """

    total = len(enrichment_map)
    keep_count = 0
    replace_count = 0
    error_count = 0

    for result in enrichment_map.values():
        if not isinstance(result, dict):
            continue

        action = clean_basic_text(result.get("action", "")).lower()
        raw_answer = clean_basic_text(result.get("raw_answer", ""))

        if action == "keep":
            keep_count += 1
        elif action == "replace":
            replace_count += 1

        if result.get("error", False) or raw_answer.startswith("ERROR:"):
            error_count += 1

    return (
        f"total={total}, keep={keep_count}, "
        f"replace={replace_count}, errors={error_count}"
    )


def enrichment_inspected_values(enrichment_map):
    """
    Format the values inspected during value enrichment.

    Parameters:
        enrichment_map: Mapping from original values to enrichment results.

    Returns:
        Comma-separated inspected values.
    """

    values = []

    for value in enrichment_map.keys():
        cleaned_value = clean_basic_text(value)

        if cleaned_value:
            values.append(cleaned_value)

    return ", ".join(values)


def enrichment_replacements(enrichment_map):
    """
    Format replacement actions from value enrichment.

    Parameters:
        enrichment_map: Mapping from original values to enrichment results.

    Returns:
        Replacement summary string, or an empty string when no values changed.
    """

    replacements = []

    for value, result in enrichment_map.items():
        if not isinstance(result, dict):
            continue

        action = clean_basic_text(result.get("action", "")).lower()
        enriched_value = clean_basic_text(result.get("enriched_value", ""))

        if action == "replace" and enriched_value:
            value_text = clean_basic_text(value)
            replacements.append(f"{value_text} -> {enriched_value}")

    return "; ".join(replacements)


def build_value_enrichment_rows(table):
    """
    Build compact value enrichment rows.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for value enrichment reporting.
    """

    rows = []

    for column in table.columns:
        enrichment_map = column.notes.get("value_enrichment_map", {})

        if not enrichment_map:
            continue

        rows.append(
            {
                "col": column.col_index,
                "raw_name": column.raw_name,
                "inspected_values": enrichment_inspected_values(enrichment_map),
                "stats": enrichment_stats(enrichment_map),
                "replacements": enrichment_replacements(enrichment_map),
            }
        )

    return rows, [
        "col",
        "raw_name",
        "inspected_values",
        "stats",
        "replacements",
    ]


def percent(value):
    """
    Format a ratio as a percentage.

    Parameters:
        value: Ratio value.

    Returns:
        Percentage string or empty string.
    """

    if isinstance(value, float):
        return f"{value * 100:.1f}%"

    return ""


def build_routing_rows(table):
    """
    Build routing decision rows per column.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for routing reporting.
    """

    rows = []

    for column in table.columns:
        rows.append(
            {
                "col": column.col_index,
                "raw_name": column.raw_name,
                "scenario": column.scenario or "",
                "header_weak": column.notes.get("header_is_weak", ""),
                "cell_strength": column.notes.get("cell_strength", ""),
                "strength_%": percent(
                    column.notes.get("routing_cell_strength_ratio", "")
                ),
            }
        )

    return rows, [
        "col",
        "raw_name",
        "scenario",
        "header_weak",
        "cell_strength",
        "strength_%",
    ]


def build_topic_detection_rows(table):
    """
    Build rows for columns whose names were inferred or updated.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for topic detection reporting.
    """

    rows = []

    for column in table.columns:
        raw_name = clean_basic_text(column.raw_name)
        inferred_name = clean_basic_text(column.get_name())

        answer = (
            column.notes.get("topic_detection_raw_answer", "")
            or column.notes.get("topic_detection_answer", "")
            or column.notes.get("topic_detection_clean_answer", "")
        )

        if answer or inferred_name.lower() != raw_name.lower():
            rows.append(
                {
                    "col": column.col_index,
                    "raw_name": column.raw_name,
                    "inferred_name": column.get_name(),
                }
            )

    return rows, ["col", "raw_name", "inferred_name"]


def top_candidate_label(candidates):
    """
    Return the top candidate label from a candidate list.

    Parameters:
        candidates: List of candidate dictionaries.

    Returns:
        Top candidate label or empty string.
    """

    if not candidates:
        return ""

    candidate = candidates[0]

    if isinstance(candidate, dict):
        return candidate.get("label", "")

    return str(candidate)


def build_cea_candidate_rows(table, max_cells=LOG_MAX_CEA_CELLS):
    """
    Build compact CEA candidate rows.

    Parameters:
        table: TableData object.
        max_cells: Maximum cells displayed.

    Returns:
        Rows and fieldnames for CEA candidate reporting.
    """

    rows = []

    for cell in table.iter_cells():
        if len(rows) >= max_cells:
            break

        candidates = cell.notes.get("cea_candidates", [])

        if not candidates:
            continue

        rows.append(
            {
                "row": cell.row_index,
                "col": cell.col_index,
                "column": table.get_column_name(cell.col_index),
                "cell_value": clean_basic_text(get_preferred_lookup_value(cell)),
                "entity_candidate_count": len(candidates),
                "top_entity_candidate": top_candidate_label(candidates),
            }
        )

    return rows, [
        "row",
        "col",
        "column",
        "cell_value",
        "entity_candidate_count",
        "top_entity_candidate",
    ]


def build_cea_selection_rows(table, max_cells=LOG_MAX_CEA_CELLS):
    """
    Build compact final CEA rows.

    Parameters:
        table: TableData object.
        max_cells: Maximum cells displayed.

    Returns:
        Rows and fieldnames for CEA selection reporting.
    """

    rows = []

    for cell in table.iter_cells():
        if len(rows) >= max_cells:
            break

        annotation = cell.notes.get("final_cell_annotation", {})

        if not annotation:
            continue

        raw_answer = cell.notes.get("cea_selection_raw_answer", "")
        final_label = annotation.get("label", "")

        rows.append(
            {
                "row": cell.row_index,
                "col": cell.col_index,
                "column": table.get_column_name(cell.col_index),
                "cell_value": clean_basic_text(get_preferred_lookup_value(cell)),
                "cell_annotation_source": annotation.get("source", ""),
                "cell_annotation_label": final_label,
                "llm_status": llm_answer_status(raw_answer, final_label),
                "reuse": cell.notes.get("cea_reuse_applied", False),
            }
        )

    return rows, [
        "row",
        "col",
        "column",
        "cell_value",
        "cell_annotation_source",
        "cell_annotation_label",
        "llm_status",
        "reuse",
    ]


def build_cta_rows(table):
    """
    Build compact final CTA rows.

    Parameters:
        table: TableData object.

    Returns:
        Rows and fieldnames for CTA reporting.
    """

    rows = []

    for column in table.columns:
        selected_type = column.selected_type or {}
        ranked_types = column.ranked_type_candidates or []

        if not selected_type:
            continue

        raw_answer = column.notes.get("cta_raw_answer", "")
        final_label = selected_type.get("label", "")

        rows.append(
            {
                "col": column.col_index,
                "raw_name": column.raw_name,
                "inferred_name": column.get_name(),
                "kg_type_candidates": len(ranked_types),
                "top_kg_type_candidate": top_candidate_label(ranked_types),
                "column_type_source": selected_type.get("source", ""),
                "column_type_label": final_label,
                "llm_status": llm_answer_status(raw_answer, final_label),
            }
        )

    return rows, [
        "col",
        "raw_name",
        "inferred_name",
        "kg_type_candidates",
        "top_kg_type_candidate",
        "column_type_source",
        "column_type_label",
        "llm_status",
    ]