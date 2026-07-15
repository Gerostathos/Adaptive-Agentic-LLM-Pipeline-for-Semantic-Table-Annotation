"""
src/pipeline/pipeline.py
========================

Main runner for the semantic table annotation pipeline. It coordinates loading,
preprocessing, routing, annotation workflows, and compact report generation.
"""

from time import perf_counter

from Code.src.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
    SAMPLE_VALUES_PER_COLUMN,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_KG_SOURCE,
    KG_CANDIDATE_LIMIT,
    CEA_MAX_ROWS,
    CEA_MAX_CELLS,
    CTA_MAX_ENTITIES,
    CTA_TYPES_PER_ENTITY,
    USE_NER,
    USE_VALUE_ENRICHMENT,
    USE_CEA_REUSE,
    LEVENSHTEIN_REUSE_RATIO,
    PIPELINE_RUN_UNTIL,
    ROUTER_TABLE_WEAK_CELL_RATIO,
    LOG_STEP_LOAD,
    LOG_STEP_PREPROCESS,
    LOG_STEP_REPRESENTATIVE,
    LOG_STEP_NER,
    LOG_STEP_VALUE_ENRICHMENT,
    LOG_STEP_ROUTING,
    LOG_STEP_TOPIC_DETECTION,
    LOG_STEP_CEA_CANDIDATES,
    LOG_STEP_CEA,
    LOG_STEP_CTA,
)

from Code.src.io.loader import load_csv_table
from Code.src.preprocessing.preprocess import preprocess_table
from Code.src.preprocessing.deduplicate import add_representative_values
from Code.src.preprocessing.ner_support import add_ner_hints
from Code.src.preprocessing.value_enrichment import add_value_enrichment

from Code.src.routing.router import route_table_columns

from Code.src.pipeline.workflows import (
    apply_topic_detection_workflow,
    generate_cea_candidates_workflow,
    apply_cea_selection_workflow,
    apply_cta_workflow,
)

from Code.src.utils.log_utils import create_run_paths, RunLogger

from Code.src.pipeline.reporting import (
    report_pipeline_header,
    report_table_metadata,
    report_loaded_table,
    report_preprocessed_table,
    report_representative_values,
    report_ner_hints,
    report_value_enrichment,
    report_routing,
    report_topic_detection,
    report_cea_candidates,
    report_cea_selection,
    report_cta_selection,
    report_runtime,
)


PIPELINE_STEPS = [
    "load",
    "preprocess",
    "representative",
    "ner",
    "value_enrichment",
    "routing",
    "topic_detection",
    "cea_candidates",
    "cea",
    "cta",
]


PROVIDER_DEFAULT_MODELS = {
    "openai": DEFAULT_OPENAI_MODEL,
    "google": DEFAULT_GOOGLE_MODEL,
    "groq": DEFAULT_GROQ_MODEL,
    "ollama": DEFAULT_OLLAMA_MODEL,
}


def get_model_for_provider(provider):
    """
    Return the default model for a provider.

    Parameters:
        provider: LLM provider name.

    Returns:
        Default model name.
    """

    provider = str(provider).strip().lower()

    return PROVIDER_DEFAULT_MODELS.get(provider, DEFAULT_LLM_MODEL)


def should_stop(current_step, run_until):
    """
    Check whether the pipeline should stop after a stage.

    Parameters:
        current_step: Current stage name.
        run_until: Final requested stage.

    Returns:
        True when the current stage is the requested final stage.
    """

    return current_step == run_until


def finish_and_return(table, run_dir, logger, run_start, status, final_step):
    """
    Finalize runtime reporting and return the current table state.

    Parameters:
        table: TableData object.
        run_dir: Run output directory.
        logger: RunLogger object.
        run_start: Start time from perf_counter.
        status: Run status.
        final_step: Final completed pipeline step.

    Returns:
        TableData object and run directory.
    """

    total_seconds = perf_counter() - run_start

    report_runtime(
        logger=logger,
        total_seconds=total_seconds,
        status=status,
        final_step=final_step,
    )

    if status == "completed":
        print("\nPipeline completed.")
    else:
        print(f"\nPipeline stopped after: {final_step}")

    print("Report:", logger.report_path)

    return table, run_dir


def get_important_config_values():
    """
    Collect the configuration values written in the report header.

    Returns:
        Dictionary of selected configuration values.
    """

    return {
        "SAMPLE_VALUES_PER_COLUMN": SAMPLE_VALUES_PER_COLUMN,
        "DEFAULT_KG_SOURCE": DEFAULT_KG_SOURCE,
        "KG_CANDIDATE_LIMIT": KG_CANDIDATE_LIMIT,
        "CEA_MAX_ROWS": CEA_MAX_ROWS,
        "CEA_MAX_CELLS": CEA_MAX_CELLS,
        "CTA_MAX_ENTITIES": CTA_MAX_ENTITIES,
        "CTA_TYPES_PER_ENTITY": CTA_TYPES_PER_ENTITY,
        "USE_NER": USE_NER,
        "USE_VALUE_ENRICHMENT": USE_VALUE_ENRICHMENT,
        "USE_CEA_REUSE": USE_CEA_REUSE,
        "LEVENSHTEIN_REUSE_RATIO": LEVENSHTEIN_REUSE_RATIO,
        "ROUTER_TABLE_WEAK_CELL_RATIO": ROUTER_TABLE_WEAK_CELL_RATIO,
    }


def validate_run_until(run_until):
    """
    Validate the requested final pipeline stage.

    Parameters:
        run_until: Final requested stage.
    """

    if run_until not in PIPELINE_STEPS:
        raise ValueError(
            f"Unknown pipeline step: {run_until}. "
            f"Available steps: {PIPELINE_STEPS}"
        )


def create_logger():
    """
    Create run paths and initialize the report logger.

    Returns:
        Run directory and RunLogger object.
    """

    run_dir, report_path, run_number, timestamp = create_run_paths(
        prefix="report"
    )

    logger = RunLogger(
        report_path=report_path,
        run_number=run_number,
        timestamp=timestamp,
    )

    return run_dir, logger


def report_current_config(
    logger,
    file_path,
    dataset_name,
    split,
    provider,
    model,
    kg_source,
    run_until,
    sample_values_per_column,
    cea_max_rows,
    router_table_weak_ratio,
):
    """
    Write the pipeline run header.

    Parameters:
        logger: RunLogger object.
        file_path: Input CSV path.
        dataset_name: Dataset name.
        split: Dataset split or experiment label.
        provider: LLM provider.
        model: LLM model.
        kg_source: Knowledge graph source.
        run_until: Final requested stage.
        sample_values_per_column: Representative value limit.
        cea_max_rows: Maximum rows used for CEA candidate generation.
        router_table_weak_ratio: Table-level weak-cell ratio.
    """

    config_values = get_important_config_values()
    config_values["SAMPLE_VALUES_PER_COLUMN"] = sample_values_per_column
    config_values["CEA_MAX_ROWS"] = cea_max_rows
    config_values["ROUTER_TABLE_WEAK_CELL_RATIO"] = router_table_weak_ratio

    report_pipeline_header(
        logger=logger,
        file_path=file_path,
        dataset_name=dataset_name,
        split=split,
        provider=provider,
        model=model,
        kg_source=kg_source,
        run_until=run_until,
        config_values=config_values,
    )


def run_pipeline(
    file_path=DEFAULT_DATASET_PATH,
    dataset_name=DEFAULT_DATASET_NAME,
    split=DEFAULT_DATASET_SPLIT,
    provider=DEFAULT_LLM_PROVIDER,
    model=None,
    kg_source=DEFAULT_KG_SOURCE,
    run_until=PIPELINE_RUN_UNTIL,
    sample_values_per_column=SAMPLE_VALUES_PER_COLUMN,
    cea_max_rows=CEA_MAX_ROWS,
    router_table_weak_ratio=ROUTER_TABLE_WEAK_CELL_RATIO,
):
    """
    Run the full semantic table annotation pipeline.

    Parameters:
        file_path: Input CSV file.
        dataset_name: Dataset name written in the report.
        split: Dataset split or experiment label.
        provider: LLM provider.
        model: LLM model. If None, the provider default is used.
        kg_source: Knowledge graph source.
        run_until: Final pipeline stage to execute.
        sample_values_per_column: Representative values per column.
        cea_max_rows: Maximum rows used for CEA candidate generation.
        router_table_weak_ratio: Weak-cell ratio for table-level routing.

    Returns:
        TableData object and run directory.
    """

    run_start = perf_counter()

    provider = str(provider).strip().lower()

    if model is None:
        model = get_model_for_provider(provider)

    validate_run_until(run_until)

    run_dir, logger = create_logger()

    report_current_config(
        logger=logger,
        file_path=file_path,
        dataset_name=dataset_name,
        split=split,
        provider=provider,
        model=model,
        kg_source=kg_source,
        run_until=run_until,
        sample_values_per_column=sample_values_per_column,
        cea_max_rows=cea_max_rows,
        router_table_weak_ratio=router_table_weak_ratio,
    )

    table = load_csv_table(
        file_path=file_path,
        dataset_name=dataset_name,
        split=split,
    )

    report_table_metadata(logger, table)

    if LOG_STEP_LOAD:
        report_loaded_table(logger, table)

    if should_stop("load", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="load",
        )

    table = preprocess_table(table)

    if LOG_STEP_PREPROCESS:
        report_preprocessed_table(logger, table)

    if should_stop("preprocess", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="preprocess",
        )

    table = add_representative_values(
        table=table,
        max_values=sample_values_per_column,
    )

    if LOG_STEP_REPRESENTATIVE:
        report_representative_values(
            logger=logger,
            table=table,
            sample_values_per_column=sample_values_per_column,
        )

    if should_stop("representative", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="representative",
        )

    if USE_NER:
        table = add_ner_hints(table)

    if LOG_STEP_NER:
        report_ner_hints(
            logger=logger,
            table=table,
            enabled=USE_NER,
        )

    if should_stop("ner", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="ner",
        )

    if USE_VALUE_ENRICHMENT:
        table = add_value_enrichment(
            table=table,
            provider=provider,
            model=model,
            apply_to_cells=True,
        )

    if LOG_STEP_VALUE_ENRICHMENT:
        report_value_enrichment(
            logger=logger,
            table=table,
            enabled=USE_VALUE_ENRICHMENT,
        )

    if should_stop("value_enrichment", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="value_enrichment",
        )

    table = route_table_columns(
        table=table,
        table_weak_cell_ratio=router_table_weak_ratio,
    )

    if LOG_STEP_ROUTING:
        report_routing(logger, table)

    if should_stop("routing", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="routing",
        )

    table = apply_topic_detection_workflow(
        table=table,
        provider=provider,
        model=model,
    )

    if LOG_STEP_TOPIC_DETECTION:
        report_topic_detection(logger, table)

    if should_stop("topic_detection", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="topic_detection",
        )

    table = generate_cea_candidates_workflow(
        table=table,
        source=kg_source,
        limit=KG_CANDIDATE_LIMIT,
        max_rows=cea_max_rows,
    )

    if LOG_STEP_CEA_CANDIDATES:
        report_cea_candidates(
            logger=logger,
            table=table,
            kg_source=kg_source,
            candidate_limit=KG_CANDIDATE_LIMIT,
            max_rows=cea_max_rows,
        )

    if should_stop("cea_candidates", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="cea_candidates",
        )

    table = apply_cea_selection_workflow(
        table=table,
        provider=provider,
        model=model,
        max_cells=CEA_MAX_CELLS,
    )

    if LOG_STEP_CEA:
        report_cea_selection(
            logger=logger,
            table=table,
            provider=provider,
            model=model,
            max_cells=CEA_MAX_CELLS,
            reuse_enabled=USE_CEA_REUSE,
        )

    if should_stop("cea", run_until):
        return finish_and_return(
            table=table,
            run_dir=run_dir,
            logger=logger,
            run_start=run_start,
            status="stopped",
            final_step="cea",
        )

    table = apply_cta_workflow(
        table=table,
        source=kg_source,
        provider=provider,
        model=model,
        max_entities=CTA_MAX_ENTITIES,
        types_per_entity=CTA_TYPES_PER_ENTITY,
    )

    if LOG_STEP_CTA:
        report_cta_selection(
            logger=logger,
            table=table,
            kg_source=kg_source,
            provider=provider,
            model=model,
            max_entities=CTA_MAX_ENTITIES,
            types_per_entity=CTA_TYPES_PER_ENTITY,
        )

    return finish_and_return(
        table=table,
        run_dir=run_dir,
        logger=logger,
        run_start=run_start,
        status="completed",
        final_step="cta",
    )