#!/usr/bin/env python3
"""
audit_dq_links.py

PURPOSE
-------
Audits all DQ Rule Templates — verifies that each template has the
correct occurrences linked in CDGC and reports mismatches.

For each template:
  - Queries its neighborhood via GET segments=all
  - Extracts all linked RuleInstance occurrence names
  - Compares against expected occurrences from File 15
  - Reports: OK / MISSING links / EXTRA (wrong) links

USAGE
-----
  python3 audit_dq_links.py

  Prompts for import directory and IDMC credentials.
"""
import getpass, time, requests, openpyxl
from pathlib import Path

LOGIN_URL  = "https://dmp-us.informaticacloud.com"
ORG_URL    = "https://idmc-api.dmp-us.informaticacloud.com"
ASSOC_TYPE = "com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance"

# ── Import directory ──────────────────────────────────────────────────────────
import_dir_raw = input("Import directory (e.g. ~/Downloads/CDGC_Import_MyClient): ").strip()
IMPORT_DIR = Path(import_dir_raw).expanduser()
TEMPLATE_FILE   = IMPORT_DIR / "13_DQ_Rule_Template_PATCHED.xlsx"
OCCURRENCE_FILE = IMPORT_DIR / "15_DQ_Rule_Occurrence.xlsx"


def load_col(ws, keyword):
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    return next(i for i, h in enumerate(hdr) if h and keyword in str(h))


def build_expected():
    """Returns {tpl_ref: [occ_ref, ...]} from Files 13 + 15."""
    wb_t = openpyxl.load_workbook(TEMPLATE_FILE)
    ws_t = wb_t.active
    tref_col  = load_col(ws_t, "Reference")
    tname_col = load_col(ws_t, "Name")
    name_to_ref = {}
    templates = []
    for row in ws_t.iter_rows(min_row=2, values_only=True):
        ref, name = row[tref_col], row[tname_col]
        if ref and name:
            name_to_ref[str(name).strip()] = str(ref).strip()
            templates.append(str(ref).strip())

    wb_o = openpyxl.load_workbook(OCCURRENCE_FILE)
    ws_o = wb_o.active
    oref_col  = load_col(ws_o, "Reference")
    oname_col = load_col(ws_o, "Name")
    expected = {t: [] for t in templates}
    for row in ws_o.iter_rows(min_row=2, values_only=True):
        oref, oname = row[oref_col], row[oname_col]
        if not oref or not oname:
            continue
        rule_name = str(oname).split(" — ")[0].strip()
        tref = name_to_ref.get(rule_name)
        if tref:
            expected[tref].append(str(oref).strip())
    return expected


def get_linked_occurrences(tpl_ref):
    """Returns list of occurrence names linked to this template in CDGC."""
    r = requests.get(
        f"{ORG_URL}/data360/search/v1/assets/{tpl_ref}?scheme=external&segments=all",
        headers=H, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    linked = []
    for group in (r.json().get("neighborhood") or []):
        for neighbor in (group.get("neighbors") or []):
            for path in (neighbor.get("paths") or []):
                for col in (path.get("collection") or []):
                    if col.get("association") == ASSOC_TYPE:
                        to_val = col.get("to", "")
                        from_type = col.get("fromType", "")
                        to_type   = col.get("toType", "")
                        if "RuleInstance" in to_type or "RuleInstance" in from_type:
                            linked.append(to_val)
    return linked, None


# ── Auth ──────────────────────────────────────────────────────────────────────
username = input("IDMC Username: ").strip()
password = getpass.getpass("IDMC Password: ")

r = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
r.raise_for_status()
sid, oid = r.json()["sessionId"], r.json()["orgId"]
r2 = requests.get(f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": sid}, cookies={"USER_SESSION": sid}, timeout=30)
jwt = r2.json().get("token") or r2.json().get("jwt_token")
H = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": oid, "Content-Type": "application/json"}
print("✓ Authenticated\n")

# ── Build expected map ────────────────────────────────────────────────────────
expected = build_expected()
print(f"Templates to audit: {len(expected)}")
print(f"Expected total links: {sum(len(v) for v in expected.values())}\n")

# ── Audit loop ────────────────────────────────────────────────────────────────
print(f"{'Template':<12} {'Expected':>8} {'Actual':>8}  Status")
print("-" * 60)

ok      = 0
missing = 0
extra   = 0
errors  = 0
issues  = []

for tpl_ref, exp_occs in expected.items():
    linked, err = get_linked_occurrences(tpl_ref)
    if err:
        print(f"  {tpl_ref:<10} {'?':>8} {'?':>8}  ERROR: {err}")
        errors += 1
        time.sleep(0.3)
        continue

    exp_count    = len(exp_occs)
    actual_count = len(linked)

    if actual_count == exp_count:
        print(f"  {tpl_ref:<10} {exp_count:>8} {actual_count:>8}  ✓ OK")
        ok += 1
    elif actual_count < exp_count:
        print(f"  {tpl_ref:<10} {exp_count:>8} {actual_count:>8}  ✗ MISSING {exp_count - actual_count} link(s)")
        missing += 1
        issues.append((tpl_ref, "MISSING", exp_count, actual_count, linked))
    else:
        print(f"  {tpl_ref:<10} {exp_count:>8} {actual_count:>8}  ⚠ EXTRA {actual_count - exp_count} link(s)")
        extra += 1
        issues.append((tpl_ref, "EXTRA", exp_count, actual_count, linked))

    time.sleep(0.25)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {ok} OK | {missing} missing links | {extra} extra links | {errors} errors")

if issues:
    print("\nDetails on mismatches:")
    for tpl_ref, kind, exp, act, linked in issues:
        print(f"\n  {tpl_ref} — {kind} (expected {exp}, got {act})")
        print(f"  Actual linked occurrences ({len(linked)}):")
        for name in linked:
            print(f"    - {name}")
else:
    print("\n✓ All template→occurrence links are correct.")
