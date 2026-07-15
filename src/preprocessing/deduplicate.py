"""
src/preprocessing/deduplicate.py
================================
Select representative values for each table column.

Representative values are general column evidence.
They are used by topic detection, CTA, logging, NER, and optional LLM cleaning.

This module intentionally removes only empty values.
It keeps numbers, dates, IDs, codes, categories, names, and text.
Later steps decide whether each value is useful for CEA, KG lookup, NER, etc.
"""

from collections import Counter

from src.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
    SAMPLE_VALUES_PER_COLUMN,
)

from src.io.loader import load_csv_table
from src.preprocessing.preprocess import preprocess_table
from src.utils.text_utils import clean_basic_text


def select_representative_values(values, max_values=SAMPLE_VALUES_PER_COLUMN):
    """
    Select top representative values from cleaned column values.

    Empty values are removed.
    Frequency is the main ranking signal.
    First-seen order is used as a tie-breaker.
    """

    cleaned_keys = []
    first_seen_order = {}
    canonical_values = {}

    for value in values:
        text = clean_basic_text(value)

        if text == "":
            continue

        key = text.lower()
        cleaned_keys.append(key)

        if key not in first_seen_order:
            first_seen_order[key] = len(first_seen_order)
            canonical_values[key] = text

    if not cleaned_keys:
        return []

    counts = Counter(cleaned_keys)

    ranked_keys = sorted(
        counts.keys(),
        key=lambda key: (
            -counts[key],
            first_seen_order[key],
        ),
    )

    representatives = []

    for key in ranked_keys[:max_values]:
        representatives.append(canonical_values[key])

    return representatives


def add_representative_values(table, max_values=SAMPLE_VALUES_PER_COLUMN):
    """
    Add representative values to every column.

    Stored:
        column.notes["representative_values"]
        column.notes["representative_value_count"]
    """

    for column in table.columns:
        values = table.get_column_values(
            col_index=column.col_index,
            cleaned=True,
        )

        representative_values = select_representative_values(
            values=values,
            max_values=max_values,
        )

        column.notes["representative_values"] = representative_values
        column.notes["representative_value_count"] = len(representative_values)

    table.notes["representative_values_added"] = True
    table.notes["representative_values_per_column"] = max_values

    return table


def print_representative_values(table, max_columns=None):
    """
    Print representative values for manual testing.
    """

    print("\n=== REPRESENTATIVE VALUES SUMMARY ===")
    print("Table ID:", table.table_id)

    columns = table.columns

    if max_columns is not None:
        columns = columns[:max_columns]

    for column in columns:
        values = column.notes.get("representative_values", [])

        print(f"\nColumn {column.col_index} - {column.get_name()}")
        print("Representative values:")

        if not values:
            print(" - No representative values")
            continue

        for value in values:
            print(" -", value)
