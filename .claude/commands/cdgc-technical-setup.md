---
description: Add real technical metadata to a CDGC governance environment — Snowflake sample data, MCC catalog source scan, column-to-Business-Term linking, governance gap analysis, and Technical Coverage dashboard. Picks up where cdgc-setup leaves off. Financial Services vertical validated end-to-end May 2026.
---

# CDGC Technical Metadata Setup

You are an Informatica CDGC specialist. This skill adds the **technical metadata layer** on top of a governance environment already built with `/cdgc-setup` or `/cdgc-demo-live`.

When invoked, greet the user and confirm prerequisites before proceeding:

```
Welcome to the CDGC Technical Metadata Setup!

This skill adds real scanned technical metadata to your CDGC governance environment —
connecting Snowflake tables and columns directly to your Business Terms, auto-classifying
PII, and showing governance coverage in the live dashboard.

Before we start: have you already run /cdgc-setup (or /cdgc-demo-live) and imported
the 14 governance files into your CDGC org?
```

If the user says no — stop and direct them to `/cdgc-setup` first. The technical layer requires Business Terms and Domains to exist before scanning.

If yes — ask for setup details in Turn 1.

---

## Why order matters

The governance layer must be imported BEFORE the MCC scan. Here's why:

MCC's **Glossary Association** capability (enabled during catalog source setup) attempts to
auto-link scanned columns to existing Business Terms as they land in CDGC. If Business Terms
don't exist yet, Glossary Association finds nothing and the scan produces ungoverned columns.

**Correct sequence:**
```
Step 1  /cdgc-setup          → Governance foundation (Terms, Policies, Domains)
Step 2  Snowflake setup      → Load sample data for scanning
Step 3  IDMC connection      → Create Snowflake connection in Administrator
Step 4  MCC scan             → Scan tables/columns, Glossary Association runs
Step 5  Column linking       → Catch what Glossary Association missed
Step 6  Gap analysis         → Create missing terms, close remaining gap
Step 7  Dashboard            → Technical Coverage tab shows full picture
```

---

## Turn 1 — Gather connection details

Ask all of the following together:

1. **Vertical** — Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector, Oil & Gas, or Manufacturing
2. **Customer prefix** — the prefix used when governance assets were imported (e.g. `RKF`, `ACM`, `BNB`)
3. **Snowflake account identifier** — found in browser URL: `<account>.snowflakecomputing.com`
   (enter just the account part, e.g. `dua50582` — no suffix)
4. **Snowflake username** — the user who will connect
5. **Snowflake warehouse** — run `SHOW WAREHOUSES;` in a worksheet if unsure
6. **Snowflake database** — existing database to use, or suggest `CDGC_DEMO`
7. **Snowflake schema** — existing or new, suggest `<PREFIX>_DEMO`

Once collected, proceed through each step below.

---

## Step 1 — Load Snowflake sample data

Tell the user to run:

```bash
python3 ~/Documents/CDGC/cdgc_snowflake_setup.py
```

Explain what it does and expected output:

- Connects to Snowflake using the credentials provided
- Creates schema if it doesn't exist
- Loads 4 tables with realistic industry sample data:

**Financial Services:**
| Table | Rows | Key columns |
|---|---|---|
| CUSTOMER_MASTER | 500 | SSN, EMAIL, DATE_OF_BIRTH, CREDIT_SCORE |
| TRANSACTION_LEDGER | 2000 | TRANSACTION_ID, AMOUNT, CURRENCY, STATUS |
| GL_ENTRY_REGISTER | 800 | ACCOUNT_CODE, DEBIT_AMOUNT, CREDIT_AMOUNT |
| RISK_EXPOSURE_DAILY | 600 | PROBABILITY_OF_DEFAULT, LOSS_GIVEN_DEFAULT |

Expected output:
```
Connecting to <account>...
Schema <database>.<schema> ready.

Creating tables...
  CUSTOMER_MASTER — OK
  TRANSACTION_LEDGER — OK
  GL_ENTRY_REGISTER — OK
  RISK_EXPOSURE_DAILY — OK

Loading data...
  CUSTOMER_MASTER           500 rows
  TRANSACTION_LEDGER       2000 rows
  GL_ENTRY_REGISTER         800 rows
  RISK_EXPOSURE_DAILY       600 rows

Done. Snowflake is ready for MCC scanning.
```

**If pip/snowflake-connector error:** Run `pip3 install snowflake-connector-python` first.

---

## Step 2 — Create IDMC Snowflake connection

Guide the user through: **IDMC → Administrator → Connections → New Connection → Snowflake**

| Field | Value |
|---|---|
| Connection name | `<PREFIX>_SNOWFLAKE_CONN` |
| Authentication | Standard |
| Username | (their Snowflake username) |
| Password | (their Snowflake password) |
| Account | `<account-identifier>` — no `.snowflakecomputing.com` suffix |
| Warehouse | (their warehouse name) |
| Additional JDBC URL Parameters | `db=<database>&schema=<schema>` |

**Critical:** The Account field must contain ONLY the account identifier — no suffix.
IDMC appends `.snowflakecomputing.com` automatically. Including it doubles up and causes:
`"Connection string is invalid. Unable to parse."`

**If the org uses org-based Snowflake accounts** (URL format: `app.snowflake.com/<org>/<account>`):
Use `<org>-<account>` as the account identifier (e.g. `wm14569-dua50582`).

Click **Test Connection** — must show Success before proceeding.

---

## Step 3 — Create MCC catalog source

Follow these steps exactly in **IDMC → Metadata Command Center**:

**1. Create the catalog source**
- Click **New** → **Catalog Source** → select **Snowflake**
- **Name:** `<PREFIX>_<Vertical>` (e.g. `FCB_FinancialServices`) — use the customer prefix and vertical name, no spaces
- **Connection:** select `<PREFIX>_SNOWFLAKE_CONN` created in Step 2
- Click **Next**

**2. Set the filter (critical)**
- Under **Filter**, enter the schema path: `<DATABASE>.<SCHEMA>` (e.g. `CDGC_DEMO.FCB_DEMO`)
- This MUST match exactly how the database and schema appear in Snowflake — case matters
- Without a filter the scanner attempts every schema the user has access to

**3. Enable capabilities**
On the Capabilities screen, enable exactly these 5 — leave all others off:

| Capability | Enable | Why |
|---|---|---|
| Metadata Extraction | ✓ | Tables/columns — required |
| Data Profiling | ✓ | Row counts, null %, distinct values — required before DQ |
| Data Quality | ✓ | Evaluates DQ rules — requires Profiling ON |
| Data Classification | ✓ | Auto-detects PII: SSN, EMAIL, DATE_OF_BIRTH |
| Glossary Association | ✓ | Auto-links columns to Business Terms during scan |
| Relationship Discovery | ✗ | Skip — requires inference model |
| Lineage Discovery | ✗ | Skip — no views/stored procs in demo schema |
| Data Observability | ✗ | Skip — needs multiple scans to build baseline |
| Writeback | ✗ | Skip — can modify source schema |

**4. Set Metadata change behaviour**
- Set to **Retain** — prevents auto-deletion of catalog objects if Snowflake tables are temporarily unavailable

**5. Select Runtime Environment**
| Runtime | Metadata Extraction | Data Profiling |
|---|---|---|
| Hosted Agent (serverless) | ✓ | ✗ not supported |
| Shared Secure Agent | ✓ | ✗ results lost (wrong org) |
| Dedicated Secure Agent | ✓ | ✓ required |

If no dedicated Secure Agent is available, disable Data Profiling and Data Quality — use `cdgc_dq_scores.py` after the scan to inject DQ scores via API.

**6. Save and Run**
- Click **Save**
- Click **Run** — scan takes 3–5 minutes
- Monitor status in MCC → Jobs

**Expected result:** 4 tables, 57 columns ingested into CDGC.

**Warning:** Re-editing a catalog source resets capability checkboxes — re-verify all capabilities are enabled before re-running after any edit.

**If scan shows 0 objects:** The filter path is wrong — verify it matches exactly `<DATABASE>.<SCHEMA>` as shown in Snowflake (case matters).

**If scan shows fewer than 57 columns:** Glossary Association ran but found no Business Terms — confirm `/cdgc-setup` import completed before the scan.

---

## Step 4 — Add Business Names via Claire

For each of the 4 scanned tables in **CDGC → Explore**:
1. Search for the table name
2. Open the table asset
3. Click the Edit (pencil) icon on the **Business Name** field
4. Click **"Use Claire to generate"**

This is a live demo moment — Claire reads the column names and generates a human-readable
business label in real time, showing AI-assisted metadata enrichment.

Expected Claire output:
| Table | Business Name |
|---|---|
| CUSTOMER_MASTER | Customer Master |
| TRANSACTION_LEDGER | Transaction Ledger |
| GL_ENTRY_REGISTER | GL Entry Register |
| RISK_EXPOSURE_DAILY | Daily Risk Exposure |

---

## Step 5 — Link columns to Business Terms (initial pass)

This script links the 18 highest-value columns to their Business Terms using the
validated PATCH API pattern.

```bash
python3 ~/Documents/CDGC/cdgc_link_technical_assets.py
```

**What it does:**
- Searches CDGC for all scanned columns by name
- PATCHes each column with its Business Term via the glossary segment
- Safe to re-run — already-linked columns show `(already linked)`

**Validated API pattern (for reference):**
```
PATCH /data360/content/v1/assets/{column-uuid}?scheme=internal
Body: [{"operation":"add","segment":"glossary","items":[{"core.externalId":"<TERM-ID>"}]}]
```
Key lesson: PATCH the **Column** (technical asset), not the BusinessTerm.

**Expected output:**
```
✓ CUSTOMER_ID → <PREFIX>BT-1
✓ SSN → <PREFIX>BT-2
✓ DATE_OF_BIRTH → <PREFIX>BT-3
... (18 total)
Linked: 18/18
```

**After this step:** ~37% Technical Coverage (columns repeat across tables so actual
governed column count is higher than 18 unique names).

---

## Step 6 — Governance pipeline (link, gap analysis, Business Names)

Use the unified governance pipeline — replaces the old `cdgc_gap_analyzer.py` + `cdgc_set_business_names.py` scripts.

**Phase 1 + 2a — Link known columns and generate gap review workbook:**
```bash
python3 ~/Documents/CDGC/cdgc_govern_technical.py --all --company "Customer Name"
```
- Links 18 known columns to their Business Terms (resolves term names live — no hardcoded IDs)
- Generates `CDGC_Gap_Review_<Company>.xlsx` and opens it automatically
- **Close any other Excel/Numbers apps before running** — macOS will append " 2" to the filename if the file is locked, causing Phase 2b to fail

**Human review:**
- Tab 1 (Suggested Links): Set APPROVE=YES for correct fuzzy matches
- Tab 2 (Suggested New Terms): Review AI-drafted terms, set APPROVE=YES
- Tab 3 (Already Governed): Reference only — no action needed
- Save and close the workbook

**Phase 2b — Apply approvals, create new terms, link columns:**
```bash
python3 ~/Documents/CDGC/cdgc_govern_technical.py --phase 2b --email your@email.com
```
- Skips term creation for any terms already in CDGC (safe to re-run)
- Resolves column UUIDs fresh from the live org — never uses stale workbook UUIDs
- Links all approved columns to their terms via PATCH

**Phase 3 — Propagate Business Names (MCC UI — not scriptable):**

After all column→term links are in place, re-run MCC Glossary Association to propagate Business Names:
1. MCC → catalog source → Glossary Association task settings
2. Set **Assign Business Names and Descriptions** → Yes
3. Disable **Keep Existing Business Names and Descriptions**
4. Re-execute the Glossary Association job

Business Names will populate on all linked columns once the job completes.

> **Note:** The API export→modify→reimport approach (Automatic Assignment = Enabled) hard FAILs on every attempt. MCC Glossary Association re-run is the only confirmed working method. Validated 2026-06-22.

**After full run:** 57/57 columns governed, Business Names populated → 100% Technical Coverage.

---

## Step 6b — DQ Rule Occurrences

This step binds your DQ Rule Templates (imported in file 13) to physical columns in the
catalog so that DQ scores are visible in CDGC. There are two paths depending on whether
ICDQ is enabled in your org:

| Path | When | Scores |
|------|------|--------|
| **ICDQ path** (recommended) | ICDQ enabled + MCC Data Quality capability | Real — ICDQ executes rules against live Snowflake data |
| **Score injection path** | No ICDQ, or demo/presentation only | Synthetic — injected via API |

**Run the dedicated skill for the full ICDQ path:**
```
/cdgc-dq-setup
```
This runs the complete 8-step sequence: fetch ICDQ rule IDs → patch template → import →
generate occurrences → import occurrences → link templates → MCC scan → verify.
The DQ deployment guide (`DQ_ICDQ_Deployment_Guide.md`) has full technical reference.

---

### Score injection path (no ICDQ)

Use when ICDQ is not available and you need DQ scores in the UI for a presentation.

#### Why 15_DQ_Rule_Occurrence.xlsx is not in the 14-file template

The standard demo package contains 14 import files (01–14). DQ Rule Occurrences are
intentionally excluded because the **Primary Data Element (PDE) path is environment-specific**:

```
FCB_Financial_Snowflake://TEST_DB/WILL_CDGC_DEMO/CUSTOMER_MASTER/SSN
```

This path contains the MCC catalog source name and the exact DB/Schema/Table/Column path
as scanned. These values only exist after your MCC scan and are unique to your org.
A static template file cannot be prefix-swapped to produce valid PDE paths for a different
environment — so the occurrence file is always generated at runtime, never copied from a template.

#### Prerequisites

- Files 01–14 imported (including `13_DQ_Rule_Template.xlsx`)
- MCC scan completed (Metadata Extraction must be done — columns must exist in the catalog)

#### Generate the occurrence file

```bash
python3 ~/Documents/CDGC/cdgc_create_dq_occurrences.py
```

This script reads `13_DQ_Rule_Template.xlsx`, queries live CDGC for all scanned columns
matching each rule's Input Port Name, and builds `15_DQ_Rule_Occurrence.xlsx` with the
correct PDE path for each column.

Expected output:
```
✓ Authenticated
Found 35 DQ Rule Templates
Matching columns in CDGC...
  SSN Not Null → CUSTOMER_MASTER.SSN (FCB_Financial_Snowflake://TEST_DB/WILL_CDGC_DEMO/CUSTOMER_MASTER/SSN)
  ...
74 occurrences written to 15_DQ_Rule_Occurrence.xlsx
0 warnings
```

**If warnings appear:** The Input Port Name in the rule template doesn't match any scanned
column name. Check the exact column name in Snowflake — Input Port Name must be an exact
case-sensitive match to the physical column name.

#### Import the occurrence file

Import `15_DQ_Rule_Occurrence.xlsx` via the standard bulk import UI (CDGC → gear icon →
Import). Wait for **COMPLETED** status before proceeding.

**If hard FAILED with empty detail:** This is a structural rejection. Causes:
- Measuring Method value is not exact CamelCase (see constraints below)
- Column structure mismatch — Input Port Name must be column 8 in the sheet (before Lifecycle)
- `Submit Ticket` column does not exist in this template — do not add it

#### Inject DQ scores

DQ Rule Occurrences using `TechnicalScript` as Measuring Method are not auto-scored by
MCC's profiling engine. Inject scores manually via API:

```bash
python3 ~/Documents/CDGC/cdgc_dq_scores.py
```

Expected output:
```
✓ Authenticated
DQ Score CSV — 74 occurrences
...
Status: 202
Status: COMPLETED
✓ DQ scores injected successfully.
```

**Note:** `cdgc_dq_scores.py` uses a deprecated endpoint (deprecated April 2026, supported
through July 2026). For new environments, use `/cdgc-dq-setup` with the ICDQ path instead.

Then in CDGC → Explore, open any DQ Rule Occurrence and check the **Data Quality** tab —
scores should now be visible with pass rate, total rows, and failed row count.

#### Measuring Method — valid enum values

The Measuring Method field in `13_DQ_Rule_Template.xlsx` must be one of these exact
CamelCase strings (from CDGC_Template_All.xlsx data validation):

| Value | When to use | Auto-scored by MCC? |
|---|---|---|
| `TechnicalScript` | External script executes the rule | ❌ — inject via API |
| `BusinessExtract` | Scores come from a business-side extract | ❌ — inject via API |
| `SystemFunction` | Scores come from a system-level function | ❌ — inject via API |
| `InformaticaCloudDataQuality` | Rules built in ICDQ | ✅ — MCC auto-scores |

**Do NOT use `InformaticaCloudDataQuality`** unless the Technical Rule Reference IDs from
ICDQ are populated. The import will fail with a hard FAILED if that field is blank.

---

## Step 7 — Launch dashboard and verify Technical Coverage

```bash
python3 ~/Documents/CDGC/cdgc_dashboard.py
```

You will be prompted for IDMC credentials. Log in before the demo call — session stays
warm for 25 minutes.

Navigate to the **Technical Coverage** tab:
- 4 stat cards: Scanned Tables, Total Columns, Governed Columns, Coverage %
- Per-table breakdown with progress bars
- Each table shows columns — green `✓ Governed` with Business Term badge, or `Ungoverned`
- Tab badge shows coverage % at a glance

**Verification checklist:**
- [ ] 4 tables visible (CUSTOMER_MASTER, TRANSACTION_LEDGER, GL_ENTRY_REGISTER, RISK_EXPOSURE_DAILY)
- [ ] 57 total columns
- [ ] Coverage % matches expected (37% after Step 5, 100% after Step 6)
- [ ] SSN column shows "Social Security Number" Business Term
- [ ] EMAIL column shows "Email Address" Business Term
- [ ] CDGC → Explore → search `SSN` → column shows Business Term in glossary
- [ ] CDGC → Explore → search `columns related to data classification 'Social Security Number'` → PII columns appear
- [ ] Business Terms show Classifications tab populated (requires Step 7)

---

## Step 7 — Link MCC classifications to Business Terms

MCC classifies columns automatically. This step links those classifications to Business Terms so the full chain is visible: column → Business Term → classification → policy.

**Prerequisite — promote MCC classifications in CDGC UI first:**
1. CDGC → **Catalog → Classifications** → Generated Classifications
2. Select SSN, Email Address, Date of Birth (and any others relevant to the vertical)
3. Click **Promote** → wait ~2 minutes

**Then run:**
```bash
python3 ~/Documents/CDGC/cdgc_link_classifications.py
```

Enter credentials when prompted. The script shows a match table (EXACT/HIGH/FUZZY confidence) and requires `CONFIRM` before writing anything. Failed links can be done manually via Business Term → Classifications tab in the UI.

---

## Demo narrative (money shots in order)

1. **Dashboard → Technical Coverage** — show baseline %, explain the governance gap
2. **CDGC → Explore → search `SSN`** — column shows Social Security Number Business Term
3. **Open Business Term** → governed by Customer Data Privacy Policy → linked to Customer & KYC domain
4. **Search `columns related to data classification 'Social Security Number'`** — MCC auto-classified PII
5. **Open CUSTOMER_MASTER table** — show Claire-generated Business Name
6. **Show gap_analyzer workbook** — "here's how we close the remaining gap with human review"
7. **After --apply → Dashboard** — coverage jumps to 100%

**Narrative thread:**
> "We scanned your Snowflake environment. MCC found 57 columns across 4 tables and
> automatically classified SSN, EMAIL, and DATE_OF_BIRTH as PII — without any configuration.
> 37% of those columns are already linked to governed Business Terms with Policy coverage.
> The remaining 63% aren't ungoverned forever — the gap analyzer drafted the missing terms.
> A data steward reviews and approves in Excel, one click applies them all. That's how you
> close a governance gap in an afternoon instead of a quarter."

---

## API automation status (April 2026)

Not everything in this skill can be scripted — here's the current state:

| Step | Automatable | Notes |
|---|---|---|
| Create IDMC connection | ❌ GUI | Administrator UI — no API in current docs |
| Create MCC catalog source | ❌ GUI | Ch.9 defers to Informatica Developer Portal |
| Configure capabilities | ❌ GUI | UI checkboxes only |
| Trigger scan | ⚠️ Maybe | Listed in Ch.9 but endpoint not published |
| Poll scan status | ✅ Yes | GET `/data360/observable/v1/jobs/{jobId}` |
| Link columns to terms | ✅ Yes | Validated — `cdgc_link_technical_assets.py` |
| Gap analysis + new terms | ✅ Yes | Validated — `cdgc_govern_technical.py` |
| Import governance assets | ✅ Yes | Validated — bulk import API |
| Link classifications to Business Terms | ✅ Yes | `cdgc_link_classifications.py` — run after promoting MCC classifications |
| Generate DQ Rule Occurrences | ✅ Yes | `cdgc_create_dq_occurrences.py` — queries live catalog, generates file 15 |
| Inject DQ scores | ✅ Yes | `cdgc_dq_scores.py` — POST `/data-quality/v1/rule-occurrences/runs` (deprecated April 2026, supported until July 2026) |

**Future automation path:** The Informatica Developer Portal (`developer.informatica.com`)
likely contains the catalog source creation endpoints. If access is obtained, Steps 2–3
may become fully scriptable — eliminating the remaining GUI steps.

---

## Known limitations

**Table → DataSet relationship:** Cannot be created via API in this CDGC version.
The DataSet asset type has no Related Assets UI and the PATCH API rejects all
association attempts. This does not affect the demo narrative — the Column → Business Term
→ Policy chain is the compelling story.

**Glossary Association auto-linking:** MCC's built-in Glossary Association may partially
link columns during the scan but typically misses many. `cdgc_link_technical_assets.py`
is the reliable completion step.

**Duplicate link response:** Re-running link scripts returns HTTP 500 with the existing
glossary payload for already-linked columns. Scripts detect this and show `(already linked)`.
This is not an error.

**Technical Coverage API:** The search API `glossary` segment returns empty for technical
assets — links cannot be detected via search. The dashboard uses the known COLUMN_TO_TERM
map for accurate display.

**Data Profiling and DQ scoring require a Dedicated Secure Agent.** The Hosted Agent
(serverless) and Shared Secure Agent do not work for profiling — results never appear in
CDGC. If no dedicated agent is available, disable Data Profiling and Data Quality in the
MCC capabilities and use `cdgc_dq_scores.py` to inject scores via API after the scan.

**Data Set → AI Model lineage cannot be bulk imported.** The relationship type
`is in Direct Lineage with` between Business Data Sets and AI Models is listed in the
Annexure but rejected by the bulk import validator with "No valid data to publish".
This relationship only works for Technical Data Sets (from MCC scan). AI lineage must
be established via MCC Lineage Discovery scanning views or stored procedures.

**`InformaticaCloudDataQuality` Measuring Method requires ICDQ rule IDs.** Do not set
this value unless Technical Rule Reference IDs from ICDQ are populated — the import will
fail with a hard FAILED and no detail in the log.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Connection string is invalid. Unable to parse." | Account field has `.snowflakecomputing.com` suffix | Remove suffix — enter account ID only |
| Scan completes with 0 objects | Filter path wrong | Verify exact `DATABASE.SCHEMA` path |
| Column not found in linking script | Column name case mismatch | Script searches uppercase — column names must match |
| 500 error with glossary data in response | Column already linked | Not an error — link exists |
| Dashboard Technical Coverage shows 0% | Hardcoded map doesn't match prefix | Update COLUMN_TO_TERM map in `cdgc_dashboard.py` to use your prefix |
