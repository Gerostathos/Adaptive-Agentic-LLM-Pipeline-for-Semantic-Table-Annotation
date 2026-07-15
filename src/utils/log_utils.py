"""
src/utils/log_utils.py
======================
Generic TXT logging utilities.

This file should stay generic. It should not know about CEA, CTA,
topic detection, or semantic table annotation internals.
"""

from datetime import datetime
from pathlib import Path

from src.config import RUNS_LOG_DIR, LOG_SUMMARY_MAX_WIDTH


def create_run_paths(prefix="report"):
    """
    Create one date folder and one incremented TXT report path.

    Example:
        logs/runs/2026-05-09/report_001_231045.txt
    """

    now = datetime.now()
    date_folder_name = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")

    run_dir = Path(RUNS_LOG_DIR) / date_folder_name
    run_dir.mkdir(parents=True, exist_ok=True)

    existing_reports = sorted(run_dir.glob(f"{prefix}_*.txt"))
    run_number = len(existing_reports) + 1

    report_name = f"{prefix}_{run_number:03d}_{timestamp}.txt"
    report_path = run_dir / report_name

    return run_dir, report_path, run_number, timestamp


class RunLogger:
    """
    One-file TXT logger for one pipeline run.
    """

    def __init__(self, report_path, run_number=None, timestamp=None):
        self.report_path = Path(report_path)
        self.run_dir = self.report_path.parent
        self.run_number = run_number
        self.timestamp = timestamp

        self.report_path.write_text(
            "SEMANTIC TABLE ANNOTATION RUN REPORT\n"
            "====================================\n\n",
            encoding="utf-8",
        )

    def append(self, text=""):
        """
        Append text to the report.
        """

        with self.report_path.open("a", encoding="utf-8") as file:
            file.write(str(text))

            if not str(text).endswith("\n"):
                file.write("\n")

    def section(self, title, status=None):
        """
        Add a main section.
        """

        if status:
            title = f"{title} [{status}]"

        self.append("\n" + "=" * 80)
        self.append(title)
        self.append("=" * 80)

    def subsection(self, title):
        """
        Add a subsection.
        """

        self.append("\n" + "-" * 80)
        self.append(title)
        self.append("-" * 80)

    def key_values(self, data):
        """
        Log key-value pairs.
        """

        for key, value in data.items():
            self.append(f"{key}: {value}")

    def rows(
        self,
        rows,
        fieldnames,
        drop_empty_fields=True,
        max_width=LOG_SUMMARY_MAX_WIDTH,
    ):
        """
        Log rows as a table-like TXT block.
        """

        if not rows:
            self.append("No rows available.")
            return

        display_rows = []

        for row in rows:
            display_row = {}

            for field in fieldnames:
                value = row.get(field, "")

                if value is None:
                    value = ""

                value = str(value)
                value = value.replace("\n", "\\n").replace("\t", "\\t")

                display_row[field] = value

            display_rows.append(display_row)

        if drop_empty_fields:
            kept_fields = []

            for field in fieldnames:
                has_value = any(
                    str(row.get(field, "")).strip() != ""
                    for row in display_rows
                )

                if has_value:
                    kept_fields.append(field)

            fieldnames = kept_fields

        if not fieldnames:
            self.append("No non-empty fields available.")
            return

        widths = {}

        for field in fieldnames:
            width = len(str(field))

            for row in display_rows:
                width = max(width, len(row.get(field, "")))

            if max_width is not None:
                width = min(width, max_width)

            widths[field] = width

        def shorten(value, width):
            value = str(value)

            if max_width is None:
                return value

            if len(value) <= width:
                return value

            if width <= 3:
                return value[:width]

            return value[: width - 3] + "..."

        header = " | ".join(
            shorten(field, widths[field]).ljust(widths[field])
            for field in fieldnames
        )

        separator = "-+-".join(
            "-" * widths[field]
            for field in fieldnames
        )

        self.append(header)
        self.append(separator)

        for row in display_rows:
            line = " | ".join(
                shorten(row.get(field, ""), widths[field]).ljust(widths[field])
                for field in fieldnames
            )

            self.append(line)

    def block(self, title, content):
        """
        Log a larger text block.
        """

        self.subsection(title)
        self.append(str(content))


def log_step(
    logger,
    title,
    status="DONE",
    info=None,
    rows=None,
    fieldnames=None,
    detail_title="Details",
    max_width=LOG_SUMMARY_MAX_WIDTH,
):
    """
    Generic step logger.

    It prints:
        section title
        useful info
        optional detail table
    """

    logger.section(title, status=status)

    if info:
        logger.key_values(info)

    if rows is not None and fieldnames is not None:
        logger.subsection(detail_title)
        logger.rows(
            rows=rows,
            fieldnames=fieldnames,
            drop_empty_fields=True,
            max_width=max_width,
        )