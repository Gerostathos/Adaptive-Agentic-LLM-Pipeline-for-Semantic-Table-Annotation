"""
src/pipeline/cli.py
===================

Command-line execution for the semantic table annotation pipeline.
"""

import argparse
from pathlib import Path

import src.config as config


def str_to_bool(value):
    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "y"}:
        return True

    if normalized in {"false", "0", "no", "n"}:
        return False

    raise argparse.ArgumentTypeError("Expected true or false.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the semantic table annotation pipeline."
    )

    parser.add_argument(
        "--file",
        default=None,
        help="Path to one input CSV file.",
    )

    parser.add_argument(
        "--folder",
        default=None,
        help="Folder containing CSV files.",
    )

    parser.add_argument(
        "--dataset-name",
        default=config.DEFAULT_DATASET_NAME,
        help="Dataset name used in the generated report.",
    )

    parser.add_argument(
        "--split",
        default=config.DEFAULT_DATASET_SPLIT,
        help="Dataset split or experiment label used in the generated report.",
    )

    parser.add_argument(
        "--provider",
        default=config.DEFAULT_LLM_PROVIDER,
        help="LLM provider: google, groq, openai, or ollama.",
    )

    parser.add_argument(
        "--llm",
        default=None,
        help="LLM model name. If omitted, the provider default is used.",
    )

    parser.add_argument(
        "--kg",
        default=config.DEFAULT_KG_SOURCE,
        help="Knowledge graph source.",
    )

    parser.add_argument(
        "--run-until",
        default=config.PIPELINE_RUN_UNTIL,
        choices=config.PIPELINE_STEPS,
        help="Final pipeline step to execute.",
    )

    parser.add_argument(
        "--sample-values",
        type=int,
        default=config.SAMPLE_VALUES_PER_COLUMN,
        help="Number of representative values selected per column.",
    )

    parser.add_argument(
        "--kg-candidate-limit",
        type=int,
        default=config.KG_CANDIDATE_LIMIT,
        help="Number of KG candidates retrieved per cell.",
    )

    parser.add_argument(
        "--cea-max-rows",
        type=int,
        default=config.CEA_MAX_ROWS,
        help="Maximum number of rows used for CEA candidate generation.",
    )

    parser.add_argument(
        "--cea-max-cells",
        type=int,
        default=config.CEA_MAX_CELLS,
        help="Maximum number of cells selected for CEA.",
    )

    parser.add_argument(
        "--cta-max-entities",
        type=int,
        default=config.CTA_MAX_ENTITIES,
        help="Maximum number of annotated entities used for CTA candidates.",
    )

    parser.add_argument(
        "--cta-types-per-entity",
        type=int,
        default=config.CTA_TYPES_PER_ENTITY,
        help="Maximum number of type candidates retrieved per entity.",
    )

    parser.add_argument(
        "--router-table-weak-ratio",
        type=float,
        default=config.ROUTER_TABLE_WEAK_CELL_RATIO,
        help="Weak-column ratio used for table-level routing.",
    )

    parser.add_argument(
        "--reuse-threshold",
        type=float,
        default=config.LEVENSHTEIN_REUSE_RATIO,
        help="Similarity threshold ratio used for CEA reuse.",
    )

    parser.add_argument(
        "--ner",
        type=str_to_bool,
        default=config.USE_NER,
        help="Enable or disable NER. Use true or false.",
    )

    parser.add_argument(
        "--value-enrichment",
        type=str_to_bool,
        default=config.USE_VALUE_ENRICHMENT,
        help="Enable or disable value enrichment. Use true or false.",
    )

    parser.add_argument(
        "--cea-reuse",
        type=str_to_bool,
        default=config.USE_CEA_REUSE,
        help="Enable or disable CEA reuse. Use true or false.",
    )

    return parser.parse_args()


def apply_cli_config(args):
    config.SAMPLE_VALUES_PER_COLUMN = args.sample_values

    config.KG_CANDIDATE_LIMIT = args.kg_candidate_limit
    config.CEA_CANDIDATE_LIMIT = args.kg_candidate_limit

    config.CEA_MAX_ROWS = args.cea_max_rows
    config.CEA_MAX_CELLS = args.cea_max_cells

    config.CTA_MAX_ENTITIES = args.cta_max_entities
    config.CTA_TYPES_PER_ENTITY = args.cta_types_per_entity

    config.ROUTER_TABLE_WEAK_CELL_RATIO = args.router_table_weak_ratio
    config.LEVENSHTEIN_REUSE_RATIO = args.reuse_threshold

    config.USE_NER = args.ner
    config.USE_VALUE_ENRICHMENT = args.value_enrichment
    config.USE_CEA_REUSE = args.cea_reuse

    config.REPORT_MODE = "compact"
    config.LOG_PROMPTS_AND_ANSWERS = False

    config.CTA_USE_KG_CANDIDATES = True
    config.CTA_ALLOW_LLM_FALLBACK = True
    config.CTA_FINAL_SELECTION_MODE = "hybrid"


def get_csv_files(folder_path):
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")

    csv_files = sorted(folder.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {folder}")

    return csv_files


def run_one_file(args, file_path):
    from src.pipeline.pipeline import run_pipeline

    print(f"\nRunning pipeline for: {file_path}")

    return run_pipeline(
        file_path=str(file_path),
        dataset_name=args.dataset_name,
        split=args.split,
        provider=args.provider,
        model=args.llm,
        kg_source=args.kg,
        run_until=args.run_until,
        sample_values_per_column=args.sample_values,
        cea_max_rows=args.cea_max_rows,
        router_table_weak_ratio=args.router_table_weak_ratio,
    )


def run_folder(args, folder_path):
    csv_files = get_csv_files(folder_path)

    print(f"\nFound {len(csv_files)} CSV files in {folder_path}")

    for index, csv_file in enumerate(csv_files, start=1):
        print("\n" + "=" * 80)
        print(f"File {index}/{len(csv_files)}")
        print("=" * 80)

        run_one_file(args, csv_file)

    print("\nFolder execution completed.")


def main():
    args = parse_args()

    if args.file and args.folder:
        raise ValueError("Use either --file or --folder, not both.")

    apply_cli_config(args)

    if args.folder:
        run_folder(args, args.folder)
        return

    if args.file:
        run_one_file(args, args.file)
        return

    run_one_file(args, config.DEFAULT_DATASET_PATH)


if __name__ == "__main__":
    main()