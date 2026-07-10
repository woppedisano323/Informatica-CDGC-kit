#!/usr/bin/env python3
"""
link_dq_templates_to_occurrences.py

PURPOSE
-------
Creates the Rule Template → Rule Occurrence relationship for all 77 FCB Financial
DQ rule pairs (FCBDQ-1..77 → FCBDQO-1..77) via the CDGC REST API.

BACKGROUND
----------
DQ Rule Occurrences (RuleInstance assets) must be linked to their parent DQ Rule
Template (RuleTemplate assets) so CDGC can display the "Rule Template" field on
each occurrence and associate scoring results correctly.

When CDGC automation is enabled on a template (Enable Automation = TRUE), it creates
this link automatically. However, the 77 FCB occurrences were created via bulk import
(File 15), which bypasses automation — so the link was never established.

The Bulk Import template has no "Rule Template" column on the DQ Rule Occurrence sheet,
and the Relationships Annexure has no RuleTemplate→RuleInstance entry, confirming
there is no import-based mechanism for this relationship. It must be set via API.

RELATIONSHIP TYPE
-----------------
  com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance
  Direction: RuleTemplate (FCBDQ-N) ──→ RuleInstance (FCBDQO-N)

API ENDPOINT
------------
  PATCH /data360/content/v1/assets/{templateExternalId}?scheme=external
  Body:
    [{"operation": "add", "segment": "relationship",
      "items": [{"fromExternalIdentity": "FCBDQ-N",
                 "toExternalIdentity": "FCBDQO-N",
                 "association": "<relationship type>"}]}]
  Reference: CDGC API Reference (April 2026), Chapter 4 — Manage assets,
             Update assets > Create relationship example (page 55)

USAGE
-----
  python3 link_dq_templates_to_occurrences.py

  Prompts for IDMC username and password. No other arguments needed.

BEHAVIOR
--------
  - For each pair FCBDQ-N / FCBDQO-N (N = 1..77):
      1. Checks the template's neighborhood via GET segments=all
      2. Skips the pair if the relatedRuleTemplateRuleInstance link already exists
      3. Issues PATCH to create the link if missing
  - Reports linked / skipped / failed counts at the end
  - Lists any failed pairs with HTTP status and response for diagnosis

NOTES
-----
  - FCBDQ-N and FCBDQO-N numbers are 1:1 (same N = same rule, same index)
  - Safe to re-run: already-linked pairs are skipped, not duplicated
  - After completion, verify with: python3 check_dq_links.py
  - Future: this step will be folded into cdgc_create_dq_occurrences.py as Phase 3
"""
import getpass, time, requests, json

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

ASSOC_TYPE = "com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance"

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


def get_neighborhood(ext_id):
    r = requests.get(
        f"{ORG_URL}/data360/search/v1/assets/{ext_id}?scheme=external&segments=all",
        headers=H, timeout=30)
    if r.status_code == 200:
        return r.json().get("neighborhood", []) or []
    return None


def already_linked(template_id, occurrence_id):
    neighborhood = get_neighborhood(template_id)
    if neighborhood is None:
        return False
    for group in neighborhood:
        grp_type = group.get("type", "")
        if "RuleInstance" in grp_type:
            for n in (group.get("neighbors", []) or []):
                for path in (n.get("paths", []) or []):
                    for col in (path.get("collection") or []):
                        if col.get("association") == ASSOC_TYPE:
                            to_val = col.get("to", "")
                            if occurrence_id.split("-")[1] in to_val or occurrence_id in to_val:
                                return True
    return False


def create_link(template_ext_id, occurrence_ext_id):
    """
    PATCH /data360/content/v1/assets/{id}?scheme=external
    Body: array with operation=add, segment=relationship, items with fromExternalIdentity/toExternalIdentity/association
    (API Reference Chapter 4, Update assets, Create relationship example)
    """
    url = f"{ORG_URL}/data360/content/v1/assets/{template_ext_id}?scheme=external"
    body = [{
        "operation": "add",
        "segment": "relationship",
        "items": [{
            "fromExternalIdentity": template_ext_id,
            "toExternalIdentity": occurrence_ext_id,
            "association": ASSOC_TYPE
        }]
    }]
    r = requests.patch(url, headers=H, json=body, timeout=30)
    return r.status_code, r.text


# ── Main loop: FCBDQ-1 through FCBDQ-77 ──────────────────────────────────────
print(f"Linking FCBDQ-N → FCBDQO-N for N=1..77\n")
print(f"{'ID':<12} {'Status':<12} Detail")
print("-" * 70)

linked   = 0
skipped  = 0
failed   = 0
errors   = []

for n in range(1, 78):
    tpl_id = f"FCBDQ-{n}"
    occ_id = f"FCBDQO-{n}"

    # Check if already linked
    if already_linked(tpl_id, occ_id):
        print(f"  {tpl_id:<10} SKIP         already linked")
        skipped += 1
        time.sleep(0.2)
        continue

    # Create the link
    status_code, resp_text = create_link(tpl_id, occ_id)

    if status_code in (200, 201, 204):
        print(f"  {tpl_id:<10} ✓ LINKED")
        linked += 1
    elif status_code == 409:
        print(f"  {tpl_id:<10} SKIP         already linked (409)")
        skipped += 1
    else:
        print(f"  {tpl_id:<10} ✗ FAILED     HTTP {status_code}: {resp_text[:80]}")
        failed += 1
        errors.append((tpl_id, occ_id, status_code, resp_text[:200]))

    time.sleep(0.3)

print(f"\n{'='*70}")
print(f"Results: {linked} linked | {skipped} already linked | {failed} failed")

if errors:
    print("\nFailed pairs:")
    for tpl, occ, code, txt in errors:
        print(f"  {tpl} → {occ}  HTTP {code}: {txt}")
    print("\nIf all failed with 4xx, the association endpoint may need a different format.")
    print("Run check_dq_links.py on a failed pair to confirm current state.")
else:
    print("\n✓ All pairs processed — run check_dq_links.py to verify FCBDQ-2/FCBDQO-2.")
