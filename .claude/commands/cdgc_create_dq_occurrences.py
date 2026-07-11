#!/usr/bin/env python3
"""
cdgc_create_dq_occurrences.py

Reads 13_DQ_Rule_Template_PATCHED.xlsx, queries CDGC for every column whose
name matches a rule's Input Port Name, and generates 15_DQ_Rule_Occurrence.xlsx.

Operation=Create  — use when occurrences do not yet exist in CDGC (first run)
Operation=Update  — use when occurrences already exist (re-run after changes)

The Primary Data Element field format required by bulk import is:
  CatalogSourceName://DB/Schema/Table/ColumnName

We reconstruct this from core.location in the CDGC search API response.

Usage:
  python3 cdgc_create_dq_occurrences.py              # defaults to Create
  python3 cdgc_create_dq_occurrences.py --update     # sets Operation=Update
  python3 cdgc_update_dq_occurrences.py              # wrapper for Update
"""
import argparse
import getpass
import time
from pathlib import Path

import requests

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--update", action="store_true", help="Set Operation=Update instead of Create")
args_parsed, _ = parser.parse_known_args()
OPERATION = "Update" if args_parsed.update else "Create"

try:
    from openpyxl import load_workbook, Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    raise SystemExit("pip3 install openpyxl")

LOGIN_URL    = "https://dmp-us.informaticacloud.com"
ORG_URL      = "https://idmc-api.dmp-us.informaticacloud.com"
COLUMN_CLASS = "com.infa.odin.models.relational.Column"

# ── Import directory and occurrence prefix ────────────────────────────────────
import_dir_raw = input("Import directory (e.g. ~/Downloads/CDGC_Import_MyClient): ").strip()
IMPORT_DIR = Path(import_dir_raw).expanduser()
OCC_PREFIX = input("Occurrence reference ID prefix (e.g. DQOCC): ").strip()

TEMPLATE_FILE   = IMPORT_DIR / "13_DQ_Rule_Template_PATCHED.xlsx"
OCCURRENCE_FILE = IMPORT_DIR / (
    "15_DQ_Rule_Occurrence_UPDATE.xlsx" if OPERATION == "Update"
    else "15_DQ_Rule_Occurrence.xlsx"
)

# Measuring method normalization — template uses CamelCase, import expects exact string
METHOD_MAP = {
    "technicalscript":              "TechnicalScript",
    "technical script":             "TechnicalScript",
    "businessextract":              "BusinessExtract",
    "business extract":             "BusinessExtract",
    "systemfunction":               "SystemFunction",
    "system function":              "SystemFunction",
    "informaticaclouddataquality":  "InformaticaCloudDataQuality",
    "informatica cloud data quality":"InformaticaCloudDataQuality",
}

# ── Auth ──────────────────────────────────────────────────────────────────────
username = input("IDMC Username: ").strip()
password = getpass.getpass("IDMC Password: ")

r = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
r.raise_for_status()
sid, oid = r.json()["sessionId"], r.json()["orgId"]
r2 = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": sid}, cookies={"USER_SESSION": sid}, timeout=30)
jwt = r2.json().get("token") or r2.json().get("jwt_token")
H = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": oid, "Content-Type": "application/json"}
print("✓ Authenticated\n")

# ── Read DQ Rule Templates ────────────────────────────────────────────────────
print("Reading 13_DQ_Rule_Template.xlsx...")
wb_tmpl = load_workbook(TEMPLATE_FILE)
ws_tmpl = wb_tmpl.active
hdrs = [str(c.value or "").strip() for c in ws_tmpl[1]]
print(f"  Headers: {hdrs}\n")

rules = []
for row in ws_tmpl.iter_rows(min_row=2, values_only=True):
    if not any(row):
        continue
    d = dict(zip(hdrs, row))
    operation  = str(d.get("Operation") or "").strip().lower()
    if operation == "delete":
        continue
    input_port = str(d.get("Input Port Name") or "").strip()
    if not input_port:
        print(f"  SKIP (no Input Port Name): {d.get('Reference ID')} — {d.get('Name')}")
        continue
    raw_method = str(d.get("Measuring Method") or "TechnicalScript").strip()
    method     = METHOD_MAP.get(raw_method.lower(), raw_method)
    rules.append({
        "ref_id":       str(d.get("Reference ID") or "").strip(),
        "name":         str(d.get("Name") or "").strip(),
        "dimension":    str(d.get("Dimension") or "Completeness").strip(),
        "criticality":  str(d.get("Criticality") or "Medium").strip(),
        "method":       method,
        "tech_ref":     str(d.get("Technical Rule Reference") or "").strip(),
        "target":       d.get("Target") if d.get("Target") is not None else 95,
        "threshold":    d.get("Threshold") if d.get("Threshold") is not None else 90,
        "input_port":   input_port,
        "primary_glossary": str(d.get("Primary Glossary") or "").strip(),
    })

print(f"  {len(rules)} rules loaded:")
for r_ in rules:
    print(f"    [{r_['ref_id']}] {r_['name']}  →  column: {r_['input_port']}")

# ── Fetch all scanned columns ─────────────────────────────────────────────────
print("\nFetching all scanned columns from CDGC...")
all_cols = []
offset   = 0
while True:
    r3 = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
        headers=H,
        json={"from": offset, "size": 100,
              "filterSpec": [{"type": "simple", "attribute": "core.classType",
                              "values": [COLUMN_CLASS]}]}, timeout=30)
    r3.raise_for_status()
    hits = r3.json().get("hits", [])
    for h in hits:
        s    = h.get("summary") or {}
        name = s.get("core.name", "")
        loc  = s.get("core.location", "")
        if name and loc:
            all_cols.append({"name": name, "loc": loc})
    if len(hits) < 100:
        break
    offset += 100
    time.sleep(0.3)

print(f"  {len(all_cols)} columns found")
print("\n  Sample core.location values (first 5):")
for c in all_cols[:5]:
    print(f"    name={c['name']!r}  loc={c['loc']!r}")

# ── Resolve catalog source name from UUID ─────────────────────────────────────
def get_catalog_source_name(uuid: str) -> str:
    """Look up the human-readable catalog source name by its internal UUID."""
    try:
        r = requests.get(
            f"{ORG_URL}/data360/search/v1/assets/{uuid}?scheme=internal&segments=summary",
            headers=H, timeout=30)
        if r.status_code == 200:
            name = (r.json().get("summary") or {}).get("core.name", "")
            if name:
                return name
    except Exception:
        pass
    return uuid  # fallback: use UUID as-is


# ── Build Primary Data Element from core.location ────────────────────────────
def build_pde(loc: str, catalog_name: str) -> str:
    """
    core.location actual format observed in CDGC:
      UUID://UUID/DB/Schema/Table/Column

    Required import format:
      CatalogSourceName://DB/Schema/Table/Column

    Strategy:
      - Split on '://' to isolate the path portion
      - The path portion is UUID/DB/Schema/Table/Column
      - Strip the leading UUID segment to get DB/Schema/Table/Column
      - Prepend the human-readable catalog source name
    """
    if "://" not in loc:
        return ""
    after_scheme = loc.split("://", 1)[1]        # UUID/DB/Schema/Table/Column
    slash_pos = after_scheme.find("/")
    if slash_pos == -1:
        return ""
    path = after_scheme[slash_pos + 1:]           # DB/Schema/Table/Column
    if not path:
        return ""
    return f"{catalog_name}://{path}"

# ── Resolve catalog source name from the UUID in the first location sample ────
catalog_name = ""
if all_cols:
    first_loc = all_cols[0]["loc"]
    if "://" in first_loc:
        catalog_uuid = first_loc.split("://", 1)[0]
        print(f"\nResolving catalog source name for UUID: {catalog_uuid} ...")
        resolved = get_catalog_source_name(catalog_uuid)
        if resolved and resolved != catalog_uuid:
            catalog_name = resolved
            print(f"  → Catalog source name: {catalog_name}")
        else:
            catalog_name = input("  Could not resolve catalog source name. Enter it manually (from MCC → Catalog Sources): ").strip()
            print(f"  → Using: {catalog_name}")

# ── Index columns by name → list of (pde, table) ─────────────────────────────
col_by_name: dict[str, list[dict]] = {}
for c in all_cols:
    key = c["name"].upper()
    pde = build_pde(c["loc"], catalog_name)
    if not pde:
        continue
    # Table is the second-to-last path segment in DB/Schema/Table/Column
    path_after_scheme = c["loc"].split("://", 1)[1] if "://" in c["loc"] else c["loc"]
    slash_pos = path_after_scheme.find("/")
    path_only = path_after_scheme[slash_pos + 1:] if slash_pos != -1 else path_after_scheme
    parts = [p for p in path_only.split("/") if p]  # [DB, Schema, Table, Column]
    table = parts[-2] if len(parts) >= 2 else (parts[-1] if parts else "UNKNOWN")
    entry = {"pde": pde, "table": table}
    if key not in col_by_name:
        col_by_name[key] = []
    if pde not in [e["pde"] for e in col_by_name[key]]:
        col_by_name[key].append(entry)

# ── Match rules to columns ────────────────────────────────────────────────────
print("\nMatching rules to columns...")
occurrences = []
occ_counter = 1
warnings    = []

for rule in rules:
    port_key = rule["input_port"].upper()
    matches  = col_by_name.get(port_key, [])
    if not matches:
        msg = f"  WARNING: No columns match Input Port Name '{rule['input_port']}' (rule {rule['ref_id']} — {rule['name']})"
        print(msg)
        warnings.append(msg)
        continue
    print(f"  {rule['ref_id']} ({rule['input_port']}): {len(matches)} column(s)")
    for m in matches:
        occ_name = f"{rule['name']} — {m['table']}.{rule['input_port']}"
        occ_ref  = f"{OCC_PREFIX}-{occ_counter}"
        occ_counter += 1
        occurrences.append({
            "ref_id":     occ_ref,
            "name":       occ_name,
            "dimension":  rule["dimension"],
            "criticality":rule["criticality"],
            "method":     rule["method"],
            "tech_ref":   rule["tech_ref"],
            "target":     rule["target"],
            "threshold":  rule["threshold"],
            "pde":        m["pde"],
            "table":      m["table"],
            "rule_name":  rule["name"],
            "input_port": rule["input_port"],
        })

print(f"\n  Occurrences to create: {len(occurrences)}")

# ── Preview table ─────────────────────────────────────────────────────────────
print("\n  Preview:")
print(f"  {'Ref ID':<12} {'Table':<30} {'Column':<20} {'PDE (truncated)'}")
print(f"  {'-'*12} {'-'*30} {'-'*20} {'-'*40}")
for occ in occurrences[:20]:
    col = occ["pde"].split("/")[-1]
    pde_short = occ["pde"][:60] + "..." if len(occ["pde"]) > 60 else occ["pde"]
    print(f"  {occ['ref_id']:<12} {occ['table']:<30} {col:<20} {pde_short}")
if len(occurrences) > 20:
    print(f"  ... and {len(occurrences) - 20} more")

# ── Write 15_DQ_Rule_Occurrence.xlsx ─────────────────────────────────────────
print(f"\nWriting {OCCURRENCE_FILE.name}...")
wb_out  = Workbook()
ws_out  = wb_out.active
ws_out.title = "Data Quality Rule Occurrence"

# Column order matches CDGC_Template_All.xlsx "Data Quality Rule Occurrence" tab exactly
HDR_COLS = [
    ("Reference ID",                          18),
    ("Name",                                  50),
    ("Description",                           20),
    ("Criticality",                           14),
    ("Dimension",                             16),
    ("Exception File Path",                   20),
    ("Frequency",                             14),
    ("Input Port Name",                       20),
    ("Lifecycle",                             14),
    ("Measuring Method",                      24),
    ("Output Port Name",                      20),
    ("Scanned Time",                          20),
    ("Score",                                 10),
    ("Technical Description",                 24),
    ("Technical Rule Reference",              28),
    ("Target",                                10),
    ("Threshold",                             12),
    ("Total Rows",                            14),
    ("Failed Rows",                           14),
    ("Primary Data Element",                  70),
    ("Secondary Data Element",                30),
    ("Operation",                             12),
    ("Stakeholder: Governance Owner",         30),
    ("Stakeholder: Governance Administrator", 30),
]

hdr_fill = PatternFill("solid", fgColor="1B2A4A")
hdr_font = Font(color="FFFFFF", bold=True, size=11)
row_font = Font(size=10)

for i, (label, width) in enumerate(HDR_COLS, 1):
    c = ws_out.cell(1, i, label)
    c.font      = hdr_font
    c.fill      = hdr_fill
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws_out.column_dimensions[get_column_letter(i)].width = width
ws_out.row_dimensions[1].height = 22

for occ in occurrences:
    row_data = [
        occ["ref_id"],       # Reference ID
        occ["name"],         # Name
        "",                  # Description
        occ["criticality"],  # Criticality
        occ["dimension"],    # Dimension
        "",                  # Exception File Path
        "",                  # Frequency
        occ["input_port"],   # Input Port Name
        "",                  # Lifecycle
        occ["method"],       # Measuring Method — InformaticaCloudDataQuality or TechnicalScript
        "Output" if occ["method"] == "InformaticaCloudDataQuality" else "",  # Output Port Name
        "",                  # Scanned Time
        "",                  # Score
        "",                  # Technical Description
        occ["tech_ref"],     # Technical Rule Reference — ICDQ rule ID when InformaticaCloudDataQuality
        occ["target"],       # Target
        occ["threshold"],    # Threshold
        "",                  # Total Rows
        "",                  # Failed Rows
        occ["pde"],          # Primary Data Element
        "",                  # Secondary Data Element
        OPERATION,           # Operation — Create (first run) or Update (re-run)
        "",                  # Stakeholder: Governance Owner
        "",                  # Stakeholder: Governance Administrator
    ]
    ws_out.append(row_data)
    rn = ws_out.max_row
    for ci in range(1, len(HDR_COLS) + 1):
        ws_out.cell(rn, ci).font      = row_font
        ws_out.cell(rn, ci).alignment = Alignment(vertical="center")
    ws_out.row_dimensions[rn].height = 16

wb_out.save(OCCURRENCE_FILE)
print(f"✓ Saved: {OCCURRENCE_FILE}")
print(f"  {len(occurrences)} rows  ({occ_counter - 1} occurrences)")

if warnings:
    print(f"\nWarnings ({len(warnings)} rules had no column matches):")
    for w in warnings:
        print(w)

print(f"""
{'═'*60}
NEXT STEPS
{'═'*60}
1. Verify the file:
   open "{OCCURRENCE_FILE}"

   Check that the Primary Data Element paths look correct:
     CatalogSourceName://DB/Schema/Table/Column

2. Import into CDGC using the bulk import tool or API.
   Upload: {OCCURRENCE_FILE.name}

3. After import completes (COMPLETED), run another MCC scan.
   The DQ scores will now appear on the matched columns.
{'═'*60}
""")
