#!/usr/bin/env python3
"""
link_dq_templates_to_occurrences.py

PURPOSE
-------
Creates the Rule Template → Rule Occurrence relationship for all DQ rule
occurrences via the CDGC REST API.

BACKGROUND
----------
DQ Rule Occurrences (RuleInstance assets) must be linked to their parent DQ Rule
Template (RuleTemplate assets) so CDGC can display the "Rule Template" field on
each occurrence and associate scoring results correctly.

When CDGC automation is enabled on a template (Enable Automation = TRUE), it creates
this link automatically. However, occurrences created via bulk import (File 15)
bypass automation — so the link is never established.

The Bulk Import template has no "Rule Template" column on the DQ Rule Occurrence sheet,
and the Relationships Annexure has no RuleTemplate→RuleInstance entry, confirming
there is no import-based mechanism for this relationship. It must be set via API.

MAPPING APPROACH
----------------
The mapping is many-to-one: templates cover occurrences (some rules apply to
multiple columns). The match is done by rule name:
  - Occurrence name format: "<rule name> — <TABLE.COLUMN>"
  - The part before " — " must exactly match a template name in File 13

Files used:
  - 13_DQ_Rule_Template_PATCHED.xlsx  — authoritative template reference IDs
  - 15_DQ_Rule_Occurrence.xlsx        — all occurrence reference IDs and names

RELATIONSHIP TYPE
-----------------
  com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance
  Direction: RuleTemplate ──→ RuleInstance

API ENDPOINT
------------
  PATCH /data360/content/v1/assets/{templateExternalId}?scheme=external
  Body:
    [{"operation": "add", "segment": "relationship",
      "items": [{"fromExternalIdentity": "<template-ref>",
                 "toExternalIdentity": "<occurrence-ref>",
                 "association": "<relationship type>"}]}]
  Reference: CDGC API Reference (April 2026), Chapter 4 — Manage assets,
             Update assets > Create relationship example (page 55)

USAGE
-----
  python3 link_dq_templates_to_occurrences.py

  Prompts for import directory and IDMC credentials.

BEHAVIOR
--------
  - Loads template and occurrence Excel files to build the name-based mapping
  - For each occurrence:
      1. Resolves the matching template reference ID by rule name
      2. Issues PATCH to create the relatedRuleTemplateRuleInstance link
      3. Treats HTTP 409 (already linked) as a skip — safe to re-run
  - Reports linked / skipped / failed counts at the end
  - Lists any failed pairs with HTTP status and response for diagnosis

NOTES
-----
  - Safe to re-run: 409 responses (already linked) are counted as skipped
  - After completion, verify with: python3 check_dq_links.py
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


def build_template_map():
    """Returns {rule_name: template_ref_id} from File 13."""
    wb = openpyxl.load_workbook(TEMPLATE_FILE)
    ws = wb.active
    ref_col  = load_col(ws, "Reference")
    name_col = load_col(ws, "Name")
    result = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        ref, name = row[ref_col], row[name_col]
        if ref and name:
            result[str(name).strip()] = str(ref).strip()
    return result


def build_occurrence_pairs(template_map):
    """Returns list of (occ_ref, tpl_ref) tuples from File 15, matched by rule name."""
    wb = openpyxl.load_workbook(OCCURRENCE_FILE)
    ws = wb.active
    ref_col  = load_col(ws, "Reference")
    name_col = load_col(ws, "Name")
    pairs = []
    unmatched = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        oref, oname = row[ref_col], row[name_col]
        if not oref or not oname:
            continue
        rule_name = str(oname).split(" — ")[0].strip()
        tref = template_map.get(rule_name)
        if tref:
            pairs.append((str(oref).strip(), tref))
        else:
            unmatched.append((str(oref).strip(), rule_name))
    return pairs, unmatched


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

# ── Build mapping ─────────────────────────────────────────────────────────────
template_map = build_template_map()
print(f"Templates loaded: {len(template_map)}")

pairs, unmatched = build_occurrence_pairs(template_map)
print(f"Occurrence pairs resolved: {len(pairs)}")

if unmatched:
    print(f"\n⚠ Unmatched occurrences (no template found by name):")
    for oref, rule_name in unmatched:
        print(f"  {oref}  rule_name=\"{rule_name}\"")
    print()

# ── Main loop ─────────────────────────────────────────────────────────────────
print(f"{'Occurrence':<14} {'Template':<12} {'Status':<12} Detail")
print("-" * 70)

linked  = 0
skipped = 0
failed  = 0
errors  = []

for occ_id, tpl_id in pairs:
    url  = f"{ORG_URL}/data360/content/v1/assets/{tpl_id}?scheme=external"
    body = [{
        "operation": "add",
        "segment": "relationship",
        "items": [{
            "fromExternalIdentity": tpl_id,
            "toExternalIdentity": occ_id,
            "association": ASSOC_TYPE
        }]
    }]
    r = requests.patch(url, headers=H, json=body, timeout=30)

    if r.status_code in (200, 201, 204):
        print(f"  {occ_id:<12} {tpl_id:<12} ✓ LINKED")
        linked += 1
    elif r.status_code == 409:
        print(f"  {occ_id:<12} {tpl_id:<12} SKIP         already linked")
        skipped += 1
    else:
        print(f"  {occ_id:<12} {tpl_id:<12} ✗ FAILED     HTTP {r.status_code}: {r.text[:60]}")
        failed += 1
        errors.append((tpl_id, occ_id, r.status_code, r.text[:200]))

    time.sleep(0.3)

print(f"\n{'='*70}")
print(f"Results: {linked} linked | {skipped} already linked | {failed} failed")

if errors:
    print("\nFailed pairs:")
    for tpl, occ, code, txt in errors:
        print(f"  {tpl} → {occ}  HTTP {code}: {txt}")
else:
    print("\n✓ All pairs processed — run check_dq_links.py to verify.")
