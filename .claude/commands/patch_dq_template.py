#!/usr/bin/env python3
"""
patch_dq_template.py

Applies exact ICDQ rule IDs to 13_DQ_Rule_Template.xlsx using a hardcoded
mapping built from semantic analysis of rule names.

Sets:
  - Technical Rule Reference = ICDQ artifact ID
  - Measuring Method = InformaticaCloudDataQuality

Rows with no ICDQ equivalent are left unchanged (TechnicalScript).
"""
import csv
import shutil
import openpyxl
from pathlib import Path

TEMPLATE = Path("/Users/woppedisano/Downloads/CDGC_Import_FirstCapitalBank/13_DQ_Rule_Template.xlsx")
CSV      = Path("/Users/woppedisano/Documents/CDGC/icdq_rules.csv")
OUTPUT   = TEMPLATE.parent / "13_DQ_Rule_Template_PATCHED.xlsx"

# ── Load ICDQ name → ID lookup ────────────────────────────────────────────────
icdq = {}
with open(CSV) as f:
    for row in csv.DictReader(f):
        icdq[row["Name"]] = row["ID"]

# ── Explicit mapping: template Reference ID → ICDQ rule name ─────────────────
# Built from semantic analysis. Rows not listed have no ICDQ equivalent
# and remain as TechnicalScript.
MAPPING = {
    "FCBDQ-1":  "SSN_presence_rule",
    "FCBDQ-2":  "SSN_pattern_rule",
    # FCBDQ-3  Credit Score Range 300 to 850  — no ICDQ credit_score rule
    # FCBDQ-4  Tax Residency Required          — no ICDQ tax rule
    "FCBDQ-5":  "TRANSACTION_AMOUNT_nonneg_rule",
    # FCBDQ-6  Currency Code ISO 4217          — no ICDQ currency_code rule
    "FCBDQ-7":  "AMOUNT_CURRENCY_CTR_FLAG_ctr_rule",
    "FCBDQ-8":  "JOURNAL_ID_DEBIT_AMOUNT_balance_rule",
    "FCBDQ-9":  "DEBIT_AMOUNT_CREDIT_AMOUNT_nonzero_rule",
    "FCBDQ-10": "DEBIT_AMOUNT_CREDIT_AMOUNT_gl_rule",
    "FCBDQ-11": "TRANSACTION_AMOUNT_presence_rule",
    "FCBDQ-12": "TRANSACTION_AMOUNT_positive_rule",
    "FCBDQ-13": "CHANNEL_values_rule",
    # FCBDQ-14 Transaction Velocity Non Negative — no ICDQ velocity rule
    "FCBDQ-15": "DEVICE_FINGERPRINT_presence_rule",
    "FCBDQ-16": "DATA_PARTITION_values_rule",
    # FCBDQ-17 Credit Score Valid Range          — no ICDQ credit_score rule
    "FCBDQ-18": "ANNUAL_INCOME_presence_rule",
    "FCBDQ-19": "ANNUAL_INCOME_positive_rule",
    "FCBDQ-20": "DEBT_TO_INCOME_RATIO_nonneg_rule",
    "FCBDQ-21": "KYC_VERIFIED_DATE_rule",
    "FCBDQ-22": "PEP_FLAG_SANCTIONS_FLAG_rule",
    "FCBDQ-23": "EMPLOYMENT_STATUS_values_rule",
    "FCBDQ-24": "INTEREST_RATE_range_rule",
    "FCBDQ-25": "LTV_RATIO_range_rule",
    "FCBDQ-26": "OUTSTANDING_BALANCE_nonneg_rule",
    "FCBDQ-27": "INTERNAL_RATING_presence_rule",
    "FCBDQ-28": "STRESS_SCENARIO_values_rule",
    "FCBDQ-29": "FILING_TYPE_presence_rule",
    "FCBDQ-30": "COMPLETENESS_SCORE_range_rule",
    "FCBDQ-31": "ERROR_COUNT_nonneg_rule",
    "FCBDQ-32": "FILED_ON_TIME_SUBMISSION_DATE_rule",
    "FCBDQ-33": "ACCEPTANCE_STATUS_values_rule",
    "FCBDQ-34": "FRAUD_PROBABILITY_range_rule",
    "FCBDQ-35": "DECISION_model_values_rule",
    "FCBDQ-36": "PD_SCORE_range_rule",
    "FCBDQ-37": "DECISION_credit_values_rule",
    "FCBDQ-38": "ACCOUNT_STATUS_values_rule",
    "FCBDQ-39": "RISK_TIER_values_rule",
    "FCBDQ-40": "TRANSACTION_TYPE_values_rule",
}

# ── Patch the workbook ────────────────────────────────────────────────────────
shutil.copy(TEMPLATE, OUTPUT)
wb = openpyxl.load_workbook(OUTPUT)
ws = wb.active

headers    = [cell.value for cell in ws[1]]
col_method = headers.index("Measuring Method") + 1
col_ref    = headers.index("Technical Rule Reference") + 1
col_op     = headers.index("Operation") + 1
col_out    = headers.index("Output Port Name") + 1

print(f"{'ID':<12} {'Template Name':<45} {'ICDQ Rule':<45} {'Ref ID'}")
print("─" * 130)

matched = 0
skipped = []
for row in ws.iter_rows(min_row=2):
    ref_id = row[0].value
    name   = row[1].value
    if not ref_id:
        continue

    # All rows already exist in CDGC — force Update
    ws.cell(row=row[0].row, column=col_op).value = "Update"

    icdq_name = MAPPING.get(ref_id)
    if icdq_name:
        rule_id = icdq.get(icdq_name)
        if rule_id:
            ws.cell(row=row[0].row, column=col_method).value = "InformaticaCloudDataQuality"
            ws.cell(row=row[0].row, column=col_ref).value    = rule_id
            ws.cell(row=row[0].row, column=col_out).value    = "Output"
            print(f"  {ref_id:<10} {name:<45} {icdq_name:<45} {rule_id}")
            matched += 1
        else:
            print(f"  {ref_id:<10} {name:<45} ⚠ '{icdq_name}' not in CSV — check name")
            skipped.append(ref_id)
    else:
        print(f"  {ref_id:<10} {name:<45} (no ICDQ equivalent — left as TechnicalScript)")
        skipped.append(ref_id)

wb.save(OUTPUT)
print(f"\n{'─' * 130}")
print(f"✓ Saved: {OUTPUT}")
print(f"  Matched: {matched}   Left as TechnicalScript: {len(skipped)}")
if skipped:
    print(f"  Skipped: {', '.join(skipped)}")
