"""Small JSON/CSV writers for curated M5 session summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_json_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv_record(record: dict[str, Any], path: Path) -> None:
    """Write the scalar acceptance fields as one reproducible CSV row."""

    fields = {
        key: value
        for key, value in record.items()
        if value is None or isinstance(value, (str, int, float, bool))
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields))
        writer.writeheader()
        writer.writerow(fields)
