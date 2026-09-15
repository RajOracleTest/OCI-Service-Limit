#!/usr/bin/env python3
"""Compare OCI service-limit CSV exports and write differing current limits."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


REQUIRED_COLUMNS = {
    "region",
    "service_name",
    "service_description",
    "limit_name",
    "scope_type",
    "availability_domain",
    "current_limit",
}

OUTPUT_COLUMNS = [
    "service_name",
    "service_description",
    "limit_name",
    "scope_type",
    "availability_domain",
    "source_region",
    "source_current_limit",
    "target_region",
    "target_current_limit",
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write OCI limits whose current_limit differs between two regional CSV files."
    )
    parser.add_argument("source_csv", type=Path, help="First regional service-limit CSV")
    parser.add_argument("target_csv", type=Path, help="Second regional service-limit CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("service_limit_current_limit_diff.csv"),
        help="Diff CSV path (default: service_limit_current_limit_diff.csv)",
    )
    return parser.parse_args()


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["service_name"].strip(),
        row["limit_name"].strip(),
        row["scope_type"].strip(),
        row["availability_domain"].strip(),
    )


def normalized_limit(value: str) -> str:
    """Compare numeric limits by value, while retaining non-numeric values safely."""
    cleaned = value.strip()
    try:
        return str(Decimal(cleaned).normalize())
    except (InvalidOperation, ValueError):
        return cleaned


def load_rows(path: Path) -> dict[tuple[str, str, str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        actual_columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - actual_columns
        if missing:
            raise ValueError(f"{path} is missing required column(s): {', '.join(sorted(missing))}")

        rows: dict[tuple[str, str, str, str], dict[str, str]] = {}
        for line_number, row in enumerate(reader, start=2):
            key = row_key(row)
            if key in rows:
                raise ValueError(
                    f"{path} has duplicate limit identity at line {line_number}: {key}"
                )
            rows[key] = row
    return rows


def main() -> int:
    args = parse_arguments()
    try:
        source_rows = load_rows(args.source_csv)
        target_rows = load_rows(args.target_csv)
    except (OSError, ValueError) as error:
        print(f"Input error: {error}")
        return 1

    differences: list[dict[str, str]] = []
    for key in sorted(source_rows.keys() & target_rows.keys()):
        source = source_rows[key]
        target = target_rows[key]
        if normalized_limit(source["current_limit"]) == normalized_limit(target["current_limit"]):
            continue

        differences.append(
            {
                "service_name": source["service_name"],
                "service_description": source["service_description"],
                "limit_name": source["limit_name"],
                "scope_type": source["scope_type"],
                "availability_domain": source["availability_domain"],
                "source_region": source["region"],
                "source_current_limit": source["current_limit"],
                "target_region": target["region"],
                "target_current_limit": target["current_limit"],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(differences)

    print(f"Compared {len(source_rows)} source limits with {len(target_rows)} target limits.")
    print(f"Found {len(differences)} current-limit difference(s).")
    print(f"Created: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
