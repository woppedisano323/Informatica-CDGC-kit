#!/usr/bin/env python3
"""
check_dq_links.py

PURPOSE: Confirm whether a DQ Rule Template (FCBDQ-*) and its corresponding
         DQ Rule Occurrence (FCBDQO-*) have a relationship link in CDGC.

USAGE:
  python3 check_dq_links.py
  → Enter credentials when prompted
  → Fetches FCBDQ-2 and FCBDQO-2 with segments=all
  → Prints neighborhood relationships for both
  → Answer: do the two assets know about each other?

WHEN TO USE:
  Before re-importing occurrences. Confirms whether template-to-occurrence
  links are missing (expected state after reboot wipe) or already present.

DO NOT USE:
  After running this to diagnose — then decide whether to re-import.
"""
import getpass, json, requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

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


def check_asset(ext_id):
    r = requests.get(
        f"{ORG_URL}/data360/search/v1/assets/{ext_id}?scheme=external&segments=all",
        headers=H, timeout=30)
    print(f"{'='*60}")
    print(f"Asset: {ext_id}  (HTTP {r.status_code})")
    if r.status_code != 200:
        print(f"  ERROR: {r.text[:200]}")
        return

    data = r.json()
    summary = data.get("summary", {})
    sys_attrs = data.get("systemAttributes", {})
    print(f"  Name:      {summary.get('core.name', '?')}")
    print(f"  ClassType: {sys_attrs.get('core.classType', '?')}")
    print(f"  Location:  {summary.get('core.location', '?')}")

    # selfAttributes — look for ICDQ ref and PDE
    self_attrs = data.get("selfAttributes", {})
    if self_attrs:
        for k in ("dq.primaryDataElement", "dq.icdqRuleRef", "dq.ruleTemplate",
                  "dq.ruleOccurrence", "core.externalId"):
            v = self_attrs.get(k)
            if v:
                print(f"  selfAttr [{k}]: {v}")

    # neighborhood — direct relationships
    neighborhood = data.get("neighborhood", [])
    if not neighborhood:
        print("  neighborhood: (empty — NO relationships)")
    else:
        print(f"  neighborhood ({len(neighborhood)} type group(s)):")
        for group in neighborhood:
            grp_type = group.get("type", "?")
            neighbors = group.get("neighbors", [])
            for n in neighbors:
                neighbor_name = n.get("neighbor", "?")
                paths = n.get("paths", [])
                for path in paths:
                    for col in path.get("collection", []):
                        assoc      = col.get("association", "?")
                        from_asset = col.get("from", "?")
                        to_asset   = col.get("to", "?")
                        from_type  = col.get("fromType", "?")
                        to_type    = col.get("toType", "?")
                        print(f"    [{grp_type}] {from_asset} --[{assoc}]--> {to_asset}")
                        print(f"      fromType: {from_type}")
                        print(f"      toType:   {to_type}")

    # customAttributes — dump all (small)
    custom = data.get("customAttributes", {})
    if custom:
        print(f"  customAttributes:")
        for k, v in custom.items():
            print(f"    {k}: {v}")

    print()


check_asset("FCBDQ-2")    # Template: SSN Format Validity
check_asset("FCBDQO-2")   # Occurrence: SSN Format Validity — CUSTOMER_MASTER.SSN
