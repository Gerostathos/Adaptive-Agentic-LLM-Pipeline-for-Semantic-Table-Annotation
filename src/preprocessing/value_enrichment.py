"""
src/preprocessing/value_enrichment.py
=====================================
LLM-based value enrichment for spelling correction and abbreviation expansion.

This version uses one LLM call per column, not one call per cell/value.

It stores:
    column.notes["value_enrichment_map"]
    cell.notes["preferred_lookup_value"]

It does not overwrite raw_value or cleaned_value.
"""

from Code.src.config import (
    SAMPLE_VALUES_PER_COLUMN,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
)

from Code.src.utils.table_utils import (
    clean_non_empty_values,
    is_numeric_value,
    is_date_like_value,
    is_id_like_value,
    value_ratio,
)

from Code.src.utils.text_utils import clean_basic_text, format_values_as_bullets
from Code.src.io.loader import load_csv_table
from Code.src.preprocessing.preprocess import preprocess_table
from Code.src.preprocessing.deduplicate import add_representative_values
from Code.src.preprocessing.ner_support import add_ner_hints
from Code.src.llm.llm_client import ask_llm
from Code.src.llm.prompt_manager import format_prompt


MAX_REPLACEMENT_WORDS = 8
MIN_VALUES_TO_ENRICH = 2
SKIP_RATIO = 0.8


# ============================================================
# Generic value / column checks
# ============================================================

def get_representative_values(table, col_index):
    """
    Return representative values for one column.
    """

    column = table.columns[col_index]
    values = column.notes.get("representative_values", [])

    if values:
        return values

    return table.get_column_values(
        col_index=col_index,
        cleaned=True,
    )[:SAMPLE_VALUES_PER_COLUMN]


def should_enrich_column(table, col_index):
    """
    Decide whether LLM value enrichment is useful for this column.

    Representative values are general column evidence.
    This function skips columns where LLM cleaning is unlikely to help:
        - too few values
        - mostly numeric
        - mostly date-like
        - mostly ID/code-like
    """

    values = clean_non_empty_values(
        get_representative_values(table, col_index)
    )

    if len(values) < MIN_VALUES_TO_ENRICH:
        return False, "not_enough_values", values

    if value_ratio(values, is_numeric_value) >= SKIP_RATIO:
        return False, "numeric_column", values

    if value_ratio(values, is_date_like_value) >= SKIP_RATIO:
        return False, "date_column", values

    if value_ratio(values, is_id_like_value) >= SKIP_RATIO:
        return False, "id_like_column", values

    return True, "text_column", values

# ============================================================
# Parsing
# ============================================================

def keep_result(value, raw_answer=""):
    """
    Standard KEEP result.
    """

    return {
        "original_value": clean_basic_text(value),
        "action": "keep",
        "enriched_value": "",
        "raw_answer": raw_answer,
    }


def replace_result(value, replacement, raw_answer=""):
    """
    Standard REPLACE result with safety checks.
    """

    original = clean_basic_text(value)
    replacement = clean_basic_text(replacement)

    if replacement == "":
        return keep_result(original, raw_answer)

    if replacement.lower() == original.lower():
        return keep_result(original, raw_answer)

    if len(replacement.split()) > MAX_REPLACEMENT_WORDS:
        return keep_result(original, raw_answer)

    return {
        "original_value": original,
        "action": "replace",
        "enriched_value": replacement,
        "raw_answer": raw_answer,
    }


def parse_enrichment_answer(answer, values):
    """
    Parse line-based output.

    Expected:
        value -> KEEP
        value -> REPLACE: normalized value

    Missing or invalid decisions default to KEEP.
    """

    answer = "" if answer is None else str(answer)
    value_by_lower = {}

    for value in values:
        text = clean_basic_text(value)

        if text != "":
            value_by_lower[text.lower()] = text

    enrichment_map = {}

    for value in value_by_lower.values():
        enrichment_map[value] = keep_result(value, raw_answer=answer)

    if answer.strip().startswith("ERROR:"):
        for value in enrichment_map:
            enrichment_map[value]["error"] = True

        return enrichment_map

    for line in answer.splitlines():
        line = clean_basic_text(line)

        if "->" not in line:
            continue

        left, right = line.split("->", 1)
        original = clean_basic_text(left)
        decision = clean_basic_text(right)

        if original.lower() not in value_by_lower:
            continue

        original = value_by_lower[original.lower()]
        lower_decision = decision.lower()

        if lower_decision.startswith("replace:"):
            replacement = decision.split(":", 1)[1].strip()
            enrichment_map[original] = replace_result(
                value=original,
                replacement=replacement,
                raw_answer=answer,
            )

        elif lower_decision.startswith("keep"):
            enrichment_map[original] = keep_result(
                value=original,
                raw_answer=answer,
            )

    return enrichment_map


# ============================================================
# LLM enrichment
# ============================================================

def enrich_column_values(
    table,
    col_index,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
):
    """
    Call the LLM once for one column.
    """

    column = table.columns[col_index]
    should_run, reason, values = should_enrich_column(table, col_index)

    column.notes["value_enrichment_checked"] = True
    column.notes["value_enrichment_skip_reason"] = reason
    column.notes["value_enrichment_provider"] = provider
    column.notes["value_enrichment_model"] = model

    if not should_run:
        column.notes["value_enrichment_map"] = {}
        column.notes["value_enrichment_applied"] = False
        return {}

    prompt = format_prompt(
        prompt_name="value_enrichment",
        values={
            "column_name": table.get_column_name(col_index),
            "dominant_entity_type": column.notes.get("dominant_entity_type", "None"),
            "representative_values": format_values_as_bullets(values),
            "cell_value": format_values_as_bullets(values),
        },
    )

    answer = ask_llm(
        prompt=prompt,
        provider=provider,
        model=model,
    )

    enrichment_map = parse_enrichment_answer(
        answer=answer,
        values=values,
    )

    column.notes["value_enrichment_map"] = enrichment_map
    column.notes["value_enrichment_applied"] = True

    return enrichment_map


def apply_enrichment_to_column_cells(table, col_index, enrichment_map):
    """
    Attach preferred lookup values to cells.
    """

    for cell in table.get_column_cells(col_index):
        cell_value = clean_basic_text(cell.cleaned_value)

        if cell_value == "":
            continue

        result = enrichment_map.get(cell_value)

        if result is None:
            cell.notes["preferred_lookup_value"] = cell.cleaned_value
            continue

        cell.notes["value_enrichment_action"] = result.get("action", "keep")
        cell.notes["value_enriched_value"] = result.get("enriched_value", "")
        cell.notes["value_enrichment_raw_answer"] = result.get("raw_answer", "")

        if result.get("action") == "replace":
            cell.notes["preferred_lookup_value"] = result.get("enriched_value", "")
        else:
            cell.notes["preferred_lookup_value"] = cell.cleaned_value


def add_value_enrichment(
    table,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
    apply_to_cells=True,
):
    """
    Apply value enrichment to the table column by column.
    """

    for column in table.columns:
        enrichment_map = enrich_column_values(
            table=table,
            col_index=column.col_index,
            provider=provider,
            model=model,
        )

        if apply_to_cells:
            apply_enrichment_to_column_cells(
                table=table,
                col_index=column.col_index,
                enrichment_map=enrichment_map,
            )

    table.notes["value_enrichment_applied"] = True
    table.notes["value_enrichment_mode"] = "column_batch"

    return table


def get_preferred_lookup_value(cell):
    """
    Return the best value for KG lookup.
    """

    preferred_value = cell.notes.get("preferred_lookup_value")

    if preferred_value:
        return preferred_value

    return cell.cleaned_value


# ============================================================
# Backward-compatible single-value function
# ============================================================

def enrich_one_value(
    table,
    col_index,
    value,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
):
    """
    Backward-compatible helper for old tests.

    It still calls the LLM once, but only for one value.
    New pipeline code should prefer add_value_enrichment().
    """

    column = table.columns[col_index]
    value = clean_basic_text(value)

    prompt = format_prompt(
        prompt_name="value_enrichment",
        values={
            "column_name": table.get_column_name(col_index),
            "dominant_entity_type": column.notes.get("dominant_entity_type", "None"),
            "representative_values": format_values_as_bullets([value]),
            "cell_value": value,
        },
    )

    answer = ask_llm(
        prompt=prompt,
        provider=provider,
        model=model,
    )

    return parse_enrichment_answer(
        answer=answer,
        values=[value],
    ).get(value, keep_result(value, raw_answer=answer))


# ============================================================
# Manual test
# ============================================================

def print_value_enrichment_summary(table):
    """
    Print value enrichment decisions.
    """

    print("\n=== VALUE ENRICHMENT SUMMARY ===")

    for column in table.columns:
        enrichment_map = column.notes.get("value_enrichment_map", {})
        reason = column.notes.get("value_enrichment_skip_reason", "")

        print(f"\nColumn {column.col_index}: {column.get_name()}")
        print("Reason:", reason)

        if not enrichment_map:
            print("No enrichment applied.")
            continue

        for value, result in enrichment_map.items():
            action = result.get("action", "keep")
            replacement = result.get("enriched_value", "")

            if action == "replace":
                print(f"  {value} -> REPLACE: {replacement}")
            else:
                print(f"  {value} -> KEEP")
