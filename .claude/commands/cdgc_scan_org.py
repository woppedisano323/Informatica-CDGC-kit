#!/usr/bin/env python3
"""
cdgc_scan_org.py — Read-only scan. Shows every asset in the org by type.
No deletes. Use to understand exactly what's present before any wipe.
"""
import getpass
import time
import requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

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
print(f"\n✓ Authenticated — org: {org_id}\n")

H = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id,
     "Content-Type": "application/json"}

grand_total = 0

for label, class_type in SEARCH_TYPES:
    results, offset = [], 0
    while True:
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=H,
            json={"from": offset, "size": 100,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType",
                                  "values": [class_type]}]}, timeout=30)
        hits = r.json().get("hits", [])
        results.extend(hits)
        if len(hits) < 100:
            break
        offset += 100
        time.sleep(0.2)

    grand_total += len(results)
    if results:
        print(f"{'─'*60}")
        print(f"{label} ({len(results)} total)")
        for h in results:
            s   = h.get("summary") or {}
            eid = h.get("core.externalId") or s.get("core.externalId", "—")
            nm  = h.get("core.name") or s.get("core.name", "?")
            print(f"  {eid:<20} {nm}")
    else:
        print(f"{label:<25}: 0")

print(f"\n{'═'*60}")
print(f"TOTAL assets in org: {grand_total}")
