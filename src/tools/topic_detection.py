"""
src/tools/topic_detection.py
============================
LLM-based topic detection for weak or unclear table column headers.

This file infers a semantic topic for columns using representative values.
The inferred topic is stored in column.semantic_name and later supports
CEA and CTA.
"""

from src.config import (
    SAMPLE_VALUES_PER_COLUMN,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    USE_NER,
    USE_VALUE_ENRICHMENT,
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
)

from src.utils.text_utils import (
    clean_basic_text,
    format_values_as_bullets,
    clean_short_label,
)

from src.io.loader import load_csv_table
from src.preprocessing.preprocess import preprocess_table
from src.preprocessing.deduplicate import add_representative_values
from src.preprocessing.ner_support import add_ner_hints
from src.preprocessing.value_enrichment import add_value_enrichment
from src.routing.router import route_table_columns, print_routing_summary
from src.llm.llm_client import ask_llm
from src.llm.prompt_manager import format_prompt


def get_representative_values(table, col_index):
    """
    Get the shared representative values for one column.

    The values should normally come from deduplicate.py.
    """

    column = table.columns[col_index]
    values = column.notes.get("representative_values")

    if values is not None:
        return values

    return table.get_column_values(col_index, cleaned=True)[:SAMPLE_VALUES_PER_COLUMN]


def get_display_values_for_topic(table, col_index):
    """
    Get values used for topic detection.

    If value enrichment suggested a replacement, use it.
    Otherwise, use the original representative value.
    """

    column = table.columns[col_index]
    representative_values = get_representative_values(table, col_index)
    enrichment_map = column.notes.get("value_enrichment_map", {})

    display_values = []

    for value in representative_values:
        text = clean_basic_text(value)

        if text == "":
            continue

        enrichment_result = enrichment_map.get(text)

        if enrichment_result:
            action = enrichment_result.get("action", "keep")
            enriched_value = enrichment_result.get("enriched_value", "")

            if action == "replace" and enriched_value:
                display_values.append(enriched_value)
            else:
                display_values.append(text)
        else:
            display_values.append(text)

    return display_values[:SAMPLE_VALUES_PER_COLUMN]


def clean_topic_answer(answer):
    """
    Clean the LLM topic answer into a short readable label.
    """

    return clean_short_label(
        answer=answer,
        max_words=5,
        fallback="Unknown",
    )


def detect_column_topic(
    table,
    col_index,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
):
    """
    Infer a semantic topic for one column.

    Parameters:
        table: TableData object.
        col_index: Target column index.
        provider: LLM provider.
        model: LLM model.

    Returns:
        topic, prompt, raw_answer
    """

    column = table.columns[col_index]

    values = get_display_values_for_topic(
        table=table,
        col_index=col_index,
    )

    prompt = format_prompt(
        prompt_name="topic_detection",
        values={
            "raw_column_name": column.raw_name,
            "dominant_entity_type": column.notes.get("dominant_entity_type", "None"),
            "cell_values": format_values_as_bullets(values),
        },
    )

    raw_answer = ask_llm(
        prompt=prompt,
        provider=provider,
        model=model,
    )

    topic = clean_topic_answer(raw_answer)

    return topic, prompt, raw_answer


def should_detect_topic_for_column(column):
    """
    Decide whether topic detection should run for one column.

    For now, topic detection runs mainly for weak-header columns.
    """

    return column.notes.get("header_is_weak", False)


def apply_topic_detection(
    table,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
    only_weak_headers=True,
):
    """
    Apply topic detection to table columns.

    Topic detection is skipped for weak-cell tables because the cell evidence is
    not reliable enough to infer useful column topics.
    """

    table_is_weak_cell = table.notes.get("routing_table_cells_are_weak", False)

    for column in table.columns:
        if table_is_weak_cell:
            column.notes["topic_detection_skipped"] = True
            column.notes["topic_detection_skip_reason"] = "weak_cell_table"
            continue

        run_detection = True

        if only_weak_headers:
            run_detection = should_detect_topic_for_column(column)

        if not run_detection:
            column.notes["topic_detection_skipped"] = True
            column.notes["topic_detection_skip_reason"] = "strong_header"
            continue

        topic, prompt, raw_answer = detect_column_topic(
            table=table,
            col_index=column.col_index,
            provider=provider,
            model=model,
        )

        if topic != "Unknown":
            column.semantic_name = topic
        else:
            column.notes["topic_detection_unknown"] = True

        column.notes["topic_detection_prompt"] = prompt
        column.notes["topic_detection_raw_answer"] = raw_answer
        column.notes["topic_detection_applied"] = True
        column.notes["topic_detection_provider"] = provider
        column.notes["topic_detection_model"] = model

    table.notes["topic_detection_applied"] = True

    return table


def print_topic_detection_summary(table):
    """
    Print a summary of inferred column topics.
    """

    print("\n=== TOPIC DETECTION SUMMARY ===")
    print("Table ID:", table.table_id)

    for column in table.columns:
        raw_answer = column.notes.get("topic_detection_raw_answer", "")
        applied = column.notes.get("topic_detection_applied", False)
        skipped = column.notes.get("topic_detection_skipped", False)

        print(f"\nColumn {column.col_index}")
        print("  Raw name:", column.raw_name)
        print("  Scenario:", column.scenario)
        print("  Used name:", column.get_name())

        if applied:
            print("  LLM raw answer:", raw_answer)
        elif skipped:
            print("  Topic detection skipped.")
        else:
            print("  Topic detection not applied.")

