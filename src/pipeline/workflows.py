"""
src/pipeline/workflows.py
=========================

Workflow coordination layer for the paper-inspired STA scenarios. The router
decides the scenario, while this module calls the appropriate annotation tools
and records which workflow stages were executed.
"""

from src.routing.router import STRONG_CELL_SCENARIOS, WEAK_CELL_SCENARIOS
from src.tools.topic_detection import apply_topic_detection
from src.tools.cea_tools import generate_cea_candidates, apply_cea_selection
from src.tools.cta_tools import apply_cta


def apply_topic_detection_workflow(table, provider, model):
    """
    Apply topic detection for weak-header columns.

    Parameters:
        table: TableData object.
        provider: LLM provider.
        model: LLM model.

    Returns:
        Updated TableData object.
    """

    table = apply_topic_detection(
        table=table,
        provider=provider,
        model=model,
        only_weak_headers=True,
    )

    table.notes["workflow_topic_detection_done"] = True

    return table


def generate_cea_candidates_workflow(table, source, limit, max_rows):
    """
    Generate KG candidates for CEA-compatible cells.

    Parameters:
        table: TableData object.
        source: Knowledge graph source.
        limit: Maximum candidates per lookup.
        max_rows: Maximum rows used for candidate generation.

    Returns:
        Updated TableData object.
    """

    table = generate_cea_candidates(
        table=table,
        source=source,
        limit=limit,
        max_rows=max_rows,
    )

    table.notes["workflow_cea_candidates_done"] = True
    table.notes["workflow_cea_allowed_scenarios"] = list(STRONG_CELL_SCENARIOS)
    table.notes["workflow_cea_skipped_scenarios"] = list(WEAK_CELL_SCENARIOS)

    return table


def apply_cea_selection_workflow(table, provider, model, max_cells):
    """
    Apply final CEA selection for candidate cells.

    Parameters:
        table: TableData object.
        provider: LLM provider.
        model: LLM model.
        max_cells: Maximum cells selected for CEA.

    Returns:
        Updated TableData object.
    """

    table = apply_cea_selection(
        table=table,
        provider=provider,
        model=model,
        max_cells=max_cells,
    )

    table.notes["workflow_cea_selection_done"] = True

    return table


def apply_cta_workflow(
    table,
    source,
    provider,
    model,
    max_entities,
    types_per_entity,
):
    """
    Apply CTA selection for all columns.

    Parameters:
        table: TableData object.
        source: Knowledge graph source.
        provider: LLM provider.
        model: LLM model.
        max_entities: Maximum selected CEA entities used for CTA candidates.
        types_per_entity: Maximum KG type candidates per entity.

    Returns:
        Updated TableData object.
    """

    table = apply_cta(
        table=table,
        source=source,
        provider=provider,
        model=model,
        max_entities=max_entities,
        types_per_entity=types_per_entity,
    )

    table.notes["workflow_cta_done"] = True

    return table