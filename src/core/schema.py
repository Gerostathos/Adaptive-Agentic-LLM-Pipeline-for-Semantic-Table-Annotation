"""
src/core/schema.py
================== 
Core table structures used across the semantic table annotation pipeline.
"""

class CellData:
    """
    Represents one cell in a table.
    """

    def __init__(self, row_index, col_index, raw_value):
        # Position of the cell inside the table.
        self.row_index = row_index
        self.col_index = col_index

        # Original value from the CSV file.
        self.raw_value = str(raw_value)

        # Value after preprocessing.
        self.cleaned_value = ""

        # Optional NER hint.
        self.entity_hint = None

        # Candidate entities retrieved from DBpedia or Wikidata.
        self.entity_candidates = []

        # Final selected entity for CEA.
        self.selected_entity = None

        # Extra debugging or extension information.
        self.notes = {}

    def get_value(self, cleaned=False):
        """
        Return either the raw value or the cleaned value.
        """
        if cleaned:
            return self.cleaned_value

        return self.raw_value

    def has_clean_value(self):
        """
        Return True if the cell has a non-empty cleaned value.
        """
        return self.cleaned_value.strip() != ""

    def has_selected_entity(self):
        """
        Return True if CEA selected an entity for this cell.
        """
        return self.selected_entity is not None

class ColumnData:
    """
    Represents one column in a table.
    """

    def __init__(self, col_index, raw_name):
        # Position of the column inside the table.
        self.col_index = col_index

        # Original and inferred column names.
        self.raw_name = str(raw_name)
        self.semantic_name = None

        # Scenario assigned by the router.
        # Example: weak_header_strong_cells.
        self.scenario = None

        # Candidate column types for CTA.
        self.type_candidates = []

        # Ranked CTA candidates after scoring.
        self.ranked_type_candidates = []

        # Final selected type for CTA.
        self.selected_type = None

        # Extra debugging or extension information.
        self.notes = {}

    def get_name(self):
        """
        Return the best available column name.
        """
        if self.semantic_name:
            return self.semantic_name

        return self.raw_name

    def has_selected_type(self):
        """
        Return True if CTA selected a type for this column.
        """
        return self.selected_type is not None

class TableData:
    """
    Represents a full table with columns and rows.
    """

    def __init__(self, table_id, dataset_name="unknown", split="unknown"):
        # Basic table identity.
        self.table_id = str(table_id)
        self.dataset_name = dataset_name
        self.split = split

        # List of ColumnData objects.
        self.columns = []

        # List of rows. Each row is a list of CellData objects.
        self.rows = []

        # Extra debugging or extension information.
        self.notes = {}

    def add_column(self, raw_name):
        """
        Add one column to the table.

        Returns:
            The created ColumnData object.
        """
        col_index = len(self.columns)
        column = ColumnData(col_index, raw_name)
        self.columns.append(column)

        return column

    def add_row(self, raw_values):
        """
        Add one row to the table from raw values.

        Parameters:
            raw_values: List of raw cell values.
        """
        row_index = len(self.rows)
        row = []

        for col_index, value in enumerate(raw_values):
            cell = CellData(row_index, col_index, value)
            row.append(cell)

        self.rows.append(row)

        return row

    def row_count(self):
        """
        Return the number of rows in the table.
        """
        return len(self.rows)

    def col_count(self):
        """
        Return the number of columns in the table.
        """
        return len(self.columns)

    def get_cell(self, row_index, col_index):
        """
        Return one cell by row and column index.
        """
        if row_index < 0 or row_index >= self.row_count():
            return None

        row = self.rows[row_index]

        if col_index < 0 or col_index >= len(row):
            return None

        return row[col_index]

    def get_row_cells(self, row_index):
        """
        Return all cells from one row.
        """
        if row_index < 0 or row_index >= self.row_count():
            return []

        return self.rows[row_index]

    def get_column_cells(self, col_index):
        """
        Return all cells from one column.
        """
        cells = []

        for row in self.rows:
            if col_index < len(row):
                cells.append(row[col_index])

        return cells

    def get_row_values(self, row_index, cleaned=False):
        """
        Return raw or cleaned values from one row.
        """
        values = []

        for cell in self.get_row_cells(row_index):
            values.append(cell.get_value(cleaned=cleaned))

        return values

    def get_column_values(self, col_index, cleaned=False):
        """
        Return raw or cleaned values from one column.
        """
        values = []

        for cell in self.get_column_cells(col_index):
            values.append(cell.get_value(cleaned=cleaned))

        return values

    def get_column_name(self, col_index):
        """
        Return the best available name for a column.
        """
        if col_index < 0 or col_index >= self.col_count():
            return ""

        return self.columns[col_index].get_name()

    def iter_cells(self):
        """
        Iterate through all cells in the table.
        """
        for row in self.rows:
            for cell in row:
                yield cell

    def get_selected_entities(self):
        """
        Return all cells that have selected CEA entities.
        """
        selected = []

        for cell in self.iter_cells():
            if cell.has_selected_entity():
                selected.append(cell)

        return selected

    def get_selected_types(self):
        """
        Return all columns that have selected CTA types.
        """
        selected = []

        for column in self.columns:
            if column.has_selected_type():
                selected.append(column)

        return selected

    def print_summary(self, max_rows=5, cleaned=False):
        """
        Print a readable summary of the table object.

        Parameters:
            max_rows: Maximum number of rows to print.
            cleaned: If True, print cleaned values instead of raw values.
        """
        print("\n=== TABLE SUMMARY ===")
        print("Table ID:", self.table_id)
        print("Dataset:", self.dataset_name)
        print("Split:", self.split)
        print("Rows:", self.row_count())
        print("Columns:", self.col_count())

        print("\nColumn overview:")
        for column in self.columns:
            scenario = column.scenario if column.scenario else "not assigned"

            print(
                f"  [{column.col_index}] "
                f"raw name: '{column.raw_name}' | "
                f"used name: '{column.get_name()}' | "
                f"scenario: {scenario}"
            )

        print("\nSample rows:")
        max_rows_to_show = min(max_rows, self.row_count())

        for row_index in range(max_rows_to_show):
            values = self.get_row_values(row_index, cleaned=cleaned)
            print(f"  Row {row_index}: {values}")

