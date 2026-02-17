#!/usr/bin/env python3

import csv
import sys
from pathlib import Path

def process_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Answer Explanation" not in reader.fieldnames:
            print(f"Skipping {path} (no 'Answer Explanation' column)")
            return

        fieldnames = reader.fieldnames
        rows = []

        for row in reader:
            # Remove extra columns stored under None
            row.pop(None, None)

            val = row.get("Answer Explanation")
            if val:
                val = val.replace("*\\n", "\n")
                val = val.replace("\\n", "\n")
                row["Answer Explanation"] = val

            rows.append(row)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"  # ignore any unexpected fields
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Processed {path}")

def handle_path(p: Path):
    if p.is_file() and p.suffix.lower() == ".csv":
        process_csv(p)
    elif p.is_dir():
        for csv_file in sorted(p.glob("*.csv")):
            process_csv(csv_file)
    else:
        print(f"Skipping {p} (not a csv file or directory)")

def main():
    if len(sys.argv) < 2:
        print("Usage: fix_csv_newlines.py <file.csv | directory> [...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        handle_path(Path(arg))

if __name__ == "__main__":
    main()
