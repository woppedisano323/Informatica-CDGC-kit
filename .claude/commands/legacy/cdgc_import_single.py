#!/usr/bin/env python3
"""Import a single xlsx file into CDGC and poll for completion."""
import getpass, requests, time, json, sys
from pathlib import Path

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

fpath = Path(input("File path: ").strip().lstrip("File:").strip().replace("~", str(Path.home())))
if not fpath.exists():
    print(f"File not found: {fpath}")
    sys.exit(1)

username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

r = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
r.raise_for_status()
sid, oid = r.json()["sessionId"], r.json()["orgId"]
r2 = requests.get(f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": sid}, cookies={"USER_SESSION": sid}, timeout=30)
jwt = r2.json().get("token") or r2.json().get("jwt_token")
H  = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": oid}
print(f"✓ Authenticated\n")

print(f"Importing {fpath.name}...")
with open(fpath, "rb") as f:
    resp = requests.post(
        f"{ORG_URL}/data360/content/import/v1/assets",
        headers=H,
        files={
            "file": (fpath.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "config": (None, '{"validationPolicy":"CONTINUE_ON_ERROR_WARNING"}', "application/json"),
        },
        timeout=60)

if resp.status_code not in (200, 201, 202):
    print(f"Submit failed: HTTP {resp.status_code}: {resp.text[:300]}")
    sys.exit(1)

job_id = resp.json().get("jobId") or resp.json().get("id")
print(f"Job ID: {job_id}")

deadline = time.time() + 3600
dots = 0
terminal = {"COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED", "PARTIAL_SUCCESS"}
while time.time() < deadline:
    r3 = requests.get(f"{ORG_URL}/data360/observable/v1/jobs/{job_id}",
        headers={**H, "Content-Type": "application/json"}, timeout=30)
    data = r3.json()
    status = data.get("status", "UNKNOWN")
    if status in terminal:
        print(f"\r  {status}          ")
        if status != "COMPLETED":
            print(f"  Detail: {json.dumps(data.get('errors', data.get('detail', '')))[:500]}")
        break
    elapsed = int(time.time() - (deadline - 3600))
    print(f"\r  {status} ({elapsed}s){'.' * (dots % 4)}   ", end="", flush=True)
    dots += 1
    time.sleep(5)
