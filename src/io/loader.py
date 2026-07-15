"""
src/io/loader.py
================ 
Load raw CSV tables and convert them into the internal TableData structure.
"""

from pathlib import Path
import pandas as pd
from src.core.schema import TableData
from src.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
)

def load_csv_table(file_path, dataset_name="custom", split="debug"):
    """
    Load a CSV file into a TableData object.

    Parameters:
        file_path: Path to the CSV file.
        dataset_name: Name of the dataset.
        split: Dataset split or debug label.

    Returns:
        A TableData object.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    dataframe = pd.read_csv(
        file_path,
        encoding="utf-8",
        encoding_errors="replace",
        )

    table_id = file_path.stem

    table = TableData(
        table_id=table_id,
        dataset_name=dataset_name,
        split=split,
    )

    # Add columns from CSV headers.
    for column_name in dataframe.columns:
        table.add_column(column_name)

    # Add rows from CSV values.
    for _, row in dataframe.iterrows():
        raw_values = row.tolist()
        table.add_row(raw_values)

    table.notes["source_file"] = str(file_path)
    table.notes["loaded_with"] = "pandas"

    return table

def load_csv_tables_from_folder(
    folder_path,
    dataset_name="custom",
    split="debug",
    file_extension=".csv",
):
    """
    Load all CSV files from a folder into TableData objects.

    Parameters:
        folder_path: Path to the folder containing CSV files.
        dataset_name: Name of the dataset.
        split: Dataset split or debug label.
        file_extension: File type to load, default is ".csv".

    Returns:
        A list of TableData objects.
    """

    folder_path = Path(folder_path)

    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")

    tables = []

    csv_files = sorted(folder_path.glob(f"*{file_extension}"))

    for csv_file in csv_files:
        table = load_csv_table(
            file_path=csv_file,
            dataset_name=dataset_name,
            split=split,
        )

        tables.append(table)

    return tables

def print_loader_preview(table, max_rows=10):
    """
    Print a short preview after loading.
    """

    print("\n=== LOADER PREVIEW ===")
    print("Source file:", table.notes.get("source_file", "unknown"))
    table.print_summary(max_rows=max_rows)

def print_multi_table_preview(tables, max_tables=3, max_rows=3):
    """
    Print a short preview of multiple loaded tables.
    """

    print("\n=== MULTI-TABLE LOADER PREVIEW ===")
    print("Tables loaded:", len(tables))

    tables_to_show = tables[:max_tables]

    for table in tables_to_show:
        table.print_summary(max_rows=max_rows)
