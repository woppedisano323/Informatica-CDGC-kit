#!/usr/bin/env python3
"""
cdgc_govern_technical.py — Full technical governance pipeline

Phases:
  --phase 1   Link 18 known columns to their FCBBT- Business Terms
  --phase 2a  Analyze gap → generate CDGC_Gap_Review.xlsx for human review
  --phase 2b  Apply workbook approvals → import new terms via API + link all approved columns
  --phase 3   Set Business Names → fresh export → Automatic Assignment=Enabled → reimport → verify
  --all       Run phases 1 + 2a, then pause for human review before 2b

Flags:
  --company   Customer name (e.g. "First Capital Bank")
  --prefix    Asset prefix (default: FCB → new terms get FCBBT-N IDs)
  --email     Governance owner email for new term imports
  --workbook  Override workbook path (default: ~/Downloads/CDGC_Gap_Review.xlsx)

Usage:
  python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 1
  python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 2a --company "First Capital Bank"
  python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 2b --email you@example.com
  python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 3
  python3 ~/Documents/CDGC/cdgc_govern_technical.py --all --company "First Capital Bank"
"""
import argparse
import getpass
import re
import subprocess
import time
from pathlib import Path

import requests

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    raise SystemExit("pip3 install openpyxl")

# ── Config ────────────────────────────────────────────────────────────────────
LOGIN_URL    = "https://dmp-us.informaticacloud.com"
ORG_URL      = "https://idmc-api.dmp-us.informaticacloud.com"
COLUMN_CLASS = "com.infa.odin.models.relational.Column"
TERM_CLASS   = "com.infa.ccgf.models.governance.BusinessTerm"
SUBDOM_CLASS = "com.infa.ccgf.models.governance.Subdomain"
CONFIDENCE_THRESHOLD = 70

# Phase 1: 18 known column → term name mappings (resolved against live CDGC at runtime)
KNOWN_LINKS = {
    "CUSTOMER_ID":            "Customer ID",
    "SSN":                    "Social Security Number",
    "DATE_OF_BIRTH":          "Date of Birth",
    "EMAIL":                  "Email Address",
    "PHONE_NUMBER":           "Phone Number",
    "CREDIT_SCORE":           "Credit Score",
    "TRANSACTION_ID":         "Transaction ID",
    "AMOUNT":                 "Transaction Amount",
    "TRANSACTION_TYPE":       "Transaction Type",
    "TRANSACTION_DATE":       "Transaction Date",
    "CURRENCY":               "Currency Code",
    "ACCOUNT_CODE":           "GL Account Number",
    "FISCAL_PERIOD":          "GL Balance",
    "DEBIT_AMOUNT":           "Debit Amount",
    "CREDIT_AMOUNT":          "Credit Amount",
    "STATUS":                 "Entry Status",
    "PROBABILITY_OF_DEFAULT": "Probability of Default",
    "LOSS_GIVEN_DEFAULT":     "Loss Given Default",
}

# Phase 2a: skip these in gap analysis (already governed after Phase 1)
# IDs confirmed from live org export — do not use gap_analyzer's stale values
GOVERNED_COLUMNS = set(KNOWN_LINKS.keys())

# AI-drafted definitions for the 27 ungoverned columns
NEW_TERM_DRAFTS = {
    # CUSTOMER_MASTER
    "FIRST_NAME":        ("First Name",               "Customer legal first name as provided at onboarding",                                       "Customer Identity",    "Customer & KYC"),
    "LAST_NAME":         ("Last Name",                "Customer legal last name or family name",                                                   "Customer Identity",    "Customer & KYC"),
    "ADDRESS_LINE1":     ("Street Address",           "Primary street address line for the customer's residence or mailing address",               "Customer Identity",    "Customer & KYC"),
    "CITY":              ("City",                     "City of residence or mailing address for the customer",                                     "Customer Identity",    "Customer & KYC"),
    "STATE":             ("State",                    "US state abbreviation for the customer's address",                                          "Customer Identity",    "Customer & KYC"),
    "ZIP_CODE":          ("Zip Code",                 "US postal zip code for the customer's address",                                             "Customer Identity",    "Customer & KYC"),
    "ACCOUNT_STATUS":    ("Account Status",           "Current status of the customer account: ACTIVE, INACTIVE, SUSPENDED, CLOSED",              "Customer Identity",    "Customer & KYC"),
    "CUSTOMER_SINCE":    ("Customer Since Date",      "Date the customer relationship was first established with the institution",                 "Customer Identity",    "Customer & KYC"),
    "ANNUAL_INCOME":     ("Annual Income",            "Customer declared annual income in USD, used for credit and risk assessment",               "Customer Identity",    "Customer & KYC"),
    "RISK_TIER":         ("Customer Risk Tier",       "Internal risk classification assigned to the customer: LOW, MEDIUM, HIGH, VERY_HIGH",      "KYC & Compliance",     "Customer & KYC"),
    # TRANSACTION_LEDGER
    "ACCOUNT_ID":        ("Account ID",               "Unique identifier for the financial account associated with a transaction",                 "Payment Processing",   "Transactions"),
    "MERCHANT_NAME":     ("Merchant Name",            "Name of the merchant or payee for the transaction",                                        "Payment Processing",   "Transactions"),
    "MERCHANT_CATEGORY": ("Merchant Category",        "Merchant category classification used for spend analytics and reporting",                   "Payment Processing",   "Transactions"),
    "BALANCE_AFTER":     ("Balance After Transaction","Account balance remaining immediately after a transaction is applied",                      "Payment Processing",   "Transactions"),
    "CHANNEL":           ("Transaction Channel",      "Channel through which the transaction was initiated: ONLINE, BRANCH, ATM, MOBILE",         "Payment Processing",   "Transactions"),
    "REFERENCE_NUMBER":  ("Reference Number",         "External reference or confirmation number assigned to the transaction",                     "Payment Processing",   "Transactions"),
    # GL_ENTRY_REGISTER
    "ENTRY_ID":          ("GL Entry ID",              "Unique identifier for a general ledger journal entry",                                      "Accounting Entries",   "General Ledger"),
    "JOURNAL_ID":        ("Journal ID",               "Identifier for the journal batch containing one or more GL entries",                        "Accounting Entries",   "General Ledger"),
    "ENTRY_DATE":        ("Entry Date",               "Date on which the accounting entry was recorded",                                           "Accounting Entries",   "General Ledger"),
    "ACCOUNT_NAME":      ("Account Name",             "Descriptive name of the general ledger account from the chart of accounts",                "Accounting Entries",   "General Ledger"),
    "NET_AMOUNT":        ("Net Amount",               "Net monetary amount calculated as debit minus credit for a GL entry",                      "Accounting Entries",   "General Ledger"),
    "COST_CENTER":       ("Cost Center",              "Business unit cost center code used for financial reporting and allocation",                "Financial Close",      "General Ledger"),
    "LEGAL_ENTITY":      ("Legal Entity Code",        "Legal entity associated with the journal entry for consolidation reporting",                "Financial Close",      "General Ledger"),
    "FISCAL_YEAR":       ("Fiscal Year",              "Fiscal year in which the journal entry is recorded",                                       "Financial Close",      "General Ledger"),
    "CREATED_BY":        ("Created By",               "User who created the journal entry in the financial system",                               "Accounting Entries",   "General Ledger"),
    "APPROVED_BY":       ("Approved By",              "User who approved the journal entry before posting to the ledger",                         "Accounting Entries",   "General Ledger"),
    "POSTING_DATE":      ("Posting Date",             "Date on which the transaction was posted to the general ledger",                           "Accounting Entries",   "General Ledger"),
    # RISK_EXPOSURE_DAILY
    "RISK_ID":           ("Risk Assessment ID",       "Unique identifier for a risk exposure assessment record",                                   "Credit Risk",          "Risk & Regulatory"),
    "ASSESSMENT_DATE":   ("Assessment Date",          "Date on which the risk exposure assessment was performed",                                  "Credit Risk",          "Risk & Regulatory"),
    "RISK_CATEGORY":     ("Risk Category",            "Type of risk: CREDIT, MARKET, OPERATIONAL, LIQUIDITY, REGULATORY",                        "Credit Risk",          "Risk & Regulatory"),
    "EXPOSURE_AMOUNT":   ("Exposure Amount",          "Total monetary exposure amount in USD for the risk assessment",                             "Credit Risk",          "Risk & Regulatory"),
    "EXPECTED_LOSS":     ("Expected Loss",            "Calculated expected loss: exposure × probability of default × loss given default",         "Credit Risk",          "Risk & Regulatory"),
    "RISK_RATING":       ("Risk Rating",              "Internal credit risk rating assigned to the obligor: AAA through CCC",                     "Credit Risk",          "Risk & Regulatory"),
    "COLLATERAL_VALUE":  ("Collateral Value",         "Estimated market value of collateral securing the exposure",                               "Credit Risk",          "Risk & Regulatory"),
    "REGULATORY_CAPITAL":("Regulatory Capital",       "Required regulatory capital allocation under Basel III rules",                             "Regulatory Reporting", "Risk & Regulatory"),
    "BASEL_CLASS":       ("Basel Asset Class",        "Basel III asset class classification for capital adequacy calculation",                    "Regulatory Reporting", "Risk & Regulatory"),
}

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--phase",    choices=["1","2a","2b","3"], help="Run a specific phase")
parser.add_argument("--all",      action="store_true",         help="Run phases 1 + 2a, then pause for review")
parser.add_argument("--company",  default="First Capital Bank",help="Customer name")
parser.add_argument("--prefix",   default="FCB",               help="Asset prefix (e.g. FCB → FCBBT-N)")
parser.add_argument("--email",    default="",                  help="Governance owner email for new terms")
parser.add_argument("--workbook", default="",                  help="Override gap review workbook path")
args = parser.parse_args()

if not args.phase and not args.all:
    parser.print_help()
    raise SystemExit(0)

slug     = args.company.strip().replace(" ", "_")
WB_PATH  = Path(args.workbook) if args.workbook else Path.home() / "Downloads" / f"CDGC_Gap_Review_{slug}.xlsx"
IMP_PATH = WB_PATH.parent / f"CDGC_New_Terms_{slug}.xlsx"
EXP_PATH = Path.home() / "Downloads" / f"CDGC_Columns_Export_{slug}.xlsx"

# ── Auth ──────────────────────────────────────────────────────────────────────
username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

resp = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
resp.raise_for_status()
session_id = resp.json()["sessionId"]
org_id     = resp.json()["orgId"]

resp = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": session_id},
    cookies={"USER_SESSION": session_id}, timeout=30)
resp.raise_for_status()
jwt = (resp.json().get("token") or resp.json().get("jwt_token")
       or resp.json().get("access_token"))
print("✓ Authenticated\n")

H  = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id,
      "Content-Type": "application/json", "Accept": "application/json"}
HD = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id}

# ── API helpers ───────────────────────────────────────────────────────────────
def fetch_all(class_type, segments="summary"):
    results, offset = [], 0
    while True:
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments={segments}",
            headers=H,
            json={"from": offset, "size": 100,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                  "values": [class_type]}]}, timeout=30)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        results.extend(hits)
        if len(hits) < 100:
            break
        offset += 100
        time.sleep(0.2)
    return results


def patch_glossary(col_int_id, bt_ext_id):
    url  = f"{ORG_URL}/data360/content/v1/assets/{col_int_id}?scheme=internal"
    body = [{"operation": "add", "segment": "glossary",
             "items": [{"core.externalId": bt_ext_id}]}]
    r = requests.patch(url, headers=H, json=body, timeout=90)
    return r.status_code, r.text

_col_uuid_cache = {}

def resolve_col_uuid(table_name, col_name):
    """Resolve column UUID live from API using table+column name. Caches results."""
    key = f"{table_name}.{col_name}"
    if key in _col_uuid_cache:
        return _col_uuid_cache[key]
    r = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
        headers=H,
        json={"from": 0, "size": 50,
              "filterSpec": [{"type": "simple", "attribute": "core.classType",
                              "values": ["com.infa.ldm.relational.Column"]}],
              "query": col_name}, timeout=30)
    if r.status_code != 200:
        return None
    for hit in r.json().get("hits", []):
        summ = hit.get("summary") or {}
        name = summ.get("core.name", "")
        parent = summ.get("core.parent", {})
        parent_name = parent.get("core.name", "") if isinstance(parent, dict) else ""
        if name.upper() == col_name.upper() and table_name.upper() in parent_name.upper():
            uuid = summ.get("core.identity") or hit.get("core.identity", "")
            if uuid:
                _col_uuid_cache[key] = uuid
                return uuid
    return None


def poll_job(job_id, label="job"):
    url      = f"{ORG_URL}/data360/observable/v1/jobs/{job_id}"
    terminal = {"COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED"}
    for attempt in range(40):
        time.sleep(4)
        rp = requests.get(url, headers=H, timeout=30)
        status = rp.json().get("status", rp.json().get("jobStatus", ""))
        print(f"  [{attempt+1}] {status}")
        if status in terminal:
            details = rp.json().get("details") or rp.json().get("message") or ""
            if details:
                print(f"  details: {str(details)[:300]}")
            return status
    print(f"  Timed out waiting for {label}")
    return "TIMEOUT"


def import_xlsx(path, label="import"):
    print(f"Submitting {label}...")
    with open(path, "rb") as f:
        files = {
            "file": (path.name, f,
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "config": (None, '{"validationPolicy":"CONTINUE_ON_ERROR_WARNING"}',
                       "application/json"),
        }
        r = requests.post(f"{ORG_URL}/data360/content/import/v1/assets",
                          headers=HD, files=files, timeout=60)
    print(f"  HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:400]}")
        return None
    job_id = r.json().get("jobId") or r.json().get("id")
    print(f"  jobId: {job_id}")
    return job_id


# ── Excel styles ──────────────────────────────────────────────────────────────
HDR_FILL  = PatternFill("solid", fgColor="1B2A4A")
HDR_FONT  = Font(color="FFFFFF", bold=True, size=11)
YES_FILL  = PatternFill("solid", fgColor="E8F5E9")
NEW_FILL  = PatternFill("solid", fgColor="E3F2FD")
DONE_FILL = PatternFill("solid", fgColor="F1F8E9")
WARN_FILL = PatternFill("solid", fgColor="FFF8E1")
YES_FONT  = Font(color="2E7D32", bold=True)
BLUE_FONT = Font(color="1565C0", bold=True)
THIN      = Side(style="thin", color="DDE1E8")
BORDER    = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def style_header(ws, cols):
    ws.row_dimensions[1].height = 22
    for i, (label, width) in enumerate(cols, 1):
        c = ws.cell(1, i, label)
        c.font = HDR_FONT; c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = width

def write_row(ws, rn, values, fill=None, col1_font=None):
    for i, val in enumerate(values, 1):
        c = ws.cell(rn, i, val)
        c.border = BORDER
        c.alignment = Alignment(vertical="center", wrap_text=(i == len(values) - 1))
        if fill:
            c.fill = fill
    if col1_font:
        ws.cell(rn, 1).font = col1_font
    ws.row_dimensions[rn].height = 18

def inst_row(ws, text, ncols):
    ws.insert_rows(2)
    c = ws.cell(2, 1, text)
    c.font = Font(color="1565C0", italic=True, size=10)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 18
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)

# ── Fuzzy matcher ─────────────────────────────────────────────────────────────
NOISE = {"of","the","a","an","and","or","for","in","on","at","to","is","as",
         "by","be","its","per","from","with","after","before"}

def tokens(s):
    return set(w.lower() for w in re.split(r'[_\s]+', s) if w)

def fuzzy_score(col_name, term_name, term_desc=""):
    ct = tokens(col_name)
    tt = tokens(term_name)
    if not ct or not tt:
        return 0
    if ct == tt:
        return 95
    if ct.issubset(tt):
        return 85
    if tt.issubset(ct):
        return 80
    overlap = ct & tt
    meaningful = overlap - NOISE
    if not meaningful:
        return 0
    jaccard = len(overlap) / len(ct | tt)
    desc_boost = 0
    if term_desc:
        dt = tokens(term_desc)
        if len(ct & dt - NOISE) >= len(ct - NOISE):
            desc_boost = 15
        elif ct & dt - NOISE:
            desc_boost = 8
    return min(100, int(jaccard * 75) + desc_boost)

def best_match(col_name, terms):
    best = None
    for t in terms:
        s = fuzzy_score(col_name, t["name"], t.get("description", ""))
        if s >= CONFIDENCE_THRESHOLD:
            if best is None or s > best[2]:
                best = (t["ext_id"], t["name"], s)
    return best


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Link 18 known columns to their Business Terms
# ══════════════════════════════════════════════════════════════════════════════
def run_phase_1():
    print("=" * 60)
    print("PHASE 1 — Link known columns to Business Terms")
    print("=" * 60)

    print("\nFetching Business Terms from CDGC...")
    term_hits = fetch_all(TERM_CLASS)
    term_lookup = {}
    for h in term_hits:
        s      = h.get("summary") or {}
        name   = s.get("core.name", "")
        ext_id = h.get("core.externalId") or s.get("core.externalId", "")
        if name and ext_id:
            term_lookup[name.lower()] = ext_id
    print(f"  {len(term_lookup)} terms found")

    # Resolve column → ext_id
    col_to_ext = {}
    for col_name, term_name in KNOWN_LINKS.items():
        ext_id = term_lookup.get(term_name.lower())
        if ext_id:
            col_to_ext[col_name] = ext_id
        else:
            print(f"  ⚠ Term not found: {term_name!r} (for column {col_name})")
    print(f"  {len(col_to_ext)}/{len(KNOWN_LINKS)} columns resolved\n")

    print("Fetching scanned columns from CDGC...")
    col_hits = fetch_all(COLUMN_CLASS)
    col_map = {}
    for h in col_hits:
        s      = h.get("summary") or {}
        name   = s.get("core.name", "")
        int_id = h.get("core.identity", "")
        if name and int_id:
            col_map[name.upper()] = int_id
    print(f"  {len(col_map)} columns found\n")

    print("Linking columns → Business Terms...")
    ok = fail = skipped = 0
    for col_name, bt_ext_id in col_to_ext.items():
        col_id = col_map.get(col_name)
        if not col_id:
            print(f"  — {col_name}: not in scan")
            skipped += 1
            continue
        status, body = patch_glossary(col_id, bt_ext_id)
        already = (status == 500 and bt_ext_id in body)
        if status in (200, 204) or already:
            tag = " (already linked)" if already else ""
            print(f"  ✓ {col_name} → {bt_ext_id}{tag}")
            ok += 1
        else:
            print(f"  ✗ {col_name} → {bt_ext_id}  [{status}] {body[:100]}")
            fail += 1
        time.sleep(0.3)

    print(f"\n  Linked: {ok}  |  Failed: {fail}  |  Not in scan: {skipped}")
    print(f"\n✓ Phase 1 complete.\n")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2a — Analyze gap, generate review workbook
# ══════════════════════════════════════════════════════════════════════════════
def run_phase_2a():
    print("=" * 60)
    print("PHASE 2a — Gap analysis → review workbook")
    print("=" * 60)

    print("\nFetching scanned columns...")
    col_hits = fetch_all(COLUMN_CLASS)
    print(f"  {len(col_hits)} columns")

    print("Fetching Business Terms...")
    term_hits = fetch_all(TERM_CLASS)
    terms = []
    for h in term_hits:
        s      = h.get("summary") or {}
        ext_id = h.get("core.externalId") or s.get("core.externalId", "")
        name   = s.get("core.name", "")
        desc   = s.get("core.description", "")
        # Skip system-generated BT- terms from Glossary Association
        if ext_id and name and not ext_id.startswith("BT-"):
            terms.append({"ext_id": ext_id, "name": name, "description": desc})
    print(f"  {len(terms)} customer-authored terms")

    print("Fetching Subdomains...")
    subdom_hits = fetch_all(SUBDOM_CLASS)
    subdom_lookup = {}
    for h in subdom_hits:
        s      = h.get("summary") or {}
        ext_id = h.get("core.externalId") or s.get("core.externalId", "")
        name   = s.get("core.name", "")
        if ext_id and name:
            subdom_lookup[name] = ext_id
    print(f"  {len(subdom_lookup)} subdomains\n")

    # Build column records
    columns = []
    for h in col_hits:
        s      = h.get("summary") or {}
        name   = s.get("core.name", "")
        loc    = s.get("core.location", "")
        parts  = loc.rstrip("/").split("/")
        table  = parts[-2] if len(parts) >= 2 else ""
        int_id = h.get("core.identity", "")
        columns.append({"name": name, "table": table, "id": int_id})

    # Categorize: already governed | suggest link | suggest new term
    already_governed, suggest_link, suggest_new = [], [], []

    for col in sorted(columns, key=lambda c: (c["table"], c["name"])):
        upper = col["name"].upper()
        if upper in GOVERNED_COLUMNS:
            term_name = KNOWN_LINKS[upper]
            ext_id    = next((t["ext_id"] for t in terms
                              if t["name"].lower() == term_name.lower()), "?")
            already_governed.append({**col, "term_ext": ext_id, "term_name": term_name})
        else:
            match = best_match(col["name"], terms)
            if match:
                suggest_link.append({**col, "term_ext": match[0],
                                     "term_name": match[1], "confidence": match[2]})
            else:
                draft = NEW_TERM_DRAFTS.get(upper)
                if draft:
                    term_name, term_desc, subdomain, domain = draft
                else:
                    term_name = col["name"].replace("_", " ").title()
                    term_desc = f"[Edit: description for {term_name}]"
                    subdomain, domain = "", "Customer & KYC"
                suggest_new.append({**col,
                                    "draft_name": term_name,
                                    "draft_desc": term_desc,
                                    "subdomain":  subdomain,
                                    "domain":     domain})

    print(f"Results:")
    print(f"  Already governed : {len(already_governed)}")
    print(f"  Suggested links  : {len(suggest_link)}")
    print(f"  Suggested new    : {len(suggest_new)}")
    print()

    # ── Build workbook ─────────────────────────────────────────────────────────
    wb = Workbook()

    # Tab 1: Suggested Links
    ws1 = wb.active
    ws1.title = "Suggested Links"
    ws1.freeze_panes = "A3"
    COLS1 = [("APPROVE",14),("Table",22),("Column Name",22),("Suggested Business Term",28),
             ("Confidence",12),("Term Description",42),("Term ext_id",14)]
    style_header(ws1, COLS1)
    inst_row(ws1, "→ Set APPROVE to YES for each match you accept, then run Phase 2b.", len(COLS1))
    for row in suggest_link:
        desc = next((t["description"] for t in terms if t["ext_id"] == row["term_ext"]), "")
        fill = YES_FILL if row["confidence"] >= 85 else WARN_FILL
        write_row(ws1, ws1.max_row+1,
                  ["", row["table"], row["name"], row["term_name"],
                   f"{row['confidence']}%", desc, row["term_ext"]],
                  fill=fill, col1_font=YES_FONT)
    if not suggest_link:
        ws1.cell(ws1.max_row+1, 1, "No suggested links — all ungoverned columns need new terms (see Tab 2)")

    # Tab 2: Suggested New Terms
    ws2 = wb.create_sheet("Suggested New Terms")
    ws2.freeze_panes = "A3"
    COLS2 = [("APPROVE",14),("Table",22),("Column Name",22),("Business Term Name",28),
             ("Description",52),("Subdomain",28),("Domain",22)]
    style_header(ws2, COLS2)
    inst_row(ws2, "→ Review/edit each row. Set APPROVE=YES to accept. Run Phase 2b when done.", len(COLS2))
    for row in suggest_new:
        write_row(ws2, ws2.max_row+1,
                  ["", row["table"], row["name"], row["draft_name"],
                   row["draft_desc"], row["subdomain"], row["domain"]],
                  fill=NEW_FILL, col1_font=BLUE_FONT)

    # Tab 3: Already Governed
    ws3 = wb.create_sheet("Already Governed")
    ws3.freeze_panes = "A2"
    COLS3 = [("Table",22),("Column Name",22),("Business Term",28),("Term ext_id",14)]
    style_header(ws3, COLS3)
    for row in already_governed:
        write_row(ws3, ws3.max_row+1,
                  [row["table"], row["name"], row["term_name"], row["term_ext"]],
                  fill=DONE_FILL)

    wb.save(WB_PATH)
    subprocess.Popen(["open", str(WB_PATH)])
    print(f"✓ Workbook written and opened: {WB_PATH}")
    print(f"""
{'═'*60}
HUMAN REVIEW REQUIRED
{'═'*60}

This workbook is the governance decision record for this
engagement. A data steward reviews and approves here before
anything is written to CDGC.

FILE: {WB_PATH.name}

─── TAB 1: Suggested Links ───────────────────────────────
  These ungoverned columns were fuzzy-matched to Business
  Terms that already exist in CDGC.

  For each row:
    • Review the suggested term name and description
    • If the match is correct → type YES in the APPROVE column
    • If wrong → leave APPROVE blank (row will be skipped)

  Green rows = high confidence (≥85%). Yellow = review carefully.

─── TAB 2: Suggested New Terms ───────────────────────────
  These ungoverned columns have no existing term to link to.
  AI has drafted a Business Term name and description for each.

  For each row:
    • Edit the Term Name or Description if needed
    • Verify the Subdomain and Domain assignment
    • If acceptable → type YES in the APPROVE column
    • If not ready → leave APPROVE blank (row will be skipped)

  Approved rows will become NEW Business Terms in CDGC with
  sequential FCBBT-N Reference IDs.

─── TAB 3: Already Governed ──────────────────────────────
  Reference only — these columns are already linked to
  Business Terms from Phase 1. No action needed.

─── WHEN DONE ────────────────────────────────────────────
  1. Save the workbook (Cmd+S)
  2. Run Phase 2b to apply all approvals:

     python3 ~/Documents/CDGC/cdgc_govern_technical.py \\
       --phase 2b --email your@email.com

  Phase 2b will:
    • Link Tab 1 approved columns to existing terms (PATCH)
    • Create Tab 2 approved terms in CDGC via API
    • Link those new columns to their new terms (PATCH)
    • Then run Phase 3 to propagate Business Names

{'═'*60}
""")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2b — Apply approvals: import new terms via API + link all columns
# ══════════════════════════════════════════════════════════════════════════════
def run_phase_2b():
    print("=" * 60)
    print("PHASE 2b — Apply approvals")
    print("=" * 60)

    if not WB_PATH.exists():
        raise SystemExit(f"ERROR: Workbook not found: {WB_PATH}\nRun --phase 2a first and complete human review before running 2b.")

    wb = load_workbook(WB_PATH)

    # Fetch all columns once — keyed by name, same pattern as Phase 1
    print("\nFetching scanned columns from CDGC...")
    col_hits = fetch_all(COLUMN_CLASS)
    col_map = {}
    for h in col_hits:
        s      = h.get("summary") or {}
        name   = s.get("core.name", "")
        int_id = h.get("core.identity", "")
        if name and int_id:
            col_map[name.upper()] = int_id
    print(f"  {len(col_map)} columns found")

    # ── Step A: Link Tab 1 approved rows to existing terms ─────────────────────
    ok1 = fail1 = skip1 = 0
    if "Suggested Links" in wb.sheetnames:
        ws1  = wb["Suggested Links"]
        hdrs = [c.value for c in ws1[1]]
        idx  = {h: i for i, h in enumerate(hdrs)}
        print(f"\nStep A — Linking Tab 1 approved rows to existing terms...")
        for row in ws1.iter_rows(min_row=3, values_only=True):
            approved = str(row[idx.get("APPROVE", 0)] or "").strip().upper() == "YES"
            if not approved:
                skip1 += 1
                continue
            term_ext = row[idx["Term ext_id"]]
            col_name = row[idx["Column Name"]]
            table    = row[idx["Table"]]
            if not term_ext:
                skip1 += 1
                continue
            col_id = col_map.get(col_name.upper())
            if not col_id:
                print(f"  ✗ {table}.{col_name} — not found in scan")
                fail1 += 1
                continue
            status, body = patch_glossary(col_id, term_ext)
            already = status == 500 and term_ext in body
            if status in (200, 204) or already:
                tag = " (already linked)" if already else ""
                print(f"  ✓ {table}.{col_name} → {term_ext}{tag}")
                ok1 += 1
            else:
                print(f"  ✗ {table}.{col_name}  [{status}] {body[:80]}")
                fail1 += 1
            time.sleep(0.3)
        print(f"  Done: {ok1} linked, {fail1} failed, {skip1} skipped")

    # ── Step B: Import new Business Terms via API ──────────────────────────────
    approved_new = []
    if "Suggested New Terms" in wb.sheetnames:
        ws2  = wb["Suggested New Terms"]
        hdrs = [c.value for c in ws2[1]]
        idx2 = {h: i for i, h in enumerate(hdrs)}
        for row in ws2.iter_rows(min_row=3, values_only=True):
            approved = str(row[idx2.get("APPROVE", 0)] or "").strip().upper() == "YES"
            if not approved:
                continue
            approved_new.append({
                "col_name":  row[idx2["Column Name"]],
                "table":     row[idx2["Table"]],
                "term_name": row[idx2["Business Term Name"]],
                "term_desc": row[idx2["Description"]],
                "subdomain": row[idx2["Subdomain"]],
                "domain":    row[idx2["Domain"]],
            })

    if not approved_new:
        print(f"\nNo approved new terms in Tab 2 — skipping import.")
    else:
        # Prompt for email if needed
        gov_email = args.email.strip()
        if not gov_email:
            gov_email = input("\nGovernance owner email for new terms: ").strip()

        print(f"\nStep B — Importing {len(set(r['term_name'] for r in approved_new))} new Business Terms via API...")

        # Find next available Reference ID number
        print("  Finding next available Reference ID...")
        all_terms = fetch_all(TERM_CLASS)
        prefix_bt = f"{args.prefix}BT-"
        max_n = 0
        for h in all_terms:
            s      = h.get("summary") or {}
            ext_id = h.get("core.externalId") or s.get("core.externalId", "")
            if ext_id.startswith(prefix_bt):
                try:
                    n = int(ext_id[len(prefix_bt):])
                    max_n = max(max_n, n)
                except ValueError:
                    pass
        next_n = max_n + 1
        print(f"  Highest existing ID: {prefix_bt}{max_n} → new terms start at {prefix_bt}{next_n}")

        # Fetch subdomains for parent reference
        subdom_hits = fetch_all(SUBDOM_CLASS)
        subdom_lookup = {}
        for h in subdom_hits:
            s      = h.get("summary") or {}
            ext_id = h.get("core.externalId") or s.get("core.externalId", "")
            name   = s.get("core.name", "")
            if ext_id and name:
                subdom_lookup[name] = ext_id

        # Build lookup of existing term names → ext_id to skip duplicates
        existing_term_map = {}
        for h in all_terms:
            s      = h.get("summary") or {}
            ext_id = h.get("core.externalId") or s.get("core.externalId", "")
            name   = s.get("core.name", "")
            if name and ext_id:
                existing_term_map[name] = ext_id

        # Deduplicate by term name — skip any that already exist in CDGC
        seen_terms = {}
        already_existing = {}
        for row in approved_new:
            tname = row["term_name"]
            if tname in existing_term_map:
                already_existing[tname] = existing_term_map[tname]
            elif tname not in seen_terms:
                seen_terms[tname] = row

        if already_existing:
            print(f"  Skipping {len(already_existing)} term(s) already in CDGC — will link directly")

        # Build import workbook
        imp_wb = Workbook()
        ws_imp = imp_wb.active
        ws_imp.title = "Business Term"

        IMP_COLS = [
            ("Reference ID",16),("Name",30),("Description",55),
            ("Alias Names",20),("Business Logic",20),("Critical Data Element",22),
            ("Examples",20),("Format Type",14),("Format Description",20),
            ("Lifecycle",14),("Security Level",16),("Classifications",20),
            ("Reference Data",20),("Operation",12),
            ("Parent: Subdomain",35),("Parent: Business Term",20),
            ("Parent: Metric",20),("Parent: Domain",20),
            ("Stakeholder: Governance Owner",35),
            ("Stakeholder: Governance Administrator",35),
        ]
        style_header(ws_imp, IMP_COLS)

        # Track Reference IDs for later column linking — pre-populate with already-existing terms
        term_ref_map = dict(already_existing)  # term_name → ext_id
        for i, (name, row) in enumerate(seen_terms.items(), 0):
            ref_id      = f"{prefix_bt}{next_n + i}"
            subdom_name = row["subdomain"] or ""
            subdom_ext  = subdom_lookup.get(subdom_name, "")
            parent_ref  = f"{subdom_name} | {subdom_ext}" if subdom_ext else subdom_name
            term_ref_map[name] = ref_id

            write_row(ws_imp, ws_imp.max_row+1, [
                ref_id, name, row["term_desc"],
                "", "", "false", "", "Text", "", "Published", "Internal",
                "", "", "Create",
                parent_ref, "", "", "",
                gov_email, gov_email,
            ], fill=NEW_FILL)

        imp_wb.save(IMP_PATH)
        print(f"  Saved import file: {IMP_PATH} ({len(seen_terms)} terms)")

        job_id = import_xlsx(IMP_PATH, "new Business Terms")
        if job_id:
            print("  Polling...")
            status = poll_job(job_id, "Business Term import")
            print(f"  Import status: {status}")
        else:
            raise SystemExit("Import failed — check output above.")

        # Wait for indexing before linking
        print("  Waiting 15s for indexing...")
        time.sleep(15)

        # ── Step C: Link approved Tab 2 columns to the newly imported terms ───────
        print(f"\nStep C — Linking {len(approved_new)} column(s) to new terms...")
        ok2 = fail2 = 0
        for row in approved_new:
            col_name  = row["col_name"]
            table     = row["table"]
            term_name = row["term_name"]
            ext_id    = term_ref_map.get(term_name)

            if not ext_id:
                print(f"  ✗ {table}.{col_name} — no ref_id for {term_name!r}")
                fail2 += 1
                continue

            col_id = col_map.get(col_name.upper())
            if not col_id:
                print(f"  ✗ {table}.{col_name} — not found in scan")
                fail2 += 1
                continue

            status, body = patch_glossary(col_id, ext_id)
            already = status == 500 and ext_id in body
            if status in (200, 204) or already:
                tag = " (already linked)" if already else ""
                print(f"  ✓ {table}.{col_name} → {term_name} ({ext_id}){tag}")
                ok2 += 1
            else:
                print(f"  ✗ {table}.{col_name} → {ext_id}  [{status}] {body[:80]}")
                fail2 += 1
            time.sleep(0.3)

        print(f"  Done: {ok2} linked, {fail2} failed")

    print(f"\n✓ Phase 2b complete.\n")
    print("Next step:")
    print("  python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 3")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Set Business Names via fresh export → Automatic Assignment → reimport
# ══════════════════════════════════════════════════════════════════════════════
def run_phase_3():
    print("=" * 60)
    print("PHASE 3 — Set Business Names on all governed columns")
    print("=" * 60)

    # ── Step A: Fresh export ───────────────────────────────────────────────────
    print("\nStep A — Exporting all column assets (fresh)...")
    export_url = (
        f"{ORG_URL}/data360/search/export/v1/assets"
        f"?knowledgeQuery=*"
        f"&segments=summary,glossary,selfAttributes"
        f"&fileName=CDGC_Columns_Export"
        f"&fileType=EXCEL"
        f"&summaryViews=Technical"
    )
    r = requests.post(export_url, headers=H,
                      json={"from": 0, "size": 200,
                            "filterSpec": [{"type": "simple",
                                            "attribute": "core.classType",
                                            "values": [COLUMN_CLASS]}]},
                      timeout=60)
    print(f"  HTTP {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:400]}")
        raise SystemExit(1)

    job_data = r.json()
    tracking = job_data.get("trackingURI", "")
    output   = job_data.get("outputURI", "")
    print(f"  jobId: {job_data.get('jobId')}  — polling...")

    if tracking:
        poll_url = f"{ORG_URL}{tracking}" if not tracking.startswith("http") else tracking
        for attempt in range(30):
            time.sleep(4)
            rp = requests.get(poll_url, headers=H, timeout=30)
            status = rp.json().get("status", rp.json().get("jobStatus", ""))
            print(f"  [{attempt+1}] {status}")
            if status in ("COMPLETED", "SUCCESS", "FAILED", "ERROR"):
                if not output:
                    output = (rp.json().get("outputURI", "") or
                              rp.json().get("outputProperties", {}).get("files", {}).get("Export_File", ""))
                break

    if not output:
        raise SystemExit("No outputURI from export job — cannot continue.")

    dl_url = f"{ORG_URL}{output}" if not output.startswith("http") else output
    rd = requests.get(dl_url, headers=H, timeout=60)
    print(f"  Download HTTP {rd.status_code}")
    if rd.status_code != 200:
        raise SystemExit(f"Download failed: {rd.text[:200]}")
    EXP_PATH.write_bytes(rd.content)
    print(f"  Saved: {EXP_PATH}  ({len(rd.content):,} bytes)")

    # ── Step B: Set Automatic Assignment = Enabled on all rows with a term ─────
    print("\nStep B — Setting Automatic Assignment = Enabled...")
    wb_exp = load_workbook(EXP_PATH)
    ws_exp = wb_exp["Technical Data element"]
    hdrs   = [c.value for c in ws_exp[1]]
    idx    = {h: i for i, h in enumerate(hdrs)}
    auto_i    = idx["Automatic Assignment"]
    accepted_i = idx["Glossaries: Accepted"]
    name_i    = idx["Name"]
    bn_i      = idx["Business Name"]

    modified = 0
    rows_info = []
    for row in ws_exp.iter_rows(min_row=2):
        accepted = row[accepted_i].value or ""
        if accepted:
            row[auto_i].value = "Enabled"
            modified += 1
            rows_info.append((row[name_i].value, accepted, row[bn_i].value or ""))

    print(f"  {modified} rows set to Enabled  |  {ws_exp.max_row-1-modified} rows skipped (no term)")

    # Save modified workbook (Technical Data element sheet only)
    SET_BN_PATH = EXP_PATH.parent / f"CDGC_Set_BusinessNames_{slug}.xlsx"
    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = "Technical Data element"
    for row in ws_exp.iter_rows(values_only=True):
        ws_out.append(list(row))
    wb_out.save(SET_BN_PATH)
    print(f"  Saved: {SET_BN_PATH}")

    # ── Step C: Reimport ───────────────────────────────────────────────────────
    print("\nStep C — Reimporting with Automatic Assignment = Enabled...")
    job_id = import_xlsx(SET_BN_PATH, "Business Name reimport")
    if job_id:
        print("  Polling...")
        status = poll_job(job_id, "reimport")
        print(f"  Import status: {status}")
    else:
        raise SystemExit("Reimport failed.")

    # ── Step D: Verify ─────────────────────────────────────────────────────────
    print("\nStep D — Waiting 20s then verifying Business Names...")
    time.sleep(20)

    # Get unique column names that had terms
    unique_cols = list(dict.fromkeys(name for name, _, _ in rows_info))
    populated = 0
    missing_names = []
    for col_name in unique_cols:
        r_v = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery={col_name}&segments=summary",
            headers=H,
            json={"from": 0, "size": 10,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                  "values": [COLUMN_CLASS]}]}, timeout=30)
        hits = r_v.json().get("hits", [])
        bn   = ""
        for h in hits:
            s = h.get("summary", {})
            if s.get("core.name") == col_name:
                bn = s.get("core.businessName", "") or ""
                break
        if bn:
            populated += 1
        else:
            missing_names.append(col_name)
        time.sleep(0.2)

    total_with_terms = len(unique_cols)
    print(f"\n  Business Names populated: {populated}/{total_with_terms}")
    if missing_names:
        print(f"  Not yet visible via search API (check UI — may be index lag):")
        for n in missing_names:
            print(f"    • {n}")
    else:
        print(f"  ✓ All {populated} governed columns have Business Names.")

    print(f"\n✓ Phase 3 complete.\n")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
if args.all:
    run_phase_1()
    run_phase_2a()
    # Phase 2a prints the handoff instructions — stop here for human review
elif args.phase == "1":
    run_phase_1()
elif args.phase == "2a":
    run_phase_2a()
elif args.phase == "2b":
    run_phase_2b()
elif args.phase == "3":
    run_phase_3()
