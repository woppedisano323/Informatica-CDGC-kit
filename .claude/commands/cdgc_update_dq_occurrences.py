#!/usr/bin/env python3
"""
cdgc_update_dq_occurrences.py

Wrapper that calls cdgc_create_dq_occurrences.py with --update flag.
Use this when DQ Rule Occurrences already exist in CDGC and you need
to modify them (e.g. after re-patching the DQ Rule Template with new
ICDQ rule IDs, or after a re-scan changes column paths).

Outputs: 15_DQ_Rule_Occurrence_UPDATE.xlsx

Usage:
  python3 cdgc_update_dq_occurrences.py

When to use Create vs Update:
  Create — occurrences do not exist in CDGC yet (first time setup)
  Update — occurrences already exist; you are modifying or re-linking them
"""
import runpy
import sys

sys.argv = [sys.argv[0], "--update"]

runpy.run_path(
    str(__file__.replace("cdgc_update_dq_occurrences.py", "cdgc_create_dq_occurrences.py")),
    run_name="__main__"
)
