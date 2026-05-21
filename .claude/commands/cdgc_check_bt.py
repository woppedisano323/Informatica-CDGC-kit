import requests, getpass, json

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

resp = requests.post(f"{LOGIN_URL}/identity-service/api/v1/Login",
    json={"username": username, "password": password}, timeout=30)
data = resp.json()
session_id = data["sessionId"]
org_id = data["orgId"]
resp = requests.get(
    f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
    headers={"IDS-SESSION-ID": session_id},
    cookies={"USER_SESSION": session_id}, timeout=30)
jwt = resp.json().get("token") or resp.json().get("jwt_token") or resp.json().get("access_token")
print(f"✓ Authenticated\n")

h = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id, "Content-Type": "application/json"}

resp = requests.post(
    f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
    headers=h,
    json={"from": 0, "size": 5,
          "filterSpec": [{"type": "simple", "attribute": "core.classType",
                          "values": ["com.infa.ccgf.models.governance.BusinessTerm"]}]},
    timeout=30)

hits = resp.json().get("hits", [])
print(f"First 5 Business Terms — raw keys and externalId:\n")
for hit in hits:
    print(f"  Keys: {list(hit.keys())}")
    print(f"  core.externalId: {hit.get('core.externalId', 'MISSING')}")
    print(f"  core.identity:   {hit.get('core.identity', 'MISSING')}")
    print(f"  name:            {(hit.get('summary') or {}).get('core.name', '?')}")
    print()
