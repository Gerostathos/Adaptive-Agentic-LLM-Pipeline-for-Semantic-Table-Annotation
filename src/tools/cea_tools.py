"""
src/tools/cea_tools.py
======================

Implements Cell Entity Annotation for strong-cell workflows. The module
retrieves KG entity candidates, asks the LLM for one final annotation label,
and stores either a KG-grounded entity or a direct LLM semantic annotation.
"""

from src.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_KG_SOURCE,
    KG_CANDIDATE_LIMIT,
    CEA_MAX_ROWS,
    CEA_MAX_CELLS,
    USE_CEA_REUSE,
    LEVENSHTEIN_REUSE_RATIO,
)

from src.core import note_keys as NK
from src.tools.levenshtein_reuse import (
    find_reusable_annotation,
    apply_reused_annotation,
)
from src.preprocessing.value_enrichment import get_preferred_lookup_value
from src.kg.kg_manager import get_entity_candidates
from src.llm.llm_client import ask_llm
from src.llm.prompt_manager import format_prompt
from src.utils.text_utils import clean_basic_text
from src.utils.table_utils import format_row_context
from src.utils.prompt_utils import format_candidates_for_prompt
from src.utils.label_parser import parse_candidate_or_label_response


STRONG_CELL_SCENARIOS = {
    "weak_header_strong_cells",
    "strong_header_strong_cells",
}


def is_strong_cell_column(column):
    """
    Return whether the column scenario supports CEA.

    Parameters:
        column: ColumnData object.

    Returns:
        True when entity annotation is meaningful for the column.
    """

    return column.scenario in STRONG_CELL_SCENARIOS


def is_cea_target_cell(table, cell):
    """
    Decide whether a cell should be processed by CEA.

    Parameters:
        table: TableData object.
        cell: CellData object.

    Returns:
        True when the cell belongs to a strong-cell workflow and has a usable
        lookup value.
    """

    if table.notes.get("routing_table_cells_are_weak", False):
        cell.notes[NK.CEA_SKIP_REASON] = "weak_cell_table"
        return False

    column = table.columns[cell.col_index]

    if not is_strong_cell_column(column):
        cell.notes[NK.CEA_SKIP_REASON] = "weak_cell_column"
        return False

    value = clean_basic_text(get_preferred_lookup_value(cell))

    if value == "":
        cell.notes[NK.CEA_SKIP_REASON] = "empty_value"
        return False

    cell.notes[NK.CEA_SKIP_REASON] = ""
    return True


def iter_cea_target_cells(table, max_rows=None, max_cells=None):
    """
    Iterate over cells selected for CEA.

    Parameters:
        table: TableData object.
        max_rows: Maximum number of rows to inspect.
        max_cells: Maximum number of target cells to yield.

    Returns:
        Generator of CellData objects.
    """

    if max_rows is None:
        rows_to_process = table.row_count()
    else:
        rows_to_process = min(max_rows, table.row_count())

    yielded_cells = 0

    for row_index in range(rows_to_process):
        row = table.get_row_cells(row_index)

        for cell in row:
            if not is_cea_target_cell(table, cell):
                cell.notes[NK.CEA_TARGET] = False
                cell.notes[NK.CEA_CANDIDATE_SKIPPED] = True
                continue

            cell.notes[NK.CEA_TARGET] = True
            cell.notes[NK.CEA_CANDIDATE_SKIPPED] = False

            yield cell

            yielded_cells += 1

            if max_cells is not None and yielded_cells >= max_cells:
                return


def generate_cea_candidates(
    table,
    source=DEFAULT_KG_SOURCE,
    limit=KG_CANDIDATE_LIMIT,
    max_rows=CEA_MAX_ROWS,
):
    """
    Retrieve KG entity candidates for CEA target cells.

    Parameters:
        table: TableData object.
        source: Knowledge graph source.
        limit: Maximum candidates per lookup.
        max_rows: Maximum rows used for candidate generation.

    Returns:
        Updated TableData object.
    """

    query_cache = {}
    processed_targets = 0

    for cell in iter_cea_target_cells(
        table=table,
        max_rows=max_rows,
        max_cells=None,
    ):
        query = clean_basic_text(get_preferred_lookup_value(cell))

        if query in query_cache:
            candidates = query_cache[query]
        else:
            candidates = get_entity_candidates(
                query=query,
                source=source,
                limit=limit,
            )
            query_cache[query] = candidates

        cell.entity_candidates = candidates

        cell.notes["cea_candidates"] = candidates
        cell.notes[NK.CEA_CANDIDATE_QUERY] = query
        cell.notes[NK.CEA_CANDIDATE_SOURCE] = source
        cell.notes[NK.CEA_CANDIDATE_COUNT] = len(candidates)
        cell.notes[NK.CEA_CANDIDATE_SKIPPED] = False

        processed_targets += 1

    table.notes["cea_candidates_generated"] = True
    table.notes["cea_candidate_source"] = source
    table.notes["cea_candidate_max_rows"] = max_rows
    table.notes["cea_candidate_target_cells"] = processed_targets

    return table


def build_final_annotation_from_kg(entity):
    """
    Build the final cell annotation from a selected KG entity.

    Parameters:
        entity: Selected KG entity dictionary.

    Returns:
        Final annotation dictionary.
    """

    return {
        "source": "kg",
        "label": entity.get("label", ""),
        "id": entity.get("id", ""),
        "description": entity.get("description", ""),
        "url": entity.get("url", ""),
    }


def build_final_annotation_from_llm(label):
    """
    Build the final cell annotation from an LLM semantic label.

    Parameters:
        label: Clean semantic label.

    Returns:
        Final annotation dictionary.
    """

    return {
        "source": "llm",
        "label": label,
        "id": "",
        "description": "",
        "url": "",
    }


def build_unknown_annotation():
    """
    Build a neutral annotation for unresolved cells.

    Returns:
        Final annotation dictionary.
    """

    return {
        "source": "none",
        "label": "Unknown",
        "id": "",
        "description": "",
        "url": "",
    }


def select_annotation_for_cell(
    table,
    cell,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
):
    """
    Select the final annotation for one cell.

    Parameters:
        table: TableData object.
        cell: CellData object.
        provider: LLM provider.
        model: LLM model.

    Returns:
        Selected KG entity, final annotation, prompt, and raw LLM answer.
    """

    candidates = cell.entity_candidates or []
    cell_value = clean_basic_text(get_preferred_lookup_value(cell))
    column_name = table.get_column_name(cell.col_index)

    row_context = format_row_context(
        table=table,
        row_index=cell.row_index,
        target_col_index=cell.col_index,
        value_getter=get_preferred_lookup_value,
    )

    prompt = format_prompt(
        prompt_name="cea_selection",
        values={
            "cell_value": cell_value,
            "column_name": column_name,
            "row_context": row_context,
            "candidates": format_candidates_for_prompt(candidates),
        },
    )

    raw_answer = ask_llm(
        prompt=prompt,
        provider=provider,
        model=model,
    )

    mode, selected_entity, final_label = parse_candidate_or_label_response(
        answer=raw_answer,
        candidates=candidates,
        max_words=8,
    )

    if mode == "kg":
        final_annotation = build_final_annotation_from_kg(selected_entity)
        return selected_entity, final_annotation, prompt, raw_answer

    if mode == "llm":
        final_annotation = build_final_annotation_from_llm(final_label)
        return None, final_annotation, prompt, raw_answer

    return None, build_unknown_annotation(), prompt, raw_answer


def should_store_for_reuse(cell):
    """
    Decide whether a cell annotation can be reused.

    Parameters:
        cell: CellData object.

    Returns:
        True when the cell has a valid final annotation.
    """

    final_annotation = cell.notes.get(NK.FINAL_CELL_ANNOTATION, {})
    label = final_annotation.get("label", "")

    if label == "" or label == "Unknown":
        return False

    return True


def store_cea_notes(cell, final_annotation, prompt, raw_answer, provider, model):
    """
    Store CEA selection metadata on a cell.

    Parameters:
        cell: CellData object.
        final_annotation: Final annotation dictionary.
        prompt: Prompt sent to the LLM.
        raw_answer: Raw LLM response.
        provider: LLM provider.
        model: LLM model.

    Returns:
        Updated CellData object.
    """

    cell.notes[NK.FINAL_CELL_ANNOTATION] = final_annotation
    cell.notes[NK.CEA_SELECTION_PROMPT] = prompt
    cell.notes[NK.CEA_SELECTION_RAW_ANSWER] = raw_answer
    cell.notes["cea_selection_provider"] = provider
    cell.notes["cea_selection_model"] = model
    cell.notes[NK.CEA_REUSE_APPLIED] = False
    cell.notes["cea_selected"] = cell.selected_entity is not None

    return cell


def apply_cea_selection(
    table,
    provider=DEFAULT_LLM_PROVIDER,
    model=DEFAULT_LLM_MODEL,
    max_cells=CEA_MAX_CELLS,
):
    """
    Apply CEA selection to target cells.

    Parameters:
        table: TableData object.
        provider: LLM provider.
        model: LLM model.
        max_cells: Maximum cells selected for CEA.

    Returns:
        Updated TableData object.
    """

    processed_cells = 0
    reusable_cells = []

    for cell in iter_cea_target_cells(
        table=table,
        max_rows=None,
        max_cells=max_cells,
    ):
        if USE_CEA_REUSE:
            reuse_result = find_reusable_annotation(
                target_cell=cell,
                annotated_cells=reusable_cells,
                ratio=LEVENSHTEIN_REUSE_RATIO,
            )

            if reuse_result is not None:
                apply_reused_annotation(
                    target_cell=cell,
                    reuse_result=reuse_result,
                )

                cell.notes[NK.CEA_SELECTION_PROMPT] = ""
                cell.notes[NK.CEA_SELECTION_RAW_ANSWER] = "REUSED"
                cell.notes["cea_selection_provider"] = "reuse"
                cell.notes["cea_selection_model"] = "levenshtein"
                cell.notes["cea_selected"] = cell.selected_entity is not None

                if should_store_for_reuse(cell):
                    reusable_cells.append(cell)

                processed_cells += 1
                continue

        selected_entity, final_annotation, prompt, raw_answer = select_annotation_for_cell(
            table=table,
            cell=cell,
            provider=provider,
            model=model,
        )

        cell.selected_entity = selected_entity

        store_cea_notes(
            cell=cell,
            final_annotation=final_annotation,
            prompt=prompt,
            raw_answer=raw_answer,
            provider=provider,
            model=model,
        )

        if should_store_for_reuse(cell):
            reusable_cells.append(cell)

        processed_cells += 1

    table.notes["cea_selection_applied"] = True
    table.notes["cea_selection_mode"] = "hybrid"
    table.notes["cea_reuse_enabled"] = USE_CEA_REUSE
    table.notes["cea_reuse_ratio"] = LEVENSHTEIN_REUSE_RATIO
    table.notes["cea_selection_max_cells"] = max_cells
    table.notes["cea_selection_processed_cells"] = processed_cells

    return table