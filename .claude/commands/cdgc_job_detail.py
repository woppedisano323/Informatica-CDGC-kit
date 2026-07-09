"""Fetch full job detail for failed import jobs."""
import requests
import getpass
import json

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

resp = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
resp.raise_for_status()
data = resp.json()
session_id = data["sessionId"]
org_id = data["orgId"]
resp = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": session_id},
    cookies={"USER_SESSION": session_id}, timeout=30)
resp.raise_for_status()
jwt = resp.json().get("token") or resp.json().get("jwt_token") or resp.json().get("access_token")
print(f"✓ Authenticated\n")

h = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id}

job_id = input("Job ID: ").strip()

r = requests.get(f"{ORG_URL}/data360/observable/v1/jobs/{job_id}", headers=h, timeout=30)
print(json.dumps(r.json(), indent=2))

for suffix in ["/errors", "/results", "/summary"]:
    r2 = requests.get(f"{ORG_URL}/data360/observable/v1/jobs/{job_id}{suffix}", headers=h, timeout=30)
    if r2.status_code == 200:
        print(f"\n── {suffix} ──────────────────────────")
        print(json.dumps(r2.json(), indent=2)[:2000])
