"""
src/utils/table_utils.py
========================
Table utility functions used across the STA pipeline.

This file contains generic helpers that are useful in multiple steps:
CEA, value enrichment, routing, reporting, and later workflow control.
"""

import re

from src.utils.text_utils import clean_basic_text


def is_numeric_value(value):
    """
    Return True if a value looks numeric.
    """

    text = clean_basic_text(value)

    if text == "":
        return False

    text = (
        text.replace(",", "")
        .replace("%", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
    )

    try:
        float(text)
        return True

    except ValueError:
        return False


def is_date_like_value(value):
    """
    Return True if a value looks like a date or a year.

    This is intentionally lightweight and generic.
    It is not meant to be a complete date parser.
    """

    text = clean_basic_text(value)

    if text == "":
        return False

    if re.fullmatch(r"\d{4}", text):
        return True

    if re.fullmatch(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", text):
        return True

    month_pattern = (
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|"
        r"january|february|march|april|june|july|august|september|"
        r"october|november|december)\b"
    )

    return re.search(month_pattern, text, flags=re.IGNORECASE) is not None


def is_id_like_value(value):
    """
    Return True if a value looks like an identifier or code.

    Generic examples:
        A-13-B34
        SKU-1001
        ID_204
        X12
    """

    text = clean_basic_text(value)

    if text == "" or " " in text:
        return False

    has_letter = re.search(r"[A-Za-z]", text) is not None
    has_digit = re.search(r"\d", text) is not None
    has_separator = re.search(r"[-_/.:]", text) is not None

    return (has_letter and has_digit) or (has_digit and has_separator)


def clean_non_empty_values(values):
    """
    Clean values and remove empty ones.
    """

    cleaned = []

    for value in values:
        text = clean_basic_text(value)

        if text != "":
            cleaned.append(text)

    return cleaned


def value_ratio(values, check_function):
    """
    Return the ratio of values matching a check function.
    """

    values = clean_non_empty_values(values)

    if not values:
        return 0

    count = 0

    for value in values:
        if check_function(value):
            count += 1

    return count / len(values)


def format_row_context(table, row_index, target_col_index=None, value_getter=None):
    """
    Build a readable row context string.

    Example:
        Title: Inception | Director: Christopher Nolan | Country: USA
    """

    row = table.get_row_cells(row_index)
    context_parts = []

    for cell in row:
        if target_col_index is not None and cell.col_index == target_col_index:
            continue

        column_name = table.get_column_name(cell.col_index)

        if value_getter is not None:
            value = value_getter(cell)
        else:
            value = cell.cleaned_value

        value = clean_basic_text(value)

        if value == "":
            continue

        context_parts.append(f"{column_name}: {value}")

    if not context_parts:
        return "No row context available."

    return " | ".join(context_parts)