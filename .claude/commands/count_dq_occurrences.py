#!/usr/bin/env python3
"""
count_dq_occurrences.py

PURPOSE: Count how many DQ Rule Occurrences with a given reference ID prefix
         currently exist in CDGC.
         Uses classType: com.infa.ccgf.models.governance.RuleInstance

USAGE:
  python3 count_dq_occurrences.py

WHEN TO USE:
  Before triggering an MCC scan — confirms occurrences are present.
  After a delete/re-import cycle — verifies the import succeeded.
"""
import getpass, time, requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

RULE_INSTANCE_CLASS = "com.infa.ccgf.models.governance.RuleInstance"

OCC_PREFIX = input("Occurrence reference ID prefix (e.g. DQOCC): ").strip()

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

all_instances = []
offset = 0
while True:
    r3 = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
        headers=H,
        json={"from": offset, "size": 100,
              "filterSpec": [{"type": "simple", "attribute": "core.classType",
                              "values": [RULE_INSTANCE_CLASS]}]}, timeout=30)
    r3.raise_for_status()
    hits = r3.json().get("hits", [])
    total_api = r3.json().get("total", len(hits))
    for h in hits:
        s      = h.get("summary") or {}
        ext_id = h.get("core.externalId", "") or s.get("core.externalId", "")
        name   = s.get("core.name", "")
        all_instances.append({"ext_id": ext_id, "name": name})
    if len(hits) < 100:
        break
    offset += 100
    time.sleep(0.3)

prefix_filter = OCC_PREFIX + "-"
occ_list = [x for x in all_instances if x["ext_id"].startswith(prefix_filter)]

def _sort_key(x):
    parts = x["ext_id"].split("-")
    return int(parts[-1]) if parts[-1].isdigit() else 0

occ_list.sort(key=_sort_key)

print(f"Total RuleInstance assets in CDGC: {len(all_instances)}")
print(f"{OCC_PREFIX}-* occurrences: {len(occ_list)}\n")

if occ_list:
    print(f"{'Ref ID':<14} Name")
    print(f"{'-'*14} {'-'*50}")
    for x in occ_list:
        print(f"  {x['ext_id']:<12} {x['name'][:60]}")

    ids = [int(x["ext_id"].split("-")[-1]) for x in occ_list if x["ext_id"].split("-")[-1].isdigit()]
    if ids:
        expected = set(range(1, max(ids) + 1))
        found    = set(ids)
        missing  = sorted(expected - found)
        if missing:
            print(f"\nMissing IDs (gaps): {missing}")
        else:
            print(f"\nNo gaps — {OCC_PREFIX}-1 through {OCC_PREFIX}-{max(ids)} all present")

print(f"\n{'='*60}")
if len(occ_list) == 0:
    print(f"✗ No {OCC_PREFIX}-* occurrences found — re-import File 15 before MCC scan")
else:
    print(f"✓ {len(occ_list)} {OCC_PREFIX}-* occurrences found")
print(f"{'='*60}")
