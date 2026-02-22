#!/usr/bin/env python3
"""
Reads ~/Downloads/zelle_export_50.csv, looks up each Token in Scambus
to find its identifier UUID, and outputs a new CSV with the UUID prepended.
"""

import csv
import os
import time

from scambus_client import ScambusClient
from scambus_client.types import FilterCriteria

RATE_LIMIT = 4  # requests per second
MIN_INTERVAL = 1.0 / RATE_LIMIT

INPUT_PATH = os.path.expanduser("~/Downloads/zelle_export_50.csv")
OUTPUT_PATH = os.path.expanduser("~/Downloads/zelle_export_50_with_uuids.csv")
UNMATCHED_PATH = os.path.expanduser("~/Downloads/zelle_export_50_unmatched.csv")


def main():
    client = ScambusClient()
    errors = []
    last_request_time = 0.0

    with (
        open(INPUT_PATH, newline="") as infile,
        open(OUTPUT_PATH, "w", newline="") as outfile,
        open(UNMATCHED_PATH, "w", newline="") as unmatchedfile,
    ):
        reader = csv.DictReader(infile)
        assert reader.fieldnames is not None, "CSV has no header row"
        orig_fieldnames = list(reader.fieldnames)

        matched_writer = csv.DictWriter(outfile, fieldnames=["UUID"] + orig_fieldnames)
        matched_writer.writeheader()

        unmatched_writer = csv.DictWriter(unmatchedfile, fieldnames=orig_fieldnames)
        unmatched_writer.writeheader()

        matched_count = 0
        unmatched_count = 0

        for i, row in enumerate(reader):
            token = row["Token"].strip()
            if not token:
                unmatched_writer.writerow(row)
                unmatched_count += 1
                continue

            try:
                elapsed = time.monotonic() - last_request_time
                if elapsed < MIN_INTERVAL:
                    time.sleep(MIN_INTERVAL - elapsed)
                last_request_time = time.monotonic()
                result = client.search_identifiers(
                    query=token,
                    limit=1,
                    filter_criteria=FilterCriteria(
                        type="payment_token",
                        service="zelle",
                    ),
                )
                identifiers = result.get("data", [])
                uuid = identifiers[0].id if identifiers else ""
            except Exception as e:
                uuid = ""
                errors.append((i + 1, token, str(e)))

            if uuid:
                row["UUID"] = uuid
                matched_writer.writerow(row)
                matched_count += 1
                print(f"[{i+1}] {token} -> FOUND ({uuid})")
            else:
                unmatched_writer.writerow(row)
                unmatched_count += 1
                print(f"[{i+1}] {token} -> NOT FOUND")

    print(f"\nDone. {matched_count} matched, {unmatched_count} unmatched.")
    print(f"  Matched:   {OUTPUT_PATH}")
    print(f"  Unmatched: {UNMATCHED_PATH}")
    if errors:
        print(f"\n{len(errors)} lookup(s) failed (written to unmatched):")
        for lineno, token, err in errors:
            print(f"  row {lineno}: {token} — {err}")


if __name__ == "__main__":
    main()
