#!/usr/bin/env python3
"""
fetch_icdq_rule_ids.py

Fetches ICDQ rule IDs from the IDMC File Repository Service (FRS).
The artifact ID = Technical Rule Reference value for 13_DQ_Rule_Template.xlsx.

Confirmed from browser Network tab:
  Host:  <frs-host>.dmp-us.informaticacloud.com  (standard IDMC platform — JWT works)
  API:   /frs/api/v1/  (OData-style)
  Example: GET /frs/api/v1/GetPermission(artifactId='8aEIEW3YLAvdZaCF1opXmH')

Usage:
  python3 fetch_icdq_rule_ids.py
  python3 fetch_icdq_rule_ids.py --csv
"""
import argparse
import csv
import getpass
import json
import requests

LOGIN_URL = "https://dmp-us.informaticacloud.com"

parser = argparse.ArgumentParser()
parser.add_argument("--csv", action="store_true", help="Write results to icdq_rules.csv")
args = parser.parse_args()

# ── Auth ──────────────────────────────────────────────────────────────────────
username = input("IDMC Username: ").strip()
password = getpass.getpass("IDMC Password: ")

r = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
r.raise_for_status()
data = r.json()
sid, oid = data["sessionId"], data["orgId"]

r2 = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": sid}, cookies={"USER_SESSION": sid}, timeout=30)
jwt = r2.json().get("token") or r2.json().get("jwt_token")
print("✓ Authenticated\n")

H = {"IDS-SESSION-ID": sid, "Accept": "application/json"}

# ── Prompts ───────────────────────────────────────────────────────────────────
frs_host     = input("FRS host (e.g. usw1.dmp-us.informaticacloud.com): ").strip()
FRS_BASE     = f"https://{frs_host}/frs/api/v1"
PROJECT_NAME = input("ICDQ project name: ").strip()
FOLDER_NAME  = input("ICDQ folder name: ").strip()

# ── Step 1: Find the project ──────────────────────────────────────────────────
resp = requests.get(f"{FRS_BASE}/Projects", headers=H, timeout=15)
resp.raise_for_status()
projects = resp.json().get("value", [])
project = next((p for p in projects if p.get("name") == PROJECT_NAME), None)
if not project:
    print(f"Project '{PROJECT_NAME}' not found. Available projects:")
    for p in projects:
        print(f"  {p.get('name')}  ({p.get('id')})")
    raise SystemExit(1)
project_id = project["id"]
print(f"✓ Project found: {PROJECT_NAME}  id={project_id}\n")

# ── Step 2: Find the folder — try navigation then full list ───────────────────
folder_id = None
for url in [
    f"{FRS_BASE}/Projects('{project_id}')/Folders?$top=200",
    f"{FRS_BASE}/Folders?$top=500",
]:
    resp = requests.get(url, headers=H, timeout=15)
    if resp.status_code != 200:
        print(f"  {resp.status_code} {url} — skipping")
        continue
    folders = resp.json().get("value", [])
    folder = next((f for f in folders if f.get("name") == FOLDER_NAME), None)
    if folder:
        folder_id = folder["id"]
        print(f"✓ Folder found: {FOLDER_NAME}  id={folder_id}\n")
        break
    else:
        print(f"  Folder '{FOLDER_NAME}' not in response from {url}")
        print(f"  Available: {[f.get('name') for f in folders[:20]]}\n")

if not folder_id:
    raise SystemExit(f"Could not locate folder '{FOLDER_NAME}'")

# ── Step 3: Fetch all BaseEntities in that folder ─────────────────────────────
attempts = [
    ("GET", f"{FRS_BASE}/BaseEntities?$filter=folderId eq '{folder_id}'&$top=200", None),
    ("GET", f"{FRS_BASE}/BaseEntities?$filter=folder/id eq '{folder_id}'&$top=200", None),
    ("GET", f"{FRS_BASE}/Folders('{folder_id}')/BaseEntities?$top=200", None),
]

rules = []

for method, url, body in attempts:
    try:
        if method == "POST":
            resp = requests.post(url, headers={**H, "Content-Type": "application/json"},
                                 json=body, timeout=15)
        else:
            resp = requests.get(url, headers=H, timeout=15)

        ct  = resp.headers.get("Content-Type", "")
        raw = resp.text[:300].strip()
        is_html = "text/html" in ct or raw.startswith("<!DOCTYPE") or raw.startswith("<html")

        print(f"  {resp.status_code} [{method}]  {url}")
        if is_html:
            print(f"    → HTML redirect\n")
            continue

        print(f"    Content-Type: {ct}")
        print(f"    Body: {raw[:200]!r}\n")

        if resp.status_code == 200:
            try:
                rbody = resp.json()
                items = (rbody.get("value") or rbody.get("items") or
                         rbody.get("data") or rbody.get("content") or
                         (rbody if isinstance(rbody, list) else None))
                if items and isinstance(items, list):
                    print(f"    ✓ {len(items)} items!")
                    # If this is the service root listing, print all resource names and continue
                    if url.endswith("/frs/api/v1/") and all("url" in i for i in items[:3]):
                        print(f"    Resources: {[i.get('name') for i in items]}\n")
                        continue
                    for item in items:
                        name  = item.get("name") or item.get("displayName") or ""
                        aid   = item.get("id") or item.get("uuid") or ""
                        if aid and name:
                            rules.append({"name": name, "id": aid})
                    if rules:
                        break
                else:
                    print(f"    keys: {list(rbody.keys())[:10] if isinstance(rbody, dict) else type(rbody)}")
            except Exception as e:
                print(f"    parse error: {e}")

    except Exception as e:
        print(f"  ! {url}: {e}\n")

# ── Results ───────────────────────────────────────────────────────────────────
display = sorted(rules, key=lambda x: x["name"])

if display:
    print(f"\n{'─'*90}")
    print(f"  {'Name':<55} {'ID (Technical Rule Reference)'}")
    print(f"{'─'*90}")
    for rule in display:
        print(f"  {rule['name']:<55} {rule['id']}")
    print(f"{'─'*90}")
    print(f"\n  Total: {len(display)} rules")

    if args.csv:
        with open("icdq_rules.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Name", "ID"])
            for rule in display:
                w.writerow([rule["name"], rule["id"]])
        print("✓ Written to icdq_rules.csv")
else:
    print("\n  No rules found. Raw response above shows what the FRS returned.")
    print("  If you see 401/403: JWT is not accepted by this FRS endpoint — need session cookie.")
    print("  If you see 200 with HTML: endpoint exists but redirects to login.")
