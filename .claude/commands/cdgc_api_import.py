import requests
import getpass
import time
import sys
import json
from pathlib import Path

import argparse
import glob

LOGIN_URL  = "https://dmp-us.informaticacloud.com"
ORG_URL    = "https://idmc-api.dmp-us.informaticacloud.com"

def _resolve_import_dir(arg):
    """Resolve import dir: use arg if given, else find newest CDGC_Import_* folder."""
    if arg:
        return Path(arg).expanduser()
    candidates = sorted(
        glob.glob(str(Path.home() / "Downloads/CDGC_Import_*")),
        key=lambda p: Path(p).stat().st_mtime, reverse=True)
    if candidates:
        return Path(candidates[0])
    return Path.home() / "Downloads"

FILES_IN_ORDER = [
    "01_Domain.xlsx",
    "02_Subdomain.xlsx",
    "03_Regulation.xlsx",
    "04_Policy.xlsx",
    "05_Legal_Entity.xlsx",
    "06_Business_Area.xlsx",
    "07_Geography.xlsx",
    "08_System.xlsx",
    "09_AI_System.xlsx",
    "10_AI_Model.xlsx",
    "11_Business_Term.xlsx",
    "12_Data_Set.xlsx",
    "13_DQ_Rule_Template.xlsx",
    "14_Relationships.xlsx",
]

def authenticate(username, password):
    resp = requests.post(
        f"{LOGIN_URL}/identity-service/api/v1/Login",
        json={"username": username, "password": password},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["sessionId"]
    org_id = data["orgId"]

    resp = requests.get(
        f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
        headers={"IDS-SESSION-ID": session_id},
        cookies={"USER_SESSION": session_id},
        timeout=30
    )
    resp.raise_for_status()
    token_data = resp.json()
    jwt_token = token_data.get("token") or token_data.get("jwt_token") or token_data.get("access_token")
    print(f"  ✓ Authenticated — orgId: {org_id}")
    return jwt_token, org_id

def import_file(jwt_token, org_id, filepath):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-INFA-ORG-ID": org_id,
    }
    with open(filepath, "rb") as f:
        files = {
            "file": (filepath.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "config": (None, '{"validationPolicy":"CONTINUE_ON_ERROR_WARNING"}', "application/json"),
        }
        resp = requests.post(
            f"{ORG_URL}/data360/content/import/v1/assets",
            headers=headers,
            files=files,
            timeout=60)
    if resp.status_code == 401:
        return None, "401"
    if not resp.text.strip():
        return None, "Empty response from import endpoint"
    try:
        data = resp.json()
    except Exception:
        return None, f"Invalid response: {resp.text[:200]}"
    if resp.status_code not in (200, 201, 202):
        return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
    job_id = data.get("jobId") or data.get("id")
    if job_id:
        return job_id, None
    return None, f"No jobId in response: {resp.text[:300]}"

def poll_job(jwt_token, org_id, job_id, filename):
    url = f"{ORG_URL}/data360/observable/v1/jobs/{job_id}"
    headers = {"Authorization": f"Bearer {jwt_token}", "X-INFA-ORG-ID": org_id}
    terminal = {"COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED", "PARTIAL_SUCCESS"}
    dots = 0
    for attempt in range(72):  # max 6 minutes (72 x 5s)
        try:
            resp = requests.get(url, headers=headers, timeout=30)
        except requests.exceptions.RequestException:
            time.sleep(5)
            continue
        if resp.status_code in (429, 502, 503, 504):
            time.sleep(10)
            continue
        if not resp.text.strip():
            time.sleep(5)
            continue
        try:
            data = resp.json()
        except Exception:
            time.sleep(5)
            continue
        status = data.get("status", "UNKNOWN")
        if status in terminal:
            print(f"\r  [{filename}] {status}          ")
            if status in ("COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED", "PARTIAL_SUCCESS"):
                print(f"  ⚠ Detail: {json.dumps(data.get('errors', data.get('detail', '')))[:300]}")
            return status, data
        print(f"\r  [{filename}] {status}{'.' * (dots % 4)}   ", end="", flush=True)
        dots += 1
        time.sleep(5)
    print(f"\r  [{filename}] TIMEOUT — job did not complete in 6 minutes")
    return "TIMEOUT", {}

# ── Main ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="CDGC API Import")
parser.add_argument("--dir", help="Import directory (default: newest ~/Downloads/CDGC_Import_* folder)")
args = parser.parse_args()
IMPORT_DIR = _resolve_import_dir(args.dir)

print("\nCDGC API Import")
print("───────────────────────────────────────────")
print(f"Import dir: {IMPORT_DIR}")
username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

print("\nAuthenticating...")
jwt_token, org_id = authenticate(username, password)

results = []
for fname in FILES_IN_ORDER:
    fpath = IMPORT_DIR / fname
    if not fpath.exists():
        print(f"\nSKIP — file not found: {fpath}")
        results.append((fname, "SKIPPED"))
        continue

    print(f"\nImporting {fname}...")
    job_id, err = import_file(jwt_token, org_id, fpath)

    if err == "401":
        print("  Token expired — re-authenticating...")
        jwt_token, org_id = authenticate(username, password)
        job_id, err = import_file(jwt_token, org_id, fpath)

    if err:
        print(f"  FAILED to submit: {err}")
        results.append((fname, "SUBMIT_FAILED"))
        print(f"\nFATAL — stopping import. Fix {fname} and retry.")
        sys.exit(1)

    status, detail = poll_job(jwt_token, org_id, job_id, fname)
    results.append((fname, status))

    if status in ("FAILED", "TIMEOUT"):
        print(f"\nFATAL — {fname} {status}. Stopping import (downstream files depend on this one).")
        print(json.dumps(detail)[:500])
        sys.exit(1)

print("\n── Import Summary ──────────────────────────────────────────")
for fname, status in results:
    icon = "✓" if status == "COMPLETED" else "⚠" if status == "COMPLETED_WITH_ERRORS" else "✗"
    print(f"  {icon}  {fname:<45} {status}")
print("────────────────────────────────────────────────────────────")

# ── Verification scan — reuses existing session ───────────────────────────────
print("\nVerifying assets in org...\n")
time.sleep(3)

VERIFY_TYPES = [
    ("Domains",           "com.infa.ccgf.models.governance.Domain"),
    ("Subdomains",        "com.infa.ccgf.models.governance.Subdomain"),
    ("Regulations",       "com.infa.ccgf.models.governance.Regulation"),
    ("Policies",          "com.infa.ccgf.models.governance.Policy"),
    ("Legal Entities",    "com.infa.ccgf.models.governance.LegalEntity"),
    ("Business Areas",    "com.infa.ccgf.models.governance.BusinessArea"),
    ("Geographies",       "com.infa.ccgf.models.governance.Geography"),
    ("Systems",           "com.infa.ccgf.models.governance.System"),
    ("AI Systems",        "com.infa.ccgf.models.governance.AISystem"),
    ("AI Models",         "com.infa.ccgf.models.governance.AIModel"),
    ("Business Terms",    "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Data Sets",         "com.infa.ccgf.models.governance.DataSet"),
    ("DQ Rule Templates", "com.infa.ccgf.models.governance.RuleTemplate"),
]

h_s = {"Authorization": f"Bearer {jwt_token}", "X-INFA-ORG-ID": org_id, "Content-Type": "application/json"}
grand_total = 0
for label, ct in VERIFY_TYPES:
    for attempt in range(3):
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=h_s,
            json={"from": 0, "size": 0,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType", "values": [ct]}]},
            timeout=30)
        if not r.text.strip():
            time.sleep(2)
            continue
        try:
            body = r.json()
            count = body.get("total", body.get("totalHits", len(body.get("hits", []))))
            break
        except Exception:
            time.sleep(2)
            continue
    else:
        count = "?"
    grand_total += count if isinstance(count, int) else 0
    icon = "✓" if isinstance(count, int) and count > 0 else "⚠"
    print(f"  {icon}  {label:<25}: {count}")
    time.sleep(0.3)

print(f"\n  Total assets in org: {grand_total}")
print("────────────────────────────────────────────────────────────\n")
