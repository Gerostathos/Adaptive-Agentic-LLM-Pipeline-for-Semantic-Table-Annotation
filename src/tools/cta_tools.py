"""
src/tools/cta_tools.py
======================

Implements Column Type Annotation. The module derives KG type candidates from
selected CEA entities when available, then stores one final semantic type per
column using either a KG-grounded type or an LLM fallback label.
"""

from collections import Counter

from src.config import (
    SAMPLE_VALUES_PER_COLUMN,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_KG_SOURCE,
    CTA_MAX_ENTITIES,
    CTA_TYPES_PER_ENTITY,
    CTA_USE_KG_CANDIDATES,
    CTA_ALLOW_LLM_FALLBACK,
    CTA_FINAL_SELECTION_MODE,
)

from src.core import note_keys as NK
from src.routing.router import column_has_strong_cells, column_has_weak_cells
from src.kg.kg_manager import get_entity_types
from src.llm.llm_client import run_llm_prompt
from src.utils.text_utils import clean_basic_text, format_values_as_bullets
from src.utils.prompt_utils import format_candidates_for_prompt
from src.utils.label_parser import parse_candidate_or_label_response


def get_representative_values(table, col_index):
    """
    Return representative values for one column.

    Parameters:
        table: TableData object.
        col_index: Column index.

    Returns:
        List of representative values.
    """

    column = table.columns[col_index]
    values = column.notes.get(NK.REPRESENTATIVE_VALUES)

    if values is not None:
        return values

    return table.get_column_values(
        col_index=col_index,
        cleaned=True,
    )[:SAMPLE_VALUES_PER_COLUMN]


def get_display_values_for_column(table, col_index):
    """
    Return values used as CTA evidence.

    Parameters:
        table: TableData object.
        col_index: Column index.

    Returns:
        List of cleaned or enriched representative values.
    """

    column = table.columns[col_index]
    enrichment_map = column.notes.get(NK.VALUE_ENRICHMENT_MAP, {})
    display_values = []

    for value in get_representative_values(table, col_index):
        text = clean_basic_text(value)

        if text == "":
            continue

        result = enrichment_map.get(text)

        if result and result.get("action") == "replace" and result.get("enriched_value"):
            display_values.append(result.get("enriched_value"))
        else:
            display_values.append(text)

    return display_values[:SAMPLE_VALUES_PER_COLUMN]


def get_other_column_names(table, target_col_index):
    """
    Return non-target column names as context.

    Parameters:
        table: TableData object.
        target_col_index: Column excluded from the context list.

    Returns:
        Bullet-formatted column names.
    """

    names = []

    for column in table.columns:
        if column.col_index == target_col_index:
            continue

        name = clean_basic_text(column.get_name())

        if name:
            names.append(name)

    if not names:
        return "- None"

    return format_values_as_bullets(names)


def get_column_final_annotations(table, col_index, max_annotations=CTA_MAX_ENTITIES):
    """
    Return final CEA annotations from one column.

    Parameters:
        table: TableData object.
        col_index: Column index.
        max_annotations: Maximum annotations to collect.

    Returns:
        List of annotation dictionaries.
    """

    annotations = []

    for cell in table.get_column_cells(col_index):
        final_annotation = cell.notes.get(NK.FINAL_CELL_ANNOTATION)

        if not final_annotation:
            continue

        label = clean_basic_text(final_annotation.get("label", ""))

        if label == "" or label == "Unknown":
            continue

        annotations.append(
            {
                "source": final_annotation.get("source", ""),
                "label": label,
                "id": final_annotation.get("id", ""),
                "description": final_annotation.get("description", ""),
            }
        )

        if len(annotations) >= max_annotations:
            break

    return annotations


def format_annotations_for_prompt(annotations, fallback_context=""):
    """
    Format CEA annotations for the CTA prompt.

    Parameters:
        annotations: List of annotation dictionaries.
        fallback_context: Text used when annotations are unavailable.

    Returns:
        Prompt-ready text.
    """

    if not annotations:
        return fallback_context or "- None"

    lines = []

    for annotation in annotations:
        label = annotation.get("label", "")
        source = annotation.get("source", "")
        description = annotation.get("description", "")

        line = f"- {label} [{source}]"

        if description:
            line += f" - {description}"

        lines.append(line)

    return "\n".join(lines)


def get_selected_entities_for_column(table, col_index, max_entities=CTA_MAX_ENTITIES):
    """
    Return KG entities selected during CEA.

    Parameters:
        table: TableData object.
        col_index: Column index.
        max_entities: Maximum selected entities to collect.

    Returns:
        List of KG entity dictionaries.
    """

    selected_entities = []

    for cell in table.get_column_cells(col_index):
        if cell.selected_entity is None:
            continue

        selected_entities.append(cell.selected_entity)

        if len(selected_entities) >= max_entities:
            break

    return selected_entities


def collect_type_candidates_for_column(
    table,
    col_index,
    source=DEFAULT_KG_SOURCE,
    max_entities=CTA_MAX_ENTITIES,
    types_per_entity=CTA_TYPES_PER_ENTITY,
):
    """
    Collect and rank KG type candidates for one column.

    Parameters:
        table: TableData object.
        col_index: Column index.
        source: Knowledge graph source.
        max_entities: Maximum selected entities used as evidence.
        types_per_entity: Maximum KG type candidates per entity.

    Returns:
        Ranked type candidate dictionaries.
    """

    selected_entities = get_selected_entities_for_column(
        table=table,
        col_index=col_index,
        max_entities=max_entities,
    )

    type_counter = Counter()
    type_map = {}

    for entity in selected_entities:
        for type_candidate in get_entity_types(
            entity=entity,
            source=source,
            limit=types_per_entity,
        ):
            type_id = type_candidate.get("id", "")

            if type_id == "":
                continue

            type_counter[type_id] += 1
            type_map[type_id] = type_candidate

    ranked_types = []

    for type_id, frequency in type_counter.most_common():
        candidate = dict(type_map[type_id])
        candidate["frequency"] = frequency
        ranked_types.append(candidate)

    return ranked_types


def build_column_type_from_kg(type_candidate):
    """
    Build the selected column type from a KG candidate.

    Parameters:
        type_candidate: Selected KG type candidate dictionary.

    Returns:
        Final column type dictionary.
    """

    return {
        "source": "kg",
        "label": type_candidate.get("label", ""),
        "id": type_candidate.get("id", ""),
        "description": type_candidate.get("description", ""),
        "url": type_candidate.get("url", ""),
    }


def build_column_type_from_llm(label):
    """
    Build the selected column type from an LLM semantic label.

    Parameters:
        label: Clean semantic type label.

    Returns:
        Final column type dictionary.
    """

    return {
        "source": "llm",
        "label": label,
        "id": "",
        "description": "",
        "url": "",
    }


def build_unknown_column_type():
    """
    Build a neutral type for unresolved columns.

    Returns:
        Final column type dictionary.
    """

    return {
        "source": "none",
        "label": "Unknown",
        "id": "",
        "description": "",
        "url": "",
    }


def should_collect_kg_types_for_column(table, column):
    """
    Decide whether KG-derived CTA candidates can be collected.

    Parameters:
        table: TableData object.
        column: ColumnData object.

    Returns:
        True when the column has KG-grounded entity evidence.
    """

    if not CTA_USE_KG_CANDIDATES:
        return False

    if table.notes.get("routing_table_cells_are_weak", False):
        return False

    return column_has_strong_cells(column)


def build_cta_prompt_values(table, column, ranked_types):
    """
    Build prompt values for CTA selection.

    Parameters:
        table: TableData object.
        column: ColumnData object.
        ranked_types: Ranked KG type candidates.

    Returns:
        Dictionary of formatted prompt values.
    """

    col_index = column.col_index
    display_values = get_display_values_for_column(table, col_index)
    annotations = get_column_final_annotations(table, col_index)

    table_is_weak_cell = table.notes.get("routing_table_cells_are_weak", False)
    column_is_weak_cell = column_has_weak_cells(column)

    fallback_context = ""

    if table_is_weak_cell or column_is_weak_cell:
        fallback_context = (
            "Cell annotations are not available for this column.\n"
            "Other column names:\n"
            f"{get_other_column_names(table, col_index)}"
        )

    return {
        "column_name": table.get_column_name(col_index),
        "column_values": format_values_as_bullets(display_values),
        "cell_annotations": format_annotations_for_prompt(
            annotations,
            fallback_context=fallback_context,
        ),
        "type_candidates": format_candidates_for_prompt(
            ranked_types,
            empty_message="No KG type candidates available.",
        ),
    }


def select_type_for_column(
    table,
    column,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
):
    """
    Select the final semantic type for one column.

    Parameters:
        table: TableData object.
        column: ColumnData object.
        provider: LLM provider.
        model: LLM model.

    Returns:
        Final column type dictionary, prompt, and raw LLM answer.
    """

    ranked_types = column.ranked_type_candidates or []

    prompt, raw_answer = run_llm_prompt(
        prompt_name="cta_selection",
        values=build_cta_prompt_values(table, column, ranked_types),
        provider=provider,
        model=model,
    )

    mode, selected_candidate, final_label = parse_candidate_or_label_response(
        answer=raw_answer,
        candidates=ranked_types,
        max_words=8,
    )

    if mode == "kg":
        selected_type = build_column_type_from_kg(selected_candidate)
        return selected_type, prompt, raw_answer

    if mode == "llm" and CTA_ALLOW_LLM_FALLBACK:
        selected_type = build_column_type_from_llm(final_label)
        return selected_type, prompt, raw_answer

    return build_unknown_column_type(), prompt, raw_answer


def apply_cta(
    table,
    source=DEFAULT_KG_SOURCE,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
    max_entities=CTA_MAX_ENTITIES,
    types_per_entity=CTA_TYPES_PER_ENTITY,
):
    """
    Apply CTA to every column in the table.

    Parameters:
        table: TableData object.
        source: Knowledge graph source.
        provider: LLM provider.
        model: LLM model.
        max_entities: Maximum CEA entities used for KG type candidates.
        types_per_entity: Maximum KG type candidates per entity.

    Returns:
        Updated TableData object.
    """

    for column in table.columns:
        if should_collect_kg_types_for_column(table, column):
            ranked_types = collect_type_candidates_for_column(
                table=table,
                col_index=column.col_index,
                source=source,
                max_entities=max_entities,
                types_per_entity=types_per_entity,
            )
        else:
            ranked_types = []

        column.ranked_type_candidates = ranked_types
        column.type_candidates = ranked_types

        selected_type, prompt, raw_answer = select_type_for_column(
            table=table,
            column=column,
            provider=provider,
            model=model,
        )

        column.selected_type = selected_type

        column.notes[NK.CTA_PROMPT] = prompt
        column.notes[NK.CTA_RAW_ANSWER] = raw_answer
        column.notes[NK.CTA_PROVIDER] = provider
        column.notes[NK.CTA_MODEL] = model
        column.notes[NK.CTA_SOURCE] = source
        column.notes[NK.CTA_SELECTED_TYPE] = selected_type
        column.notes[NK.CTA_SELECTED_TYPE_SOURCE] = selected_type.get("source", "")
        column.notes[NK.CTA_SELECTED_TYPE_LABEL] = selected_type.get("label", "")
        column.notes["cta_final_selection_mode"] = CTA_FINAL_SELECTION_MODE

    table.notes["cta_applied"] = True
    table.notes["cta_source"] = source
    table.notes["cta_final_selection_mode"] = CTA_FINAL_SELECTION_MODE

    return table