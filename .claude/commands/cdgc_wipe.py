#!/usr/bin/env python3
"""
cdgc_wipe.py — Delete all customer governance assets from a CDGC org.

Only deletes assets whose externalId starts with the customer prefix (e.g. FCB).
BT- system terms created by MCC Glossary Association are intentionally ignored —
they cannot be deleted via the content API and are harmless to the reimport.

Usage:
  python3 ~/Documents/CDGC/cdgc_wipe.py
"""
import getpass
import sys
import time

import requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

# Deletion order matters — children before parents
SEARCH_TYPES = [
    ("DQ Rule Templates", "com.infa.ccgf.models.governance.RuleTemplate"),
    ("Business Terms",    "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Data Sets",         "com.infa.ccgf.models.governance.DataSet"),
    ("AI Models",         "com.infa.ccgf.models.AIModel.AIModel"),
    ("AI Systems",        "com.infa.ccgf.models.AIModel.AISystem"),
    ("Systems",           "com.infa.ccgf.models.governance.System"),
    ("Business Areas",    "com.infa.ccgf.models.governance.BusinessArea"),
    ("Legal Entities",    "com.infa.ccgf.models.governance.LegalEntity"),
    ("Geographies",       "com.infa.ccgf.models.governance.Geography"),
    ("Policies",          "com.infa.ccgf.models.governance.Policy"),
    ("Regulations",       "com.infa.ccgf.models.governance.Regulation"),
    ("Subdomains",        "com.infa.ccgf.models.governance.Subdomain"),
    ("Domains",           "com.infa.ccgf.models.governance.Domain"),
]

# ── Auth ──────────────────────────────────────────────────────────────────────
print("""
╔══════════════════════════════════════════════════════════════════╗
║              ⚠  DESTRUCTIVE OPERATION — READ CAREFULLY           ║
╚══════════════════════════════════════════════════════════════════╝

This will permanently delete all customer governance assets.
BT- system terms from MCC are skipped (cannot be deleted via API).
There is NO undo.
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
print("✓ Authenticated\n")

H_S = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id,
       "Content-Type": "application/json"}
H_D = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id}

# ── Helpers ───────────────────────────────────────────────────────────────────
def ext_id_of(item):
    return (item.get("core.externalId") or
            (item.get("summary") or {}).get("core.externalId", ""))

def name_of(item):
    return (item.get("summary") or {}).get("core.name", "?")

def search_customer(class_type, prefix, filter_prefix=True):
    """Fetch assets of class_type. If filter_prefix=False, return all regardless of prefix."""
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
            if not filter_prefix or eid.startswith(prefix):
                results.append(h)
        if len(hits) < 100:
            break
        offset += 100
        time.sleep(0.2)
    return results

def delete_asset(ext_id):
    """DELETE by externalId. Returns status code."""
    r = requests.delete(
        f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
        headers=H_D, timeout=30)
    if r.status_code == 429:
        time.sleep(15)
        r = requests.delete(
            f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
            headers=H_D, timeout=30)
    return r.status_code

def delete_and_confirm(ext_id, retries=3, delay=2):
    """
    Delete an asset and confirm it's gone via GET.
    FCB-prefixed assets use scheme=external; BT- system IDs use scheme=internal.
    Returns True only when GET returns 404.
    """
    delete_asset(ext_id)
    scheme = "external" if ext_id.startswith(customer_prefix) else "internal"
    confirm_url = (f"{ORG_URL}/data360/content/v1/assets/{ext_id}"
                   f"?scheme={scheme}&segments=summary")
    for attempt in range(retries):
        time.sleep(delay)
        r = requests.get(confirm_url, headers=H_S, timeout=30)
        if r.status_code == 404:
            return True
        delete_asset(ext_id)
    return False

# ── Auto-detect prefix ────────────────────────────────────────────────────────
def detect_prefix():
    r = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
        headers=H_S,
        json={"from": 0, "size": 1,
              "filterSpec": [{"type": "simple", "attribute": "core.classType",
                              "values": ["com.infa.ccgf.models.governance.Domain"]}]},
        timeout=30)
    if r.status_code != 200:
        return None
    hits = r.json().get("hits", [])
    for h in hits:
        eid = ext_id_of(h)
        if "DOM" in eid:
            return eid.split("DOM")[0]
    return None

customer_prefix = detect_prefix()
if customer_prefix:
    print(f"Auto-detected prefix: {customer_prefix}")
    override = input(f"Press Enter to confirm or type a different prefix: ").strip().upper()
    if override:
        customer_prefix = override
else:
    customer_prefix = input("Could not auto-detect prefix — enter manually (e.g. RKF, FCB): ").strip().upper()
print(f"Using prefix: {customer_prefix}\n")

# ── Scan ──────────────────────────────────────────────────────────────────────
print("Scanning org for customer assets...\n")

# AI Models/Systems: probe by sequential externalId (classType search broken on suborg)
print("  Probing AI Models and AI Systems by externalId...")
for suffix, label in [("AIM", "AI Model"), ("AIS", "AI System")]:
    found = 0
    for i in range(1, 201):
        ext_id = f"{customer_prefix}{suffix}-{i}"
        sc = delete_asset(ext_id)
        if sc == 404:
            break
        if sc in (200, 201, 204):
            found += 1
        time.sleep(0.2)
    print(f"  {label+'s':<25}: {found} deleted during probe")

# Business Terms use system-assigned BT- prefix (not customer prefix) — fetch all
NO_PREFIX_TYPES = {"Business Terms"}

# All other types
all_customer = {}
total = 0
for label, class_type in SEARCH_TYPES:
    use_prefix = label not in NO_PREFIX_TYPES
    hits = search_customer(class_type, customer_prefix, filter_prefix=use_prefix)
    all_customer[label] = hits
    total += len(hits)
    print(f"  {label:<25}: {len(hits)}")
    time.sleep(0.3)

print(f"\n  Total customer assets: {total}")

if total == 0:
    print("\n✓ Org is already clean — nothing to delete.")
    sys.exit(0)

confirm = input(f"\n⚠ Permanently delete all {total} customer assets?\n  Type CONFIRM to proceed: ")
if confirm.strip() != "CONFIRM":
    print("Cancelled.")
    sys.exit(0)

# ── Delete pass — with confirmation ──────────────────────────────────────────
print()
ok_count = fail_count = 0

for label, class_type in SEARCH_TYPES:
    hits = all_customer[label]
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
        else:
            # One more hard delete attempt before giving up
            delete_asset(eid)
            time.sleep(8)
            r = requests.get(
                f"{ORG_URL}/data360/content/v1/assets/{eid}?scheme=external&segments=summary",
                headers=H_S, timeout=30)
            if r.status_code == 404:
                print(f"  ✓ {name!r} ({eid})  (confirmed on retry)")
                ok_count += 1
            else:
                print(f"  ✗ {name!r} ({eid}) — still present after retries")
                fail_count += 1

print(f"\nDeleted: {ok_count}  |  Failed: {fail_count}")

# ── Final verification — customer assets only ─────────────────────────────────
print("\nVerifying...\n")
time.sleep(5)

remaining = 0
for label, class_type in SEARCH_TYPES:
    use_prefix = label not in NO_PREFIX_TYPES
    hits = search_customer(class_type, customer_prefix, filter_prefix=use_prefix)
    if hits:
        remaining += len(hits)
        for h in hits:
            print(f"  ✗ {label}: {ext_id_of(h)} ({name_of(h)}) — still present")
    else:
        print(f"  ✓ {label:<25}: 0")

print(f"\n  Customer assets remaining: {remaining}")
if remaining == 0:
    print("\n✓ Org is clean — ready for import.")
else:
    print(f"\n✗ {remaining} customer asset(s) remain.")
    print("  Re-run the script or delete manually in the CDGC UI.")
    print("  (BT- system terms from MCC are normal and excluded from this count.)")
