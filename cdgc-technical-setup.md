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

Guide the user through: **IDMC → Metadata Command Center → New → Catalog Source → Snowflake**

| Setting | Value |
|---|---|
| Name | `<PREFIX>_FinancialServices` |
| Connection | `<PREFIX>_SNOWFLAKE_CONN` |
| Metadata change | **Retain** |

**Capabilities — enable these 6:**

| Capability | Enable | Why |
|---|---|---|
| Metadata Extraction | ✓ | Tables/columns — required |
| Data Profiling | ✓ | Row counts, null %, distinct values — **required before DQ** |
| Data Quality | ✓ | Evaluates DQ rules — requires Profiling ON |
| Data Classification | ✓ | Auto-detects PII: SSN, EMAIL, DATE_OF_BIRTH |
| Glossary Association | ✓ | Auto-links columns to Business Terms |
| Relationship Discovery | skip | Requires inference model — skip for demo |
| Lineage Discovery | skip | No views/stored procs in demo schema |
| Data Observability | skip | Needs multiple scans to build baseline |
| Writeback | skip | Can modify source schema — too risky |

**Critical:** Data Profiling must be ON for DQ results to appear. If DQ shows nothing
after the scan, this was the missing capability — re-run with Profiling enabled.

**Runtime Environment — profiling requirement:**
| Runtime | Metadata Extraction | Data Profiling |
|---|---|---|
| Hosted Agent (serverless) | ✓ | ✗ not supported |
| Shared Secure Agent | ✓ | ✗ results lost (wrong org) |
| Dedicated Secure Agent | ✓ | ✓ required |

If no dedicated Secure Agent is available, skip profiling and use `cdgc_dq_scores.py`
to inject DQ scores directly via API. Profiling is a "live customer environment" story.

**Warning:** Re-editing a catalog source resets capability checkboxes — re-verify all
capabilities are enabled before re-running after any edit.

**Filter:** Enter the schema path: `<database>.<schema>`
This is critical — without a filter, the scanner will attempt every schema the user has access to.

**Metadata change behaviour:** Set to **Retain**
This prevents auto-deletion of catalog objects if the Snowflake tables are temporarily unavailable.

Click **Run**. Scan takes 3–5 minutes.

**Expected result:** 4 tables, 57 columns ingested into CDGC.

**If scan shows 0 objects:** The filter path is wrong — verify it matches exactly
`<DATABASE>.<SCHEMA>` as shown in Snowflake (case matters).

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

## Step 6 — Gap analysis and close remaining coverage

The gap analyzer identifies ungoverned columns, matches them to existing terms where
possible, and drafts new Business Terms for everything else.

**Analyze:**
```bash
python3 ~/Documents/CDGC/cdgc_gap_analyzer.py
```

Opens `CDGC_Gap_Review.xlsx` with 3 tabs:

| Tab | Content | Action |
|---|---|---|
| Suggested Links | Columns matched to existing terms | Set APPROVE=YES to accept |
| Suggested New Terms | AI-drafted names, descriptions, domains | Edit if needed, set APPROVE=YES |
| Already Governed | Reference — already linked columns | No action needed |

**Human review step:**
- Open the workbook
- Tab 1: Verify suggested matches look correct — set APPROVE=YES
- Tab 2: Review AI-drafted Business Term names and descriptions — edit if needed, set APPROVE=YES
- Tab 2: Verify domain assignment for each new term is correct

**Apply after review:**
```bash
python3 ~/Documents/CDGC/cdgc_gap_analyzer.py --apply
```

What `--apply` does:
- Tab 1 YES rows: PATCHes column glossary link to existing term
- Tab 2 YES rows: POSTs new Business Term to CDGC, then PATCHes column glossary link

**After full approval:** 57/57 columns governed → 100% Technical Coverage.

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
| Gap analysis + new terms | ✅ Yes | Validated — `cdgc_gap_analyzer.py` |
| Import governance assets | ✅ Yes | Validated — bulk import API |
| Link classifications to Business Terms | ✅ Yes | `cdgc_link_classifications.py` — run after promoting MCC classifications |

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

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Connection string is invalid. Unable to parse." | Account field has `.snowflakecomputing.com` suffix | Remove suffix — enter account ID only |
| Scan completes with 0 objects | Filter path wrong | Verify exact `DATABASE.SCHEMA` path |
| Column not found in linking script | Column name case mismatch | Script searches uppercase — column names must match |
| 500 error with glossary data in response | Column already linked | Not an error — link exists |
| Dashboard Technical Coverage shows 0% | Hardcoded map doesn't match prefix | Update COLUMN_TO_TERM map in `cdgc_dashboard.py` to use your prefix |
