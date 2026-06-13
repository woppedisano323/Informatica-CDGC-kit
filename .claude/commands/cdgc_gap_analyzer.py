#!/usr/bin/env python3
"""
cdgc_gap_analyzer.py  —  Governance Gap Analyzer

ANALYZE mode (default):
  Fetches scanned columns + existing Business Terms, then produces a 3-tab
  review workbook:
    Tab 1 — Suggested Links     : ungoverned columns matched to EXISTING terms
    Tab 2 — Suggested New Terms : ungoverned columns with no match — AI-drafted
                                  term name, description, and domain for review
    Tab 3 — Already Governed    : columns already linked (reference only)

APPLY mode (--apply):
  Reads the approved rows from both Tab 1 and Tab 2:
    - Tab 1 APPROVE=YES  → PATCH column glossary link to existing term
    - Tab 2 APPROVE=YES  → POST new Business Term, then PATCH column glossary link

Usage:
  python3 cdgc_gap_analyzer.py                           # analyze
  python3 cdgc_gap_analyzer.py --apply                   # apply approvals
  python3 cdgc_gap_analyzer.py --out ~/Desktop/gap.xlsx  # custom path
"""
import argparse
import getpass
import re
import time
from pathlib import Path

import requests

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl not installed.  Run: pip3 install openpyxl")
    raise SystemExit(1)

# ── Config ────────────────────────────────────────────────────────────────────
LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

COLUMN_CLASS = "com.infa.odin.models.relational.Column"
TERM_CLASS   = "com.infa.ccgf.models.governance.BusinessTerm"

CONFIDENCE_THRESHOLD = 70  # minimum score for Tab 1 suggested links

# Domain ext_ids (RKF prefix in live org)
DOMAINS = {
    "Customer & KYC":    "RKFDOM-1",
    "Transactions":      "RKFDOM-2",
    "General Ledger":    "RKFDOM-3",
    "Risk & Regulatory": "RKFDOM-4",
    "Products":          "RKFDOM-5",
}

# Already-linked columns — skip entirely in gap analysis
ALREADY_LINKED_MAP = {
    "CUSTOMER_ID":            ("RKFBT-1",  "Customer ID"),
    "SSN":                    ("RKFBT-2",  "Social Security Number"),
    "DATE_OF_BIRTH":          ("RKFBT-3",  "Date of Birth"),
    "EMAIL":                  ("RKFBT-4",  "Email Address"),
    "PHONE_NUMBER":           ("RKFBT-5",  "Phone Number"),
    "CREDIT_SCORE":           ("RKFBT-9",  "Credit Score"),
    "TRANSACTION_ID":         ("RKFBT-12", "Transaction ID"),
    "AMOUNT":                 ("RKFBT-13", "Transaction Amount"),
    "TRANSACTION_DATE":       ("RKFBT-15", "Transaction Date"),
    "POSTING_DATE":           ("RKFBT-16", "Post Date"),
    "CURRENCY":               ("RKFBT-17", "Currency Code"),
    "ACCOUNT_CODE":           ("RKFBT-22", "GL Account Number"),
    "DEBIT_AMOUNT":           ("RKFBT-24", "Debit Amount"),
    "CREDIT_AMOUNT":          ("RKFBT-25", "Credit Amount"),
    "STATUS":                 ("RKFBT-26", "Entry Status"),
    "FISCAL_PERIOD":          ("RKFBT-27", "Accounting Period"),
    "PROBABILITY_OF_DEFAULT": ("RKFBT-30", "Probability of Default"),
    "LOSS_GIVEN_DEFAULT":     ("RKFBT-31", "Loss Given Default"),
}

# AI-drafted new Business Terms for ungoverned columns
# Format: column_name_upper → (term_name, description, domain)
NEW_TERM_DRAFTS = {
    # CUSTOMER_MASTER
    "FIRST_NAME":       ("First Name",          "Customer legal first name as provided at onboarding", "Customer & KYC"),
    "LAST_NAME":        ("Last Name",            "Customer legal last name or family name", "Customer & KYC"),
    "ADDRESS_LINE1":    ("Street Address",       "Primary street address line for the customer's residence or mailing address", "Customer & KYC"),
    "CITY":             ("City",                 "City of residence or mailing address for the customer", "Customer & KYC"),
    "STATE":            ("State",                "US state abbreviation for the customer's address", "Customer & KYC"),
    "ZIP_CODE":         ("Zip Code",             "US postal zip code for the customer's address", "Customer & KYC"),
    "ACCOUNT_STATUS":   ("Account Status",       "Current status of the customer account: ACTIVE, INACTIVE, SUSPENDED, or CLOSED", "Customer & KYC"),
    "CUSTOMER_SINCE":   ("Customer Since Date",  "Date the customer relationship was first established with the institution", "Customer & KYC"),
    "ANNUAL_INCOME":    ("Annual Income",        "Customer's declared annual income in USD, used for credit and risk assessment", "Customer & KYC"),
    "RISK_TIER":        ("Customer Risk Tier",   "Internal risk classification tier assigned to the customer: LOW, MEDIUM, HIGH, VERY_HIGH", "Customer & KYC"),
    # TRANSACTION_LEDGER
    "ACCOUNT_ID":       ("Account ID",           "Unique identifier for the financial account associated with a transaction", "Transactions"),
    "TRANSACTION_TYPE": ("Transaction Type",     "Classification of the transaction: DEBIT, CREDIT, TRANSFER, or FEE", "Transactions"),
    "MERCHANT_NAME":    ("Merchant Name",        "Name of the merchant or payee for the transaction", "Transactions"),
    "MERCHANT_CATEGORY":("Merchant Category",    "Merchant category classification used for spend analytics and reporting", "Transactions"),
    "BALANCE_AFTER":    ("Balance After Transaction", "Account balance remaining immediately after a transaction is applied", "Transactions"),
    "CHANNEL":          ("Transaction Channel",  "Channel through which the transaction was initiated: ONLINE, BRANCH, ATM, or MOBILE", "Transactions"),
    "REFERENCE_NUMBER": ("Reference Number",     "External reference or confirmation number assigned to the transaction", "Transactions"),
    # GL_ENTRY_REGISTER
    "ENTRY_ID":         ("GL Entry ID",          "Unique identifier for a general ledger journal entry", "General Ledger"),
    "JOURNAL_ID":       ("Journal ID",           "Identifier for the journal batch containing one or more GL entries", "General Ledger"),
    "ENTRY_DATE":       ("Entry Date",           "Date on which the accounting entry was recorded", "General Ledger"),
    "ACCOUNT_NAME":     ("Account Name",         "Descriptive name of the general ledger account from the chart of accounts", "General Ledger"),
    "NET_AMOUNT":       ("Net Amount",           "Net monetary amount calculated as debit minus credit for a GL entry", "General Ledger"),
    "COST_CENTER":      ("Cost Center",          "Business unit cost center code used for financial reporting and allocation", "General Ledger"),
    "LEGAL_ENTITY":     ("Legal Entity",         "Legal entity associated with the journal entry for consolidation reporting", "General Ledger"),
    "FISCAL_YEAR":      ("Fiscal Year",          "Fiscal year in which the journal entry is recorded", "General Ledger"),
    "CREATED_BY":       ("Created By",           "User who created the journal entry in the financial system", "General Ledger"),
    "APPROVED_BY":      ("Approved By",          "User who approved the journal entry before posting to the ledger", "General Ledger"),
    # RISK_EXPOSURE_DAILY
    "RISK_ID":          ("Risk Assessment ID",   "Unique identifier for a risk exposure assessment record", "Risk & Regulatory"),
    "ASSESSMENT_DATE":  ("Assessment Date",      "Date on which the risk exposure assessment was performed", "Risk & Regulatory"),
    "RISK_CATEGORY":    ("Risk Category",        "Type of risk: CREDIT, MARKET, OPERATIONAL, LIQUIDITY, or REGULATORY", "Risk & Regulatory"),
    "EXPOSURE_AMOUNT":  ("Exposure Amount",      "Total monetary exposure amount in USD for the risk assessment", "Risk & Regulatory"),
    "EXPECTED_LOSS":    ("Expected Loss",        "Calculated expected loss: exposure amount × probability of default × loss given default", "Risk & Regulatory"),
    "RISK_RATING":      ("Risk Rating",          "Internal credit risk rating assigned to the obligor: AAA through CCC", "Risk & Regulatory"),
    "COLLATERAL_VALUE": ("Collateral Value",     "Estimated market value of collateral securing the exposure", "Risk & Regulatory"),
    "REGULATORY_CAPITAL":("Regulatory Capital", "Required regulatory capital allocation for the exposure under Basel III rules", "Risk & Regulatory"),
    "BASEL_CLASS":      ("Basel Asset Class",    "Basel III asset class classification for capital adequacy calculation", "Risk & Regulatory"),
}

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument("--out",   default="CDGC_Gap_Review.xlsx")
args = parser.parse_args()
OUT_PATH = Path(args.out)

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

# ── API helpers ───────────────────────────────────────────────────────────────
def fetch_all(class_type):
    results, offset = [], 0
    while True:
        body = {"from": offset, "size": 100,
                "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                 "values": [class_type]}]}
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=H, json=body, timeout=30)
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


def post_term(name, description, domain_ext_id):
    """Create a new Business Term under the given domain."""
    body = {
        "core.classType": TERM_CLASS,
        "summary": {"core.name": name, "core.description": description},
        "parent": {"core.externalId": domain_ext_id},
    }
    r = requests.post(f"{ORG_URL}/data360/content/v1/assets",
                      headers=H, json=body, timeout=30)
    return r.status_code, r.json()

# ── Fuzzy matcher ─────────────────────────────────────────────────────────────
NOISE = {"of","the","a","an","and","or","for","in","on","at","to","is","as",
         "by","be","its","per","from","with","after","before"}

def tokens(s):
    return set(w.lower() for w in re.split(r'[_\s]+', s) if w)

def score(col_name, term_name, term_desc=""):
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
        s = score(col_name, t["name"], t.get("description", ""))
        if s >= CONFIDENCE_THRESHOLD:
            if best is None or s > best[2]:
                best = (t["ext_id"], t["name"], s)
    return best

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

def write_row(ws, rn, values, fill=None, approve_font=None):
    for i, val in enumerate(values, 1):
        c = ws.cell(rn, i, val)
        c.border = BORDER
        c.alignment = Alignment(vertical="center", wrap_text=(i >= len(values) - 1))
        if fill:
            c.fill = fill
    if approve_font:
        ws.cell(rn, 1).font = approve_font
    ws.row_dimensions[rn].height = 18

def inst_row(ws, text, ncols):
    ws.insert_rows(2)
    c = ws.cell(2, 1, text)
    c.font = Font(color="1565C0", italic=True, size=10)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 18
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)

# ══════════════════════════════════════════════════════════════════════════════
# APPLY MODE
# ══════════════════════════════════════════════════════════════════════════════
if args.apply:
    if not OUT_PATH.exists():
        print(f"ERROR: {OUT_PATH} not found")
        raise SystemExit(1)

    wb  = load_workbook(OUT_PATH)
    ok = fail = 0

    # ── Tab 1: link existing terms ────────────────────────────────────────────
    if "Suggested Links" in wb.sheetnames:
        ws1 = wb["Suggested Links"]
        hdrs = [c.value for c in ws1[1]]
        idx  = {h: i for i, h in enumerate(hdrs)}
        print("Applying Tab 1 — Suggested Links...")
        for row in ws1.iter_rows(min_row=3, values_only=True):
            if str(row[idx.get("APPROVE", 0)] or "").strip().upper() != "YES":
                continue
            col_id   = row[idx["Column Internal ID"]]
            term_ext = row[idx["Term ext_id"]]
            col_name = row[idx["Column Name"]]
            table    = row[idx["Table"]]
            status, body = patch_glossary(col_id, term_ext)
            already = status == 500 and term_ext in body
            if status in (200, 204) or already:
                tag = "(already)" if already else ""
                print(f"  ✓ {table}.{col_name} → {term_ext} {tag}")
                ok += 1
            else:
                print(f"  ✗ {table}.{col_name}  [{status}] {body[:80]}")
                fail += 1
            time.sleep(0.3)

    # ── Tab 2: create new terms then link ─────────────────────────────────────
    if "Suggested New Terms" in wb.sheetnames:
        ws2 = wb["Suggested New Terms"]
        hdrs = [c.value for c in ws2[1]]
        idx  = {h: i for i, h in enumerate(hdrs)}
        print("\nApplying Tab 2 — Suggested New Terms...")
        for row in ws2.iter_rows(min_row=3, values_only=True):
            if str(row[idx.get("APPROVE", 0)] or "").strip().upper() != "YES":
                continue
            col_id    = row[idx["Column Internal ID"]]
            col_name  = row[idx["Column Name"]]
            table     = row[idx["Table"]]
            term_name = row[idx["Business Term Name"]]
            term_desc = row[idx["Description"]]
            domain    = row[idx["Domain"]]
            dom_ext   = DOMAINS.get(domain, "RKFDOM-1")

            # Create the Business Term
            status, resp_data = post_term(term_name, term_desc, dom_ext)
            if status in (200, 201):
                new_ext = (resp_data.get("core.externalId", "")
                           or resp_data.get("externalId", ""))
                print(f"  ✓ Created term '{term_name}' ({new_ext})")
                time.sleep(0.5)
                # Link column to new term
                if new_ext:
                    s2, b2 = patch_glossary(col_id, new_ext)
                    if s2 in (200, 204):
                        print(f"    ✓ Linked {table}.{col_name} → {new_ext}")
                        ok += 1
                    else:
                        print(f"    ✗ Link failed [{s2}] {b2[:80]}")
                        fail += 1
                else:
                    print(f"    ⚠ Term created but no ext_id returned — link manually")
                    fail += 1
            else:
                print(f"  ✗ Failed to create '{term_name}'  [{status}] {str(resp_data)[:80]}")
                fail += 1
            time.sleep(0.3)

    print(f"\n{'─'*50}")
    print(f"Done.  {ok} applied,  {fail} failed.")
    raise SystemExit(0)

# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE MODE
# ══════════════════════════════════════════════════════════════════════════════
print("Fetching scanned columns...")
col_hits = fetch_all(COLUMN_CLASS)
print(f"  {len(col_hits)} columns")

print("Fetching Business Terms...")
term_hits = fetch_all(TERM_CLASS)
terms = [{"ext_id": h.get("core.externalId",""),
          "name":   (h.get("summary") or {}).get("core.name",""),
          "description": (h.get("summary") or {}).get("core.description","")}
         for h in term_hits]
print(f"  {len(terms)} terms\n")

# Build column records with table from location path
columns = []
for h in col_hits:
    s     = h.get("summary") or {}
    name  = s.get("core.name","")
    loc   = s.get("core.location","")
    parts = loc.rstrip("/").split("/")
    table = parts[-2] if len(parts) >= 2 else ""
    int_id = h.get("core.identity","")
    columns.append({"name": name, "table": table, "id": int_id})

# Categorize
linked_tab, suggest_link, suggest_new = [], [], []

for col in sorted(columns, key=lambda c: (c["table"], c["name"])):
    upper = col["name"].upper()
    if upper in ALREADY_LINKED_MAP:
        bt_ext, bt_name = ALREADY_LINKED_MAP[upper]
        linked_tab.append({**col, "term_ext": bt_ext, "term_name": bt_name})
    else:
        match = best_match(col["name"], terms)
        if match:
            suggest_link.append({**col, "term_ext": match[0],
                                  "term_name": match[1], "confidence": match[2]})
        else:
            draft = NEW_TERM_DRAFTS.get(upper)
            if draft:
                suggest_new.append({**col, "draft_name": draft[0],
                                    "draft_desc": draft[1], "domain": draft[2]})
            else:
                suggest_new.append({**col, "draft_name": col["name"].replace("_"," ").title(),
                                    "draft_desc": f"[Edit description for {col['name']}]",
                                    "domain": "Customer & KYC"})

print(f"Results:")
print(f"  Already governed : {len(linked_tab)}")
print(f"  Suggested links  : {len(suggest_link)}")
print(f"  Suggested new    : {len(suggest_new)}")
print()

# ── Build workbook ────────────────────────────────────────────────────────────
wb = Workbook()

# ── Tab 1: Suggested Links ────────────────────────────────────────────────────
ws1 = wb.active
ws1.title = "Suggested Links"
ws1.freeze_panes = "A3"
COLS1 = [("APPROVE",14),("Table",22),("Column Name",22),("Suggested Business Term",28),
         ("Confidence",12),("Term Description",42),("Term ext_id",14),("Column Internal ID",38)]
style_header(ws1, COLS1)
inst_row(ws1, "→ Set APPROVE to YES, then run: python3 cdgc_gap_analyzer.py --apply", len(COLS1))

for row in suggest_link:
    desc = next((t["description"] for t in terms if t["ext_id"] == row["term_ext"]), "")
    fill = YES_FILL if row["confidence"] >= 85 else WARN_FILL
    write_row(ws1, ws1.max_row+1,
              ["", row["table"], row["name"], row["term_name"],
               f"{row['confidence']}%", desc, row["term_ext"], row["id"]],
              fill=fill, approve_font=YES_FONT)

if not suggest_link:
    ws1.cell(ws1.max_row+1, 1, "No suggested links found — all ungoverned columns need new terms (see Tab 2)")

# ── Tab 2: Suggested New Terms ────────────────────────────────────────────────
ws2 = wb.create_sheet("Suggested New Terms")
ws2.freeze_panes = "A3"
COLS2 = [("APPROVE",14),("Table",22),("Column Name",22),("Business Term Name",28),
         ("Description",52),("Domain",22),("Column Internal ID",38)]
style_header(ws2, COLS2)
inst_row(ws2, "→ Edit Name/Description/Domain as needed, set APPROVE to YES, then run: python3 cdgc_gap_analyzer.py --apply", len(COLS2))

for row in suggest_new:
    write_row(ws2, ws2.max_row+1,
              ["", row["table"], row["name"], row["draft_name"],
               row["draft_desc"], row["domain"], row["id"]],
              fill=NEW_FILL, approve_font=BLUE_FONT)

# ── Tab 3: Already Governed ────────────────────────────────────────────────────
ws3 = wb.create_sheet("Already Governed")
ws3.freeze_panes = "A2"
COLS3 = [("Table",22),("Column Name",22),("Business Term",28),("Term ext_id",14)]
style_header(ws3, COLS3)
for row in linked_tab:
    write_row(ws3, ws3.max_row+1,
              [row["table"], row["name"], row["term_name"], row["term_ext"]],
              fill=DONE_FILL)

wb.save(OUT_PATH)
print(f"✓ Written: {OUT_PATH}")
print()
print("Next steps:")
print(f"  1. Open {OUT_PATH.name}")
print(f"  2. Tab 1 'Suggested Links'    — set APPROVE=YES to link to existing terms")
print(f"  3. Tab 2 'Suggested New Terms'— edit descriptions, set APPROVE=YES to create + link")
print(f"  4. Run: python3 cdgc_gap_analyzer.py --apply")
