#!/usr/bin/env python3
"""
unlink_wrong_dq_template_links.py

PURPOSE
-------
Removes the 37 incorrect RuleTemplate→RuleInstance relationships created by
the first (numeric 1:1) run of link_dq_templates_to_occurrences.py.

BACKGROUND
----------
The first run assumed FCBDQ-N maps to FCBDQO-N (same number). This is wrong —
the mapping is many-to-one by rule name. For example, FCBDQ-39 (Annual Income
Positive) should link to FCBDQO-39, FCBDQO-40, FCBDQO-41 — but the numeric
run instead linked FCBDQ-39 to FCBDQO-39, creating a cross-rule link.

This script removes those 37 wrong links using operation=remove.
The correct links (set by the name-based run) are left untouched.

API ENDPOINT
------------
  PATCH /data360/content/v1/assets/{templateExternalId}?scheme=external
  Body: [{"operation": "remove", "segment": "relationship",
          "items": [{"fromExternalIdentity": "FCBDQ-N",
                     "toExternalIdentity": "FCBDQO-N",
                     "association": "<relationship type>"}]}]

USAGE
-----
  python3 unlink_wrong_dq_template_links.py
"""
import getpass, time, requests

LOGIN_URL  = "https://dmp-us.informaticacloud.com"
ORG_URL    = "https://idmc-api.dmp-us.informaticacloud.com"
ASSOC_TYPE = "com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance"

# Wrong links: (template_that_was_incorrectly_used, occurrence_that_was_linked_to_it)
# FCBDQ-N was linked to FCBDQO-N but correct template for FCBDQO-N is a different FCBDQ-*
WRONG_LINKS = [
    ("FCBDQ-4",  "FCBDQO-4"),
    ("FCBDQ-5",  "FCBDQO-5"),
    ("FCBDQ-6",  "FCBDQO-6"),
    ("FCBDQ-7",  "FCBDQO-7"),
    ("FCBDQ-8",  "FCBDQO-8"),
    ("FCBDQ-9",  "FCBDQO-9"),
    ("FCBDQ-10", "FCBDQO-10"),
    ("FCBDQ-11", "FCBDQO-11"),
    ("FCBDQ-12", "FCBDQO-12"),
    ("FCBDQ-13", "FCBDQO-13"),
    ("FCBDQ-14", "FCBDQO-14"),
    ("FCBDQ-15", "FCBDQO-15"),
    ("FCBDQ-16", "FCBDQO-16"),
    ("FCBDQ-17", "FCBDQO-17"),
    ("FCBDQ-18", "FCBDQO-18"),
    ("FCBDQ-19", "FCBDQO-19"),
    ("FCBDQ-20", "FCBDQO-20"),
    ("FCBDQ-21", "FCBDQO-21"),
    ("FCBDQ-22", "FCBDQO-22"),
    ("FCBDQ-23", "FCBDQO-23"),
    ("FCBDQ-24", "FCBDQO-24"),
    ("FCBDQ-25", "FCBDQO-25"),
    ("FCBDQ-26", "FCBDQO-26"),
    ("FCBDQ-27", "FCBDQO-27"),
    ("FCBDQ-28", "FCBDQO-28"),
    ("FCBDQ-29", "FCBDQO-29"),
    ("FCBDQ-30", "FCBDQO-30"),
    ("FCBDQ-31", "FCBDQO-31"),
    ("FCBDQ-32", "FCBDQO-32"),
    ("FCBDQ-33", "FCBDQO-33"),
    ("FCBDQ-34", "FCBDQO-34"),
    ("FCBDQ-35", "FCBDQO-35"),
    ("FCBDQ-36", "FCBDQO-36"),
    ("FCBDQ-37", "FCBDQO-37"),
    ("FCBDQ-38", "FCBDQO-38"),
    ("FCBDQ-39", "FCBDQO-39"),
    ("FCBDQ-40", "FCBDQO-40"),
]

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

# ── Remove loop ───────────────────────────────────────────────────────────────
print(f"{'Template':<12} {'Occurrence':<14} {'Status':<12} Detail")
print("-" * 70)

removed = 0
skipped = 0
failed  = 0
errors  = []

for tpl_id, occ_id in WRONG_LINKS:
    url  = f"{ORG_URL}/data360/content/v1/assets/{tpl_id}?scheme=external"
    body = [{
        "operation": "remove",
        "segment": "relationship",
        "items": [{
            "fromExternalIdentity": tpl_id,
            "toExternalIdentity": occ_id,
            "association": ASSOC_TYPE
        }]
    }]
    r = requests.patch(url, headers=H, json=body, timeout=30)

    if r.status_code in (200, 201, 204):
        print(f"  {tpl_id:<10} {occ_id:<14} ✓ REMOVED")
        removed += 1
    elif r.status_code == 404:
        print(f"  {tpl_id:<10} {occ_id:<14} SKIP         not found (already removed)")
        skipped += 1
    else:
        print(f"  {tpl_id:<10} {occ_id:<14} ✗ FAILED     HTTP {r.status_code}: {r.text[:60]}")
        failed += 1
        errors.append((tpl_id, occ_id, r.status_code, r.text[:200]))

    time.sleep(0.3)

print(f"\n{'='*70}")
print(f"Results: {removed} removed | {skipped} already gone | {failed} failed")

if errors:
    print("\nFailed pairs:")
    for tpl, occ, code, txt in errors:
        print(f"  {tpl} → {occ}  HTTP {code}: {txt}")
else:
    print("\n✓ Done — run check_dq_links.py to verify FCBDQ-39 neighborhood.")
