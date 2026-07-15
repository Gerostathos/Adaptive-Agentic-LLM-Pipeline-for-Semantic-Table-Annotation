"""
src/preprocessing/ner_support.py
================================
NER support for detecting entity-type hints in table values.

This file uses spaCy to identify possible entity types in cell values.
It does not change cell values. It only stores hints for later functions.
"""

from Code.src.utils.text_utils import clean_basic_text
from collections import Counter
from Code.src.config import SAMPLE_VALUES_PER_COLUMN
from Code.src.io.loader import load_csv_table
from Code.src.preprocessing.preprocess import preprocess_table
from Code.src.preprocessing.deduplicate import add_representative_values
from Code.src.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SPLIT,
)

def load_spacy_model(model_name="en_core_web_sm"):
    """
    Load a spaCy model.

    Parameters:
        model_name: Name of the spaCy model.

    Returns:
        Loaded spaCy model, or None if unavailable.
    """

    try:
        import spacy
    except ImportError:
        print("spaCy is not installed. Install it with: python -m pip install spacy")
        return None

    try:
        return spacy.load(model_name)
    except OSError:
        print(f"spaCy model not found: {model_name}")
        print(f"Install it with: python -m spacy download {model_name}")
        return None


def detect_entity_label(value, nlp):
    """
    Detect the first NER label for one value.

    Parameters:
        value: Cleaned cell value.
        nlp: Loaded spaCy model.

    Returns:
        Entity label such as PERSON, ORG, GPE, DATE, or an empty string.
    """

    text = clean_basic_text(value)

    if text == "":
        return ""

    doc = nlp(text)

    if not doc.ents:
        return ""

    return doc.ents[0].label_


def get_column_evidence_values(table, column):
    """
    Get representative values for one column.

    If representative values exist, use them.
    Otherwise, fall back to all cleaned values.
    """

    values = column.notes.get("representative_values")

    if values is not None:
        return values

    return table.get_column_values(column.col_index, cleaned=True)[:SAMPLE_VALUES_PER_COLUMN]


def add_ner_hints(table, model_name="en_core_web_sm", max_cell_rows=10):
    """
    Add NER hints to the table.

    For each column:
        - run NER on representative values
        - count entity labels
        - store the dominant entity type

    For a limited number of rows:
        - run NER on cells
        - store cell.entity_hint

    Parameters:
        table: TableData object after preprocessing and deduplication.
        model_name: spaCy model name.
        max_cell_rows: Number of rows to process for cell-level hints.

    Returns:
        The same TableData object with NER hints stored.
    """

    nlp = load_spacy_model(model_name)

    if nlp is None:
        table.notes["ner_applied"] = False
        table.notes["ner_error"] = "spaCy model unavailable"
        return table

    # Column-level NER hints based on representative values.
    for column in table.columns:
        values = get_column_evidence_values(table, column)

        labels = []

        for value in values:
            label = detect_entity_label(value, nlp)

            if label:
                labels.append(label)

        label_counts = Counter(labels)

        if label_counts:
            dominant_type = label_counts.most_common(1)[0][0]
        else:
            dominant_type = ""

        column.notes["ner_label_counts"] = dict(label_counts)
        column.notes["dominant_entity_type"] = dominant_type

    # Cell-level NER hints for a limited preview/sample.
    rows_to_process = min(max_cell_rows, table.row_count())

    for row_index in range(rows_to_process):
        row = table.get_row_cells(row_index)

        for cell in row:
            cell.entity_hint = detect_entity_label(cell.cleaned_value, nlp)

    table.notes["ner_applied"] = True
    table.notes["ner_model"] = model_name
    table.notes["ner_cell_rows_processed"] = rows_to_process

    return table


def print_ner_summary(table):
    """
    Print column-level NER results.
    """

    print("\n=== NER SUMMARY ===")
    print("Table ID:", table.table_id)

    for column in table.columns:
        dominant_type = column.notes.get("dominant_entity_type", "")
        label_counts = column.notes.get("ner_label_counts", {})

        print(f"\nColumn {column.col_index} - {column.get_name()}")
        print("  Dominant entity type:", dominant_type if dominant_type else "None")
        print("  Label counts:", label_counts if label_counts else "{}")


def print_ner_cell_preview(table, max_rows=5):
    """
    Print a small preview of cell values and their NER hints.
    """

    print("\n=== NER CELL PREVIEW ===")
    print("Table ID:", table.table_id)

    rows_to_show = min(max_rows, table.row_count())

    for row_index in range(rows_to_show):
        print(f"\nRow {row_index}")

        for cell in table.get_row_cells(row_index):
            column_name = table.get_column_name(cell.col_index)
            hint = cell.entity_hint if cell.entity_hint else "None"

            print(f"  {column_name}: {cell.cleaned_value} → {hint}")

