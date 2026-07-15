"""
src/routing/router.py
=====================
Assign workflow scenarios based on header strength and cell strength.

Only the 3 paper scenarios are used:
    - weak_header_strong_cells
    - strong_header_weak_cells
    - strong_header_strong_cells

The router stores:
    column.scenario                  -> column-level evidence
    table.notes["routing_table_scenario"] -> table-level workflow decision
"""

import re

from src.config import (
    ROUTER_WEAK_HEADER_MAX_LENGTH,
    ROUTER_AUTO_GENERATED_HEADER_PATTERNS,
    ROUTER_CELL_STRENGTH_THRESHOLD,
    ROUTER_TABLE_WEAK_CELL_RATIO,
)
from src.core import note_keys as NK
from src.utils.text_utils import clean_basic_text
from src.utils.table_utils import (
    is_numeric_value,
    is_date_like_value,
    is_id_like_value,
)


WEAK_HEADER_STRONG_CELLS = "weak_header_strong_cells"
STRONG_HEADER_WEAK_CELLS = "strong_header_weak_cells"
STRONG_HEADER_STRONG_CELLS = "strong_header_strong_cells"

STRONG_CELL_SCENARIOS = {
    WEAK_HEADER_STRONG_CELLS,
    STRONG_HEADER_STRONG_CELLS,
}

WEAK_CELL_SCENARIOS = {
    STRONG_HEADER_WEAK_CELLS,
}


def is_weak_header(header):
    text = clean_basic_text(header).lower()

    if text == "":
        return True

    if not re.search(r"[a-zA-Z]", text):
        return True

    if len(text) <= ROUTER_WEAK_HEADER_MAX_LENGTH:
        return True

    for pattern in ROUTER_AUTO_GENERATED_HEADER_PATTERNS:
        if re.match(pattern, text):
            return True

    return False


def is_meaningful_routing_value(value):
    text = clean_basic_text(value)

    if text == "":
        return False

    if is_numeric_value(text):
        return False

    if is_date_like_value(text):
        return False

    if is_id_like_value(text):
        return False

    return True


def get_column_routing_values(table, column):
    representative_values = column.notes.get(NK.REPRESENTATIVE_VALUES, [])

    if representative_values:
        return representative_values

    return table.get_column_values(
        col_index=column.col_index,
        cleaned=True,
    )


def calculate_cell_strength(table, column):
    values = get_column_routing_values(table, column)

    total_non_empty = 0
    meaningful_count = 0

    for value in values:
        text = clean_basic_text(value)

        if text == "":
            continue

        total_non_empty += 1

        if is_meaningful_routing_value(text):
            meaningful_count += 1

    if total_non_empty == 0:
        return 0.0

    return meaningful_count / total_non_empty


def column_cells_are_strong(table, column):
    strength_ratio = calculate_cell_strength(table, column)
    cells_are_strong = strength_ratio >= ROUTER_CELL_STRENGTH_THRESHOLD

    column.notes[NK.CELL_STRENGTH] = "strong" if cells_are_strong else "weak"
    column.notes["routing_cell_strength_ratio"] = round(strength_ratio, 3)
    column.notes["routing_cell_strength_threshold"] = ROUTER_CELL_STRENGTH_THRESHOLD
    column.notes["routing_column_cells_are_strong"] = cells_are_strong

    return cells_are_strong


def assign_column_scenario(header_is_weak, cells_are_strong):
    if not cells_are_strong:
        return STRONG_HEADER_WEAK_CELLS

    if header_is_weak:
        return WEAK_HEADER_STRONG_CELLS

    return STRONG_HEADER_STRONG_CELLS


def table_cells_are_weak(column_profiles, table_weak_cell_ratio):
    if not column_profiles:
        return False, 0, 0.0

    weak_columns = 0

    for profile in column_profiles:
        if not profile["cells_are_strong"]:
            weak_columns += 1

    weak_column_ratio = weak_columns / len(column_profiles)
    table_is_weak = weak_column_ratio >= table_weak_cell_ratio

    return table_is_weak, weak_columns, weak_column_ratio


def choose_table_scenario(table_is_weak, weak_header_columns, total_columns):
    if table_is_weak:
        return STRONG_HEADER_WEAK_CELLS

    if total_columns == 0:
        return STRONG_HEADER_STRONG_CELLS

    weak_header_ratio = weak_header_columns / total_columns

    if weak_header_ratio >= 0.5:
        return WEAK_HEADER_STRONG_CELLS

    return STRONG_HEADER_STRONG_CELLS


def route_table_columns(
    table,
    table_weak_cell_ratio=ROUTER_TABLE_WEAK_CELL_RATIO,
):
    column_profiles = []

    for column in table.columns:
        header_is_weak = is_weak_header(column.raw_name)
        cells_are_strong = column_cells_are_strong(table, column)

        column.notes[NK.HEADER_IS_WEAK] = header_is_weak

        column_profiles.append(
            {
                "column": column,
                "header_is_weak": header_is_weak,
                "cells_are_strong": cells_are_strong,
            }
        )

    table_is_weak, weak_columns, weak_column_ratio = table_cells_are_weak(
        column_profiles=column_profiles,
        table_weak_cell_ratio=table_weak_cell_ratio,
    )

    weak_header_columns = sum(
        1 for profile in column_profiles if profile["header_is_weak"]
    )

    table_scenario = choose_table_scenario(
        table_is_weak=table_is_weak,
        weak_header_columns=weak_header_columns,
        total_columns=len(column_profiles),
    )

    for profile in column_profiles:
        column = profile["column"]
        header_is_weak = profile["header_is_weak"]
        cells_are_strong = profile["cells_are_strong"]

        column.scenario = assign_column_scenario(
            header_is_weak=header_is_weak,
            cells_are_strong=cells_are_strong,
        )

        column.notes["routing_final_cells_are_strong"] = cells_are_strong

    table.notes["routed"] = True
    table.notes["routing_table_scenario"] = table_scenario
    table.notes["routing_table_cells_are_weak"] = table_is_weak
    table.notes["routing_weak_cell_columns"] = weak_columns
    table.notes["routing_total_columns"] = len(column_profiles)
    table.notes["routing_weak_column_ratio"] = round(weak_column_ratio, 3)
    table.notes["routing_weak_header_columns"] = weak_header_columns
    table.notes["routing_table_weak_cell_ratio_threshold"] = table_weak_cell_ratio

    return table


def column_has_strong_cells(column):
    return column.scenario in STRONG_CELL_SCENARIOS


def column_has_weak_cells(column):
    return column.scenario in WEAK_CELL_SCENARIOS


def count_scenarios(table):
    counts = {}

    for column in table.columns:
        scenario = column.scenario or "none"
        counts[scenario] = counts.get(scenario, 0) + 1

    return counts


def print_routing_summary(table):
    print("\n=== ROUTING SUMMARY ===")
    print("Table scenario:", table.notes.get("routing_table_scenario"))
    print("Scenario counts:", count_scenarios(table))
    print("Table weak cells:", table.notes.get("routing_table_cells_are_weak"))
    print("Weak column ratio:", table.notes.get("routing_weak_column_ratio"))

    for column in table.columns:
        print(
            f"[{column.col_index}] "
            f"raw='{column.raw_name}' | "
            f"used='{column.get_name()}' | "
            f"header_weak={column.notes.get(NK.HEADER_IS_WEAK)} | "
            f"cell_strength={column.notes.get(NK.CELL_STRENGTH)} | "
            f"ratio={column.notes.get('routing_cell_strength_ratio')} | "
            f"scenario={column.scenario}"
        )