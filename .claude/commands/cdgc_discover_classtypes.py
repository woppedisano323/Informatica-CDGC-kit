import requests, getpass, json, time
from collections import Counter

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

KNOWN_TYPES = [
    ("Domain",        "com.infa.ccgf.models.governance.Domain"),
    ("Subdomain",     "com.infa.ccgf.models.governance.Subdomain"),
    ("BusinessTerm",  "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Policy",        "com.infa.ccgf.models.governance.Policy"),
    ("Regulation",    "com.infa.ccgf.models.governance.Regulation"),
    ("System",        "com.infa.ccgf.models.governance.System"),
    ("DataSet",       "com.infa.ccgf.models.governance.DataSet"),
    ("RuleTemplate",  "com.infa.ccgf.models.governance.RuleTemplate"),
    ("BusinessArea",  "com.infa.ccgf.models.governance.BusinessArea"),
    ("LegalEntity",   "com.infa.ccgf.models.governance.LegalEntity"),
    ("Geography",     "com.infa.ccgf.models.governance.Geography"),
    ("AIModel",       "com.infa.ccgf.models.AIModel.AIModel"),
    ("AISystem",      "com.infa.ccgf.models.AIModel.AISystem"),
]

print(f"{'Asset Type':<20} {'API Count':>10}  ExternalIds")
print("-" * 60)
for label, ct in KNOWN_TYPES:
    r = requests.post(
        f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
        headers=h,
        json={"from": 0, "size": 100,
              "filterSpec": [{"type": "simple", "attribute": "core.classType", "values": [ct]}]},
        timeout=30)
    if not r.text.strip():
        print(f"  {label:<20}: empty response")
        time.sleep(1)
        continue
    body = r.json()
    hits = body.get("hits", [])
    total = body.get("total", len(hits))
    ids = [h2.get("core.externalId", "?") for h2 in hits]
    print(f"  {label:<20}: {total:>4}   {ids}")
    time.sleep(0.3)

# ── Raw knowledgeQuery for DQ Rule Occurrences (no classType filter) ──────────
print("\n" + "-" * 60)
print("Searching for FCBDQO-* occurrences via knowledgeQuery...")
r = requests.post(
    f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=FCBDQO&segments=summary",
    headers=h,
    json={"from": 0, "size": 100},
    timeout=30)
hits = r.json().get("hits", [])
total = r.json().get("total", len(hits))
print(f"  Total found: {total}")
for hit in hits[:5]:
    s = hit.get("summary") or {}
    print(f"  {s.get('core.externalId','?'):<16} classType: {s.get('core.classType','?')}")
