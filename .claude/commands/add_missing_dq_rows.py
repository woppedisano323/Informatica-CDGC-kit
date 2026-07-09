#!/usr/bin/env python3
"""
add_missing_dq_rows.py

Adds FCBDQ-38, -39, -40 to 13_DQ_Rule_Template_PATCHED.xlsx for the 3 ICDQ
rules that had no template row:
  - ACCOUNT_STATUS_values_rule     → FCBDQ-38
  - RISK_TIER_values_rule          → FCBDQ-39
  - TRANSACTION_TYPE_values_rule   → FCBDQ-40
"""
import openpyxl
from pathlib import Path

PATCHED = Path("/Users/woppedisano/Downloads/CDGC_Import_FirstCapitalBank/13_DQ_Rule_Template_PATCHED.xlsx")

wb = openpyxl.load_workbook(PATCHED)
ws = wb.active

# Column order (confirmed from header row):
# 0  Reference ID
# 1  Name
# 2  Description
# 3  Criticality
# 4  Dimension
# 5  Enable Automation
# 6  Frequency
# 7  Input Port Name
# 8  Lifecycle
# 9  Measuring Method
# 10 Output Port Name
# 11 Technical Description
# 12 Technical Rule Reference
# 13 Target
# 14 Threshold
# 15 Primary Glossary
# 16 Secondary Glossary
# 17 Operation
# 18 Stakeholder: Governance Owner
# 19 Stakeholder: Governance Administrator

NEW_ROWS = [
    (
        "FCBDQ-38",
        "Account Status Valid Value",
        "Account status must be a valid value from the approved domain (e.g. ACTIVE, CLOSED, SUSPENDED, DORMANT)",
        "High", "Validity", "true", "Daily", "ACCOUNT_STATUS", "Published",
        "InformaticaCloudDataQuality", "DQ_RESULT",
        "Invalid account status values cause errors in portfolio reporting and regulatory filings",
        "9J4L90ztq5IkvsYjkqC2q9",   # ACCOUNT_STATUS_values_rule
        100, 0, "Account Status", None, "Create",
        "woppedisano@informatica.com", "woppedisano@informatica.com"
    ),
    (
        "FCBDQ-39",
        "Risk Tier Valid Value",
        "Risk tier must be a valid value from the approved domain (e.g. LOW, MEDIUM, HIGH, CRITICAL)",
        "High", "Validity", "true", "Daily", "RISK_TIER", "Published",
        "InformaticaCloudDataQuality", "DQ_RESULT",
        "Invalid risk tier values distort risk aggregation and capital reserve calculations",
        "96SizOoG8aDbVQric2t5a5",   # RISK_TIER_values_rule
        100, 0, "Risk Tier", None, "Create",
        "woppedisano@informatica.com", "woppedisano@informatica.com"
    ),
    (
        "FCBDQ-40",
        "Transaction Type Valid Value",
        "Transaction type must be a valid value from the approved domain (e.g. DEBIT, CREDIT, TRANSFER, FEE)",
        "High", "Validity", "true", "Daily", "TRANSACTION_TYPE", "Published",
        "InformaticaCloudDataQuality", "DQ_RESULT",
        "Invalid transaction type values break downstream GL reconciliation and fraud detection logic",
        "5P0UFNRLqtIe5n7pb5H6sZ",   # TRANSACTION_TYPE_values_rule
        100, 0, "Transaction Type", None, "Create",
        "woppedisano@informatica.com", "woppedisano@informatica.com"
    ),
]

for row_data in NEW_ROWS:
    ws.append(row_data)
    print(f"  ✓ Added {row_data[0]}  {row_data[1]}")

wb.save(PATCHED)
print(f"\n✓ Saved. Total rows: {ws.max_row - 1} rules")
