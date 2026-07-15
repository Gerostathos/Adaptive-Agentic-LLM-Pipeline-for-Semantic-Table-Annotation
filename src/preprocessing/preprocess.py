"""
src/preprocessing/preprocess.py
===============================
Basic preprocessing utilities for cleaning table cell values.

This file performs lightweight, dataset-independent cleaning.
"""

from Code.src.utils.text_utils import clean_basic_text
from Code.src.io.loader import load_csv_table
from Code.src.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
)

MISSING_VALUES = {
    "",
    " ",
    "-",
    "--",
    "---",
    "_",
    "null",
    "none",
    "nan",
    "n/a",
    "na",
    "n.a.",
    "unk",
    "missing",
    "no data",
    "nodata",
    "not known",
    "undefined",
    "unknown",
    "nil",
    "empty",
    "?",
    "??"
}


def clean_text(value):
    """
    Clean one raw cell value in a generic way.
    """

    text = clean_basic_text(value)

    if text.lower() in MISSING_VALUES:
        return ""

    return text


def preprocess_table(table):
    """
    Clean all cell values in a TableData object.

    Parameters:
        table: TableData object created by the loader.

    Returns:
        The same TableData object with cell.cleaned_value filled.
    """

    for cell in table.iter_cells():
        cell.cleaned_value = clean_text(cell.raw_value)

    table.notes["preprocessed"] = True

    return table


def get_non_empty_ratio(values):
    """
    Calculate the ratio of non-empty cleaned values in a list.
    """

    if not values:
        return 0

    non_empty_count = 0

    for value in values:
        if clean_text(value) != "":
            non_empty_count += 1

    return non_empty_count / len(values)


def print_cleaning_preview(table, max_rows=5):
    """
    Print raw and cleaned values side by side.
    """

    print("\n=== PREPROCESSING PREVIEW ===")
    print("Table ID:", table.table_id)

    rows_to_show = min(max_rows, table.row_count())

    for row_index in range(rows_to_show):
        raw_values = table.get_row_values(row_index, cleaned=False)
        cleaned_values = table.get_row_values(row_index, cleaned=True)

        print(f"\nRow {row_index}")
        print("  Raw:    ", raw_values)
        print("  Cleaned:", cleaned_values)

