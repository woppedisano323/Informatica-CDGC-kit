#!/usr/bin/env python3
"""
cdgc_wipe.py — Delete all customer governance assets from a CDGC org.

Deletes ALL assets of every governance class type regardless of prefix.
The only assets intentionally skipped are BT- system terms created by MCC
Glossary Association — they are system-managed and cannot be deleted via API.

Safe to run on any org. No prefix knowledge required.

Usage:
  python3 ~/Documents/CDGC/cdgc_wipe.py
"""
import getpass
import sys
import time

import requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

# Deletion order: relationship sources must be deleted before relationship targets.
# 14_Relationships.xlsx creates: Policy→BusinessTerm, AISystem→AIModel, System→AIModel.
# If a "source" still exists when we delete its "target", the async delete is silently
# blocked by the live relationship edge — causing the classic "two-run" failure pattern.
#
# Rule: delete the asset that HOLDS the relationship first, then the asset it points to.
SEARCH_TYPES = [
    ("DQ Rule Templates", "com.infa.ccgf.models.governance.RuleTemplate"),
    ("Data Sets",         "com.infa.ccgf.models.governance.DataSet"),
    # Relationship sources — must come before their targets
    ("Policies",          "com.infa.ccgf.models.governance.Policy"),      # → Business Terms
    ("Regulations",       "com.infa.ccgf.models.governance.Regulation"),
    ("Business Areas",    "com.infa.ccgf.models.governance.BusinessArea"),
    ("Legal Entities",    "com.infa.ccgf.models.governance.LegalEntity"),
    ("Geographies",       "com.infa.ccgf.models.governance.Geography"),
    ("AI Systems",        "com.infa.ccgf.models.AIModel.AISystem"),       # → AI Models
    ("Systems",           "com.infa.ccgf.models.governance.System"),      # → AI Models
    # Relationship targets (safe to delete now that sources are gone)
    ("AI Models",         "com.infa.ccgf.models.AIModel.AIModel"),
    ("Business Terms",    "com.infa.ccgf.models.governance.BusinessTerm"),
    # Hierarchy — children before parents
    ("Subdomains",        "com.infa.ccgf.models.governance.Subdomain"),
    ("Domains",           "com.infa.ccgf.models.governance.Domain"),
]

# ── Auth ──────────────────────────────────────────────────────────────────────
print("""
╔══════════════════════════════════════════════════════════════════╗
║              ⚠  DESTRUCTIVE OPERATION — READ CAREFULLY           ║
╚══════════════════════════════════════════════════════════════════╝

This will permanently delete ALL governance assets in the org.
BT- system terms from MCC are skipped (cannot be deleted via API).
There is NO undo.

REQUIRED STEPS BEFORE RUNNING THIS SCRIPT:
  1. MCC → open catalog source → Purge Data
  2. MCC → delete the catalog source config
  Skipping these leaves column→term links intact which block
  Business Term deletion. Domains and Subdomains will also survive
  because their children cannot be removed.
""")

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
print(f"✓ Authenticated — org: {org_id}\n")

H_S = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id,
       "Content-Type": "application/json"}
H_D = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id}

# ── Helpers ───────────────────────────────────────────────────────────────────
def ext_id_of(item):
    return (item.get("core.externalId") or
            (item.get("summary") or {}).get("core.externalId", ""))

def name_of(item):
    return (item.get("summary") or {}).get("core.name", "?")

def search_all(class_type):
    """Fetch all assets of class_type. Skips BT- system terms for Business Terms."""
    results, offset = [], 0
    while True:
        for _ in range(3):
            r = requests.post(
                f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
                headers=H_S,
                json={"from": offset, "size": 100,
                      "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                      "values": [class_type]}]}, timeout=30)
            if r.status_code == 429:
                time.sleep(15)
                continue
            if not r.text.strip():
                time.sleep(3)
                continue
            try:
                hits = r.json().get("hits", [])
                break
            except Exception:
                time.sleep(3)
                hits = []
        else:
            break
        for h in hits:
            eid = ext_id_of(h)
            # Skip MCC-managed BT- system terms — cannot be deleted via API
            if eid.startswith("BT-"):
                continue
            results.append(h)
        if len(hits) < 100:
            break
        offset += 100
        time.sleep(0.2)
    return results

def delete_asset(ext_id):
    """DELETE by externalId. Treats timeout as 201 — verification scan is authoritative."""
    try:
        r = requests.delete(
            f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
            headers=H_D, timeout=60)
        if r.status_code == 429:
            time.sleep(15)
            r = requests.delete(
                f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
                headers=H_D, timeout=60)
        return r.status_code
    except requests.exceptions.Timeout:
        return 201  # assume processed

def delete_and_confirm(ext_id):
    sc = delete_asset(ext_id)
    return sc in (200, 201, 204, 404)

# ── Scan ──────────────────────────────────────────────────────────────────────
print("Scanning org for assets to delete...\n")

all_assets = {}
total = 0
for label, class_type in SEARCH_TYPES:
    hits = search_all(class_type)
    all_assets[label] = hits
    total += len(hits)
    print(f"  {label:<25}: {len(hits)}")

print(f"\n  Total assets found: {total}")

if total == 0:
    print("\n✓ Org is already clean — nothing to delete.")
    sys.exit(0)

confirm = input(f"\n⚠ Permanently delete all {total} assets?\n  Type CONFIRM to proceed: ")
if confirm.strip() != "CONFIRM":
    print("Cancelled.")
    sys.exit(0)

# ── Delete + auto-retry ───────────────────────────────────────────────────────
MAX_PASSES = 3

for pass_num in range(1, MAX_PASSES + 1):
    # Re-scan on pass 2+ (first pass uses the pre-confirm scan)
    if pass_num > 1:
        print(f"\n── Pass {pass_num}: re-scanning for remaining assets...\n")
        still_present = False
        for label, class_type in SEARCH_TYPES:
            hits = search_all(class_type)
            all_assets[label] = hits
            if hits:
                still_present = True
        if not still_present:
            break

    ok_count = fail_count = 0
    any_deleted = False

    for label, class_type in SEARCH_TYPES:
        hits = all_assets[label]
        if not hits:
            continue
        print(f"{label} ({len(hits)}):")
        for item in hits:
            eid  = ext_id_of(item)
            name = name_of(item)
            if not eid:
                print(f"  ✗ {name!r} — no externalId")
                fail_count += 1
                continue
            gone = delete_and_confirm(eid)
            if gone:
                print(f"  ✓ {name!r} ({eid})")
                ok_count += 1
                any_deleted = True
            else:
                print(f"  ✗ {name!r} ({eid}) — delete failed")
                fail_count += 1
        # Brief pause between groups so async deletes can propagate before
        # we move to assets that may have been relationship targets of this group
        time.sleep(3)

    print(f"\nPass {pass_num} — Deleted: {ok_count}  |  Failed: {fail_count}")

    if not any_deleted:
        break

    # Wait longer after each pass for async operations to settle
    wait = 10 * pass_num
    print(f"Waiting {wait}s for async deletes to settle...")
    time.sleep(wait)

# ── Verify ────────────────────────────────────────────────────────────────────
print("\nVerifying...\n")
time.sleep(10)

remaining = 0
for label, class_type in SEARCH_TYPES:
    hits = search_all(class_type)
    if hits:
        remaining += len(hits)
        for h in hits:
            print(f"  ✗ {label}: {ext_id_of(h)} ({name_of(h)}) — still present")
    else:
        print(f"  ✓ {label:<25}: 0")

print(f"\n  Assets remaining: {remaining}")
if remaining == 0:
    print("\n✓ Org is clean — ready for import.")
else:
    print(f"\n✗ {remaining} asset(s) remain after {MAX_PASSES} passes.")
    print("  If Business Terms remain: MCC purge + delete catalog source was likely skipped.")
    print("  Re-run after completing the MCC steps.")
