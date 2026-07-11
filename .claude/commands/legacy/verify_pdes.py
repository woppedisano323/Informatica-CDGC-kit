#!/usr/bin/env python3
"""Verify that every PDE in 15_DQ_Rule_Occurrence.xlsx exists as a scanned column in CDGC."""
import getpass, time, requests, openpyxl
from pathlib import Path

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"
COLUMN_CLASS = "com.infa.odin.models.relational.Column"

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
print("✓ Auth OK\n")

# Fetch all scanned columns — build set of valid PDE paths
print("Fetching all scanned columns from CDGC...")
catalog_name = None
all_pdes = set()
offset = 0
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
        s = h.get("summary") or {}
        loc = s.get("core.location", "")
        if not loc:
            continue
        # Resolve catalog name once
        if catalog_name is None and "://" in loc:
            uuid = loc.split("://")[0]
            r4 = requests.get(f"{ORG_URL}/data360/search/v1/assets/{uuid}?scheme=internal&segments=summary",
                headers=H, timeout=30)
            if r4.status_code == 200:
                catalog_name = (r4.json().get("summary") or {}).get("core.name", uuid)
        if catalog_name and "://" in loc:
            after = loc.split("://", 1)[1]
            path = after[after.find("/")+1:]  # strip leading UUID segment
            if path:
                all_pdes.add(f"{catalog_name}://{path}")
    if len(hits) < 100:
        break
    offset += 100
    time.sleep(0.2)

print(f"  {len(all_pdes)} column PDEs in catalog")
print(f"  Catalog source name: {catalog_name}\n")

# Load occurrence file and check each PDE
occ_file = Path.home() / "Downloads/CDGC_Import_FirstCapitalBank/15_DQ_Rule_Occurrence.xlsx"
wb = openpyxl.load_workbook(occ_file)
ws = wb.active
hdrs = [c.value for c in ws[1]]
pde_idx  = hdrs.index("Primary Data Element")
ref_idx  = hdrs.index("Reference ID")

missing = []
matched = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if not any(row):
        continue
    ref = row[ref_idx]
    pde = str(row[pde_idx] or "")
    if pde in all_pdes:
        matched.append((ref, pde))
    else:
        missing.append((ref, pde))

print(f"MATCHED ({len(matched)}):")
for ref, pde in matched[:5]:
    print(f"  ✓ {ref:<12} {pde}")
if len(matched) > 5:
    print(f"  ... and {len(matched)-5} more")

print(f"\nMISSING from catalog ({len(missing)}):")
for ref, pde in missing:
    print(f"  ✗ {ref:<12} {pde}")
