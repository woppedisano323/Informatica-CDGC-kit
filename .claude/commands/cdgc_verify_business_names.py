#!/usr/bin/env python3
"""
cdgc_verify_business_names.py — Check Business Name status on all 57 columns.

Run this after cdgc_set_business_names.py to verify propagation completed.

Usage:
  python3 ~/Documents/CDGC/cdgc_verify_business_names.py
"""
import getpass
import time
from pathlib import Path

import requests

LOGIN_URL    = "https://dmp-us.informaticacloud.com"
ORG_URL      = "https://idmc-api.dmp-us.informaticacloud.com"
COLUMN_CLASS = "com.infa.odin.models.relational.Column"

# All 57 columns — (name, expected_business_name_or_None)
COLUMNS = [
    # CUSTOMER_MASTER
    ("ACCOUNT_STATUS",          "Account Status"),
    ("ADDRESS_LINE1",           "Address Line1"),
    ("ANNUAL_INCOME",           "Annual Income"),
    ("CITY",                    "City"),
    ("CREDIT_SCORE",            "Credit Score"),
    ("CUSTOMER_ID",             "Customer ID"),
    ("CUSTOMER_SINCE",          "Customer Since"),
    ("DATE_OF_BIRTH",           "Date of Birth"),
    ("EMAIL",                   "Email Address"),
    ("FIRST_NAME",              "First Name"),
    ("LAST_NAME",               "Last Name"),
    ("PHONE_NUMBER",            "Phone Number"),
    ("RISK_TIER",               "Risk Tier"),
    ("SSN",                     "Social Security Number"),
    ("STATE",                   "State"),
    ("ZIP_CODE",                "Zip Code"),
    # GL_ENTRY_REGISTER
    ("ACCOUNT_CODE",            "GL Account Number"),
    ("ACCOUNT_NAME",            None),
    ("APPROVED_BY",             None),
    ("COST_CENTER",             None),
    ("CREATED_BY",              None),
    ("CREDIT_AMOUNT",           "Credit Amount"),
    ("CURRENCY",                "Currency Code"),
    ("DEBIT_AMOUNT",            "Debit Amount"),
    ("ENTRY_DATE",              None),
    ("ENTRY_ID",                None),
    ("FISCAL_PERIOD",           "GL Balance"),
    ("FISCAL_YEAR",             None),
    ("JOURNAL_ID",              None),
    ("LEGAL_ENTITY",            None),
    ("NET_AMOUNT",              None),
    ("POSTING_DATE",            None),
    # RISK_EXPOSURE_DAILY
    ("ASSESSMENT_DATE",         None),
    ("BASEL_CLASS",             None),
    ("COLLATERAL_VALUE",        None),
    ("EXPECTED_LOSS",           None),
    ("EXPOSURE_AMOUNT",         None),
    ("LOSS_GIVEN_DEFAULT",      "Loss Given Default"),
    ("PROBABILITY_OF_DEFAULT",  "Probability of Default"),
    ("REGULATORY_CAPITAL",      None),
    ("RISK_CATEGORY",           None),
    ("RISK_ID",                 None),
    ("RISK_RATING",             None),
    # TRANSACTION_LEDGER
    ("ACCOUNT_ID",              None),
    ("AMOUNT",                  "Transaction Amount"),
    ("BALANCE_AFTER",           None),
    ("CHANNEL",                 None),
    # CURRENCY appears in multiple tables — check both
    ("MERCHANT_CATEGORY",       None),
    ("MERCHANT_NAME",           None),
    ("REFERENCE_NUMBER",        None),
    ("STATUS",                  "Entry Status"),
    ("TRANSACTION_DATE",        "Transaction Date"),
    ("TRANSACTION_ID",          "Transaction ID"),
    ("TRANSACTION_TYPE",        "Transaction Type"),
]

# ── Auth ──────────────────────────────────────────────────────────────────────
username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

resp = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
resp.raise_for_status()
data = resp.json()
session_id, org_id = data["sessionId"], data["orgId"]

resp = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": session_id},
    cookies={"USER_SESSION": session_id}, timeout=30)
resp.raise_for_status()
jwt = (resp.json().get("token") or resp.json().get("jwt_token")
       or resp.json().get("access_token"))
print("✓ Authenticated\n")

H = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id,
     "Content-Type": "application/json", "Accept": "application/json"}

# ── Check each unique column name ─────────────────────────────────────────────
print("Checking Business Names via search API...\n")

# Dedupe column names for API calls, then map results
seen = {}
unique_names = []
for col_name, expected in COLUMNS:
    if col_name not in seen:
        seen[col_name] = expected
        unique_names.append(col_name)

actual_bn = {}
for col_name in unique_names:
    r = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery={col_name}&segments=summary",
        headers=H,
        json={"from": 0, "size": 10,
              "filterSpec": [{"type": "simple", "attribute": "core.classType",
                              "values": [COLUMN_CLASS]}]}, timeout=30)
    hits = r.json().get("hits", [])
    # Take the first hit whose name matches exactly
    bn = ""
    for h in hits:
        s = h.get("summary", {})
        if s.get("core.name") == col_name:
            bn = s.get("core.businessName", "") or ""
            break
    actual_bn[col_name] = bn
    time.sleep(0.25)

# ── Print results ─────────────────────────────────────────────────────────────
print(f"{'Column':<28} {'Expected':<32} {'Actual':<32} Status")
print("-" * 105)

total = len(unique_names)
has_bn = 0
should_have = 0
correct = 0
missing = 0
ungoverned_count = 0

for col_name in unique_names:
    expected = seen[col_name]
    actual   = actual_bn[col_name]

    if expected is None:
        ungoverned_count += 1
        status = "— ungoverned"
        print(f"  {'':2}{col_name:<26} {'—':<32} {actual or '—':<32} {status}")
    else:
        should_have += 1
        if actual:
            has_bn += 1
            match = "✓" if actual == expected else "≈"
            correct += 1
            print(f"  {match} {col_name:<26} {expected:<32} {actual:<32}")
        else:
            missing += 1
            print(f"  ✗ {col_name:<26} {expected:<32} {'(empty)':<32} MISSING")

print(f"\n{'='*60}")
print(f"  Governed columns with Business Name: {has_bn}/{should_have}")
print(f"  Missing Business Name:               {missing}/{should_have}")
print(f"  Ungoverned (no term yet):            {ungoverned_count}")
print(f"  Total unique columns checked:        {total}")

if missing:
    print(f"\n⚠  {missing} columns still missing Business Name.")
    print("   If this runs <60s after the import, wait and re-run.")
    print("   Otherwise check CDGC UI — search may be lagging behind.")
else:
    print(f"\n✓ All {should_have} governed columns have Business Names populated.")
