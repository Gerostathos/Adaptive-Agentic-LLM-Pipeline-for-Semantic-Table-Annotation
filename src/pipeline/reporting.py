"""
src/pipeline/reporting.py
=========================

Compact report sections for one semantic table annotation run. 
"""

from src.config import LOG_TABLE_MAX_WIDTH
from src.utils.log_utils import log_step
from src.routing.router import STRONG_CELL_SCENARIOS

from src.pipeline.reporting_helpers import (
    count_columns_with_note,
    count_cells_with_note,
    count_selected_types,
    count_cea_reused_cells,
    build_table_sample_rows,
    build_representative_rows,
    build_ner_rows,
    build_value_enrichment_rows,
    build_routing_rows,
    build_topic_detection_rows,
    build_cea_candidate_rows,
    build_cea_selection_rows,
    build_cta_rows,
)


def write_step(logger, title, rows=None, fieldnames=None, info=None, detail="Details"):
    """
    Write a completed report section.

    Parameters:
        logger: RunLogger object.
        title: Section title.
        rows: Optional table rows.
        fieldnames: Optional table fieldnames.
        info: Optional key-value summary.
        detail: Table subtitle.
    """

    log_step(
        logger=logger,
        title=title,
        status="DONE",
        info=info,
        rows=rows,
        fieldnames=fieldnames,
        detail_title=detail,
        max_width=LOG_TABLE_MAX_WIDTH,
    )


def write_skip(logger, title, reason):
    """
    Write a skipped report section.

    Parameters:
        logger: RunLogger object.
        title: Section title.
        reason: Reason for skipping the section.
    """

    log_step(
        logger=logger,
        title=title,
        status="SKIPPED",
        info={"reason": reason},
    )


def has_strong_cell_columns(table):
    """
    Check whether the table has at least one strong-cell column.

    Parameters:
        table: TableData object.

    Returns:
        True when CEA-related stages can run.
    """

    for column in table.columns:
        if column.scenario in STRONG_CELL_SCENARIOS:
            return True

    return False


def scenario_counts(table):
    """
    Count routing scenarios across columns.

    Parameters:
        table: TableData object.

    Returns:
        Dictionary mapping scenario names to counts.
    """

    counts = {}

    for column in table.columns:
        scenario = column.scenario or "none"
        counts[scenario] = counts.get(scenario, 0) + 1

    return counts


def report_pipeline_header(
    logger,
    file_path,
    dataset_name,
    split,
    provider,
    model,
    kg_source,
    run_until,
    config_values,
):
    """
    Write the pipeline run overview.

    Parameters:
        logger: RunLogger object.
        file_path: Input file path.
        dataset_name: Dataset name.
        split: Dataset split or experiment label.
        provider: LLM provider.
        model: LLM model.
        kg_source: Knowledge graph source.
        run_until: Final executed stage.
        config_values: Selected configuration values.
    """

    logger.section("00 - PIPELINE RUN OVERVIEW")

    logger.key_values(
        {
            "report_name": logger.report_path.name,
            "report_folder": str(logger.run_dir),
            "run_number_today": logger.run_number,
            "timestamp": logger.timestamp,
            "dataset_name": dataset_name,
            "dataset_split": split,
            "dataset_path": file_path,
            "llm_provider": provider,
            "llm_model": model,
            "kg_source": kg_source,
            "run_until": run_until,
        }
    )

    logger.subsection("Configuration")
    logger.key_values(config_values)


def report_table_metadata(logger, table):
    """
    Write basic table metadata.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
    """

    logger.subsection("Table metadata")

    logger.key_values(
        {
            "table_id": table.table_id,
            "dataset_name": table.dataset_name,
            "split": table.split,
            "source_file": table.notes.get("source_file", ""),
            "rows": table.row_count(),
            "columns": table.col_count(),
        }
    )


def report_table_sample(logger, table, title, cleaned, purpose):
    """
    Write a table sample section.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        title: Section title.
        cleaned: Whether to display cleaned values.
        purpose: Short section purpose.
    """

    rows, fieldnames = build_table_sample_rows(table, cleaned=cleaned)

    write_step(
        logger=logger,
        title=title,
        info={"purpose": purpose},
        rows=rows,
        fieldnames=fieldnames,
        detail="Sample",
    )


def report_loaded_table(logger, table):
    """
    Write the loaded table sample.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
    """

    report_table_sample(
        logger=logger,
        table=table,
        title="01 - LOADED TABLE SAMPLE",
        cleaned=False,
        purpose="Raw table sample before preprocessing.",
    )


def report_preprocessed_table(logger, table):
    """
    Write the preprocessed table sample.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
    """

    report_table_sample(
        logger=logger,
        table=table,
        title="02 - PREPROCESSED TABLE SAMPLE",
        cleaned=True,
        purpose="Cleaned table sample after preprocessing.",
    )


def report_representative_values(logger, table, sample_values_per_column):
    """
    Write representative values per column.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        sample_values_per_column: Maximum representative values per column.
    """

    rows, fieldnames = build_representative_rows(table)

    write_step(
        logger=logger,
        title="03 - REPRESENTATIVE VALUES",
        info={
            "columns_processed": table.col_count(),
            "sample_values_per_column": sample_values_per_column,
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="Column evidence",
    )


def report_ner_hints(logger, table, enabled=True):
    """
    Write NER hints per column.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        enabled: Whether NER was enabled.
    """

    if not enabled:
        write_skip(logger, "04 - NER HINTS", "NER disabled")
        return

    rows, fieldnames = build_ner_rows(table)

    write_step(
        logger=logger,
        title="04 - NER HINTS",
        info={
            "columns_processed": table.col_count(),
            "columns_with_dominant_ner": count_columns_with_note(
                table,
                "dominant_entity_type",
            ),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="NER hints",
    )


def report_value_enrichment(logger, table, enabled=True):
    """
    Write value enrichment results.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        enabled: Whether value enrichment was enabled.
    """

    if not enabled:
        write_skip(logger, "05 - VALUE ENRICHMENT", "value enrichment disabled")
        return

    rows, fieldnames = build_value_enrichment_rows(table)

    if not rows:
        write_skip(logger, "05 - VALUE ENRICHMENT", "no enrichment entries produced")
        return

    write_step(
        logger=logger,
        title="05 - VALUE ENRICHMENT",
        info={
            "columns_processed": table.col_count(),
            "columns_with_value_enrichment": count_columns_with_note(
                table,
                "value_enrichment_map",
            ),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="Value enrichment",
    )


def report_routing(logger, table):
    """
    Write routing decisions.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
    """

    rows, fieldnames = build_routing_rows(table)

    write_step(
        logger=logger,
        title="06 - ROUTING",
        info={
            "table_scenario": table.notes.get("routing_table_scenario", ""),
            "scenario_counts": scenario_counts(table),
            "table_cells_are_weak": table.notes.get(
                "routing_table_cells_are_weak",
                False,
            ),
            "weak_column_ratio": table.notes.get("routing_weak_column_ratio", ""),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="Routing decisions",
    )


def report_topic_detection(logger, table):
    """
    Write topic detection results.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
    """

    rows, fieldnames = build_topic_detection_rows(table)

    if not rows:
        write_skip(logger, "07 - TOPIC DETECTION", "no column topic update required")
        return

    write_step(
        logger=logger,
        title="07 - TOPIC DETECTION",
        rows=rows,
        fieldnames=fieldnames,
        detail="Inferred column names",
    )


def report_cea_candidates(logger, table, kg_source, candidate_limit, max_rows):
    """
    Write CEA candidate generation results.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        kg_source: Knowledge graph source.
        candidate_limit: Maximum KG candidates per cell.
        max_rows: Maximum rows used for candidate generation.
    """

    if not has_strong_cell_columns(table):
        write_skip(logger, "08 - CEA CANDIDATES", "no strong-cell columns")
        return

    rows, fieldnames = build_cea_candidate_rows(table)

    if not rows:
        write_skip(logger, "08 - CEA CANDIDATES", "no KG candidates produced")
        return

    write_step(
        logger=logger,
        title="08 - CEA CANDIDATES",
        info={
            "kg_source": kg_source,
            "candidate_limit": candidate_limit,
            "max_rows": max_rows,
            "cells_with_candidates": count_cells_with_note(
                table,
                "cea_candidates",
            ),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="CEA candidate sample",
    )


def report_cea_selection(logger, table, provider, model, max_cells, reuse_enabled):
    """
    Write final CEA selection results.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        provider: LLM provider.
        model: LLM model.
        max_cells: Maximum cells selected for CEA.
        reuse_enabled: Whether CEA reuse was enabled.
    """

    if not has_strong_cell_columns(table):
        write_skip(logger, "09 - CEA SELECTION", "no strong-cell columns")
        return

    rows, fieldnames = build_cea_selection_rows(table)

    if not rows:
        write_skip(logger, "09 - CEA SELECTION", "no final cell annotations")
        return

    write_step(
        logger=logger,
        title="09 - CEA SELECTION",
        info={
            "provider": provider,
            "model": model,
            "max_cells": max_cells,
            "reuse_enabled": reuse_enabled,
            "cells_with_final_annotation": count_cells_with_note(
                table,
                "final_cell_annotation",
            ),
            "cells_reused_by_levenshtein": count_cea_reused_cells(table),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="Final CEA annotations",
    )


def report_cta_selection(
    logger,
    table,
    kg_source,
    provider,
    model,
    max_entities,
    types_per_entity,
):
    """
    Write final CTA selection results.

    Parameters:
        logger: RunLogger object.
        table: TableData object.
        kg_source: Knowledge graph source.
        provider: LLM provider.
        model: LLM model.
        max_entities: Maximum CEA entities used for CTA candidates.
        types_per_entity: Maximum KG type candidates per entity.
    """

    rows, fieldnames = build_cta_rows(table)

    write_step(
        logger=logger,
        title="10 - CTA SELECTION",
        info={
            "kg_source": kg_source,
            "provider": provider,
            "model": model,
            "max_entities": max_entities,
            "types_per_entity": types_per_entity,
            "columns_with_final_type": count_selected_types(table),
        },
        rows=rows,
        fieldnames=fieldnames,
        detail="Final CTA annotations",
    )


def report_runtime(logger, total_seconds, status, final_step):
    """
    Write total runtime for the pipeline run.

    Parameters:
        logger: RunLogger object.
        total_seconds: Total elapsed runtime in seconds.
        status: Run status.
        final_step: Final completed step.
    """

    logger.section("11 - RUNTIME")

    logger.key_values(
        {
            "status": status,
            "final_step": final_step,
            "total_seconds": round(total_seconds, 3),
        }
    )