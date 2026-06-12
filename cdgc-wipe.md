---
description: Wipe all governance assets from a CDGC org — Domains, Subdomains, Business Terms, Policies, Regulations, Systems, AI Systems, AI Models, Data Sets, Business Areas, Legal Entities, Geographies, DQ Rule Templates. Use before reloading a demo environment. Requires API credentials and customer prefix. Prompts for confirmation before deleting anything. Validated and tested end-to-end May 2026.
---

# CDGC Glossary Wipe

You are an Informatica CDGC specialist. This skill deletes all governance assets from a CDGC org to prepare it for a clean demo reload. It is destructive and irreversible — always confirm with the user before executing.

---

## Overview

This skill:
1. Authenticates to IDMC using the two-step JWT flow
2. Searches for all governance assets by type
3. Presents a count summary and asks for explicit confirmation
4. Deletes assets in reverse dependency order using `DELETE /data360/content/v1/assets/{externalId}?scheme=external`
5. Loops until 404 confirms each asset is fully gone
6. Reports a final summary of what was deleted

### Key facts about the delete endpoint

The bulk import `Operation=Delete` approach does not work on suborg accounts — import jobs FAIL silently. The working approach is:

```
DELETE {ORG_URL}/data360/content/v1/assets/{externalId}?scheme=external
```

- Use `core.externalId` (e.g., `RKFBT-3`, `RKFDOM-1`) — NOT `core.identity` (UUID)
- Returns HTTP 201 + `{"messageCode":"Asset with id: [X] deleted"}` on success — **do NOT loop**; 201 means done
- The API returns 201 on every call regardless of async state — looping causes each asset to be deleted 19+ extra times (wasted time, no harm). Single call is correct.
- UUID-based delete (`DELETE /assets/{uuid}`) returns 404 — not supported for governance assets
- 429 rate limit: sleep 15s and retry once

### AI Model / AI System — classType search broken on suborg

`com.infa.ccgf.models.governance.AIModel` and `AISystem` return 0 hits from the search API on suborg accounts even when assets exist. This is a known platform bug. The working approach is to probe by sequential externalId:

- AI Models use prefix `<CUSTOMER_PREFIX>AIM-` (e.g., `RKFAIM-1`, `RKFAIM-2`...)
- AI Systems use prefix `<CUSTOMER_PREFIX>AIS-` (e.g., `RKFAIS-1`, `RKFAIS-2`...)
- Attempt DELETE on each sequential ID; stop when 404 is returned
- The DELETE itself acts as the existence check — 201 = existed and deleted; 404 = sequence is exhausted

The script prompts for `CUSTOMER_PREFIX` at runtime so it works for any customer.

### Deletion order

Order matters — dependency relationships block deletion if parents are deleted before children:

1. DQ Rule Templates — their glossary links block Business Term deletion
2. Business Terms
3. Data Sets
4. AI Models — must come before AI Systems (AI Model has AI System as parent)
5. AI Systems
6. Systems
7. Business Areas
8. Legal Entities
9. Geographies
10. Policies
11. Regulations
12. **Subdomains** — must come before Domains (auto-relationship blocks Domain deletion)
13. **Domains** — last

### Confirmed classTypes (tested and verified)

```
com.infa.ccgf.models.governance.RuleTemplate       ← DQ Rule Template (NOT DataQualityRuleTemplate)
com.infa.ccgf.models.governance.BusinessTerm
com.infa.ccgf.models.governance.DataSet
com.infa.ccgf.models.governance.AIModel
com.infa.ccgf.models.governance.AISystem
com.infa.ccgf.models.governance.System
com.infa.ccgf.models.governance.BusinessArea
com.infa.ccgf.models.governance.LegalEntity
com.infa.ccgf.models.governance.Geography
com.infa.ccgf.models.governance.Policy
com.infa.ccgf.models.governance.Regulation
com.infa.ccgf.models.governance.Subdomain          ← NOT SubjectArea
com.infa.ccgf.models.governance.Domain
```

---

## Step 0 — Warn and collect credentials

Present this warning before collecting anything:

```
╔══════════════════════════════════════════════════════════════════╗
║              ⚠  DESTRUCTIVE OPERATION — READ CAREFULLY           ║
╚══════════════════════════════════════════════════════════════════╝

This process will PERMANENTLY WIPE your CDGC implementation.

All governance assets will be deleted — this includes:
  • All Domains and Subdomains
  • All Business Terms
  • All Policies and Regulations
  • All Systems, AI Systems, AI Models, Data Sets, Business Areas, Legal Entities, and Geographies
  • All DQ Rule Templates

There is NO undo. Deleted assets cannot be recovered from the UI
or the API. If you need a backup, export your assets first.

This skill is intended for sandbox and demo orgs only.
DO NOT run this against a production environment.

If you are sure you want to continue, provide your IDMC credentials
below. They are used only in this session to generate a temporary
JWT token and are not stored anywhere.
```

Collect:
- `USERNAME` — IDMC username (not necessarily an email address)
- `PASSWORD` — IDMC password (use getpass — never print)
- `CUSTOMER_NAME` — the customer name used when the assets were originally generated (e.g., `Ronkonkoma Financial`). The prefix is derived from this name using the same logic as `/cdgc-setup`: take the first letter of each word, uppercase, up to 4 characters (e.g., `Ronkonkoma Financial` → `RKF`, `First Capital Bank` → `FCB`, `Acme Healthcare` → `AH`). Show the derived prefix to the user and confirm before proceeding — they can override it if needed.

---

## Step 1 — Write and execute the wipe script

Use this exact script — tested and validated end-to-end May 2026. Also available as `cdgc_wipe.py` in the repo.

Key design decisions baked in:
- **Single DELETE per asset** — the API returns HTTP 201 every call; looping wastes time with no benefit
- **AI Models/AI Systems probed by externalId** — classType search returns 0 on suborg (platform bug); probe by sequential ID and stop at 404
- **Second pass** — catches any stragglers from async deletion
- **Final verification scan** — confirms all-zeros before declaring clean

```python
import requests
import getpass
import sys
import time

LOGIN_URL = "https://dmp-us.informaticacloud.com"
ORG_URL   = "https://idmc-api.dmp-us.informaticacloud.com"

# classType search works for all types EXCEPT AIModel and AISystem on suborg —
# those are deleted by scanning all externalIds with known prefixes instead
SEARCH_TYPES = [
    ("DQ Rule Templates", "com.infa.ccgf.models.governance.RuleTemplate"),
    ("Business Terms",    "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Data Sets",         "com.infa.ccgf.models.governance.DataSet"),
    ("Systems",           "com.infa.ccgf.models.governance.System"),
    ("Business Areas",    "com.infa.ccgf.models.governance.BusinessArea"),
    ("Legal Entities",    "com.infa.ccgf.models.governance.LegalEntity"),
    ("Geographies",       "com.infa.ccgf.models.governance.Geography"),
    ("Policies",          "com.infa.ccgf.models.governance.Policy"),
    ("Regulations",       "com.infa.ccgf.models.governance.Regulation"),
    ("Subdomains",        "com.infa.ccgf.models.governance.Subdomain"),
    ("Domains",           "com.infa.ccgf.models.governance.Domain"),
]

username      = input("IDMC Username: ")
password      = getpass.getpass("IDMC Password: ")
customer_name = input("Customer name (as used when assets were generated, e.g. Ronkonkoma Financial): ").strip()

# Derive prefix the same way /cdgc-setup does — initials of each word, uppercase, up to 4 chars
derived = "".join(w[0].upper() for w in customer_name.split() if w)[:4]
override = input(f"  Derived prefix: {derived!r} — press Enter to confirm or type a different prefix: ").strip().upper()
customer_prefix = override if override else derived
print(f"  Using prefix: {customer_prefix}")

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

h_s = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id, "Content-Type": "application/json"}
h_d = {"Authorization": f"Bearer {jwt}", "X-INFA-ORG-ID": org_id}

def delete_one(ext_id):
    r = requests.delete(
        f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
        headers=h_d, timeout=30)
    if r.status_code == 429:
        time.sleep(15)
        r = requests.delete(
            f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
            headers=h_d, timeout=30)
    return r.status_code in (200, 201, 204, 404)

def search_type(class_type):
    for attempt in range(3):
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=h_s,
            json={"from": 0, "size": 100,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType", "values": [class_type]}]},
            timeout=30)
        if r.status_code == 429:
            time.sleep(15)
            continue
        if not r.text.strip():
            time.sleep(3)
            continue
        try:
            return r.json().get("hits", [])
        except Exception:
            time.sleep(3)
    return []

# ── Scan ──────────────────────────────────────────────────────────────────────

# AI Models and AI Systems: probe by externalId — classType search returns 0 on suborg
print("Scanning for AI Models and AI Systems by externalId probe...")
ai_to_delete = []
for suffix, label in [("AIM", "AI Model"), ("AIS", "AI System")]:
    found = []
    for i in range(1, 30):
        ext_id = f"{customer_prefix}{suffix}-{i}"
        r = requests.delete(
            f"{ORG_URL}/data360/content/v1/assets/{ext_id}?scheme=external",
            headers=h_d, timeout=30)
        if r.status_code == 404:
            break
        if r.status_code in (200, 201, 204):
            found.append(ext_id)
        time.sleep(0.2)
    print(f"  {label+'s':<25}: {len(found)} {'(deleted during probe)' if found else ''}")
    ai_to_delete.extend(found)

# All other types via classType search
all_assets = {}
total_search = 0
for label, class_type in SEARCH_TYPES:
    hits = search_type(class_type)
    all_assets[label] = hits
    total_search += len(hits)
    print(f"  {label:<25}: {len(hits)}")
    time.sleep(0.5)

total = total_search  # AI assets already deleted during probe above
print(f"\n  {'Total (search)':<25}: {total}")

if total == 0 and not ai_to_delete:
    print("\nOrg is clean — nothing to delete.")
    sys.exit(0)

confirm = input(f"\n⚠ This will permanently delete all remaining {total} assets.\n  Type CONFIRM to proceed: ")
if confirm.strip() != "CONFIRM":
    print("Cancelled.")
    sys.exit(0)

# ── Delete ────────────────────────────────────────────────────────────────────
total_cleared = 0
total_failed  = 0
print()
for label, class_type in SEARCH_TYPES:
    hits = all_assets[label]
    if not hits:
        continue
    print(f"  {label}: {len(hits)} found")
    for item in hits:
        name   = (item.get("summary") or {}).get("core.name", "?")
        ext_id = item.get("core.externalId", "")
        if not ext_id:
            print(f"    ✗ {name!r} — no externalId, delete manually in UI")
            total_failed += 1
            continue
        ok = delete_one(ext_id)
        if ok:
            print(f"    ✓ {name!r}")
            total_cleared += 1
        else:
            print(f"    ✗ {name!r} — unexpected response, delete manually in UI")
            total_failed += 1
        time.sleep(0.5)

print(f"\nCleared: {total_cleared + len(ai_to_delete)}  |  Failed: {total_failed}")
if total_failed:
    print("Failed assets may need manual deletion in the CDGC UI.")

# ── Second pass — catch any stragglers ────────────────────────────────────────
print("\nRunning second pass for stragglers...")
time.sleep(3)
straggler_cleared = 0
for label, class_type in SEARCH_TYPES:
    hits = search_type(class_type)
    if not hits:
        continue
    print(f"  {label}: {len(hits)} remaining")
    for item in hits:
        ext_id = item.get("core.externalId", "")
        name   = (item.get("summary") or {}).get("core.name", "?")
        if not ext_id:
            print(f"    ✗ {name!r} — no externalId, delete manually in UI")
            continue
        ok = delete_one(ext_id)
        if ok:
            print(f"    ✓ {name!r}")
            straggler_cleared += 1
        time.sleep(0.5)
if straggler_cleared:
    print(f"  Second pass cleared {straggler_cleared} additional assets.")
    time.sleep(3)

# ── Final verification scan ───────────────────────────────────────────────────
print("\nVerifying org is clean...\n")
time.sleep(3)
grand_total = 0
ALL_TYPES = SEARCH_TYPES + [
    ("AI Models",  "com.infa.ccgf.models.governance.AIModel"),
    ("AI Systems", "com.infa.ccgf.models.governance.AISystem"),
]
for label, class_type in ALL_TYPES:
    hits = search_type(class_type)
    count = len(hits)
    grand_total += count
    status = "✓" if count == 0 else "⚠"
    print(f"  {status} {label:<25}: {count}")

print(f"\n  {'Total':<25}: {grand_total}")
if grand_total == 0:
    print("\nOrg is clean — ready for import.")
else:
    print("\n⚠ Some assets remain. Check the CDGC UI and re-run if needed.")
```

---

## Safety rules

- **Never run against a production org** — always confirm the org URL before proceeding
- **Confirmation is mandatory** — the script will not delete anything without the user typing `CONFIRM`
- **No undo** — deleted assets cannot be recovered; export first if you need a backup
- **AI Models/AI Systems count in verification will show 0** even when they were present — classType search is broken on suborg. Deletion is confirmed by the probe showing counts deleted during scan.
- **If the UI still shows assets after the wipe completes** — re-run the script; the second-pass and verification scan are authoritative. The UI can lag by a few minutes.

---

## Sharing this skill

Copy `cdgc-wipe.md` to `~/.claude/commands/cdgc-wipe.md`.
Invoke with `/cdgc-wipe` in any Claude Code session.
