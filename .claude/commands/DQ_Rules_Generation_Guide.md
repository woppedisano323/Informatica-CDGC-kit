# DQ Rules Generation Guide

## Overview

This guide documents the standalone flow for generating and deploying ICDQ data quality rules
without a CDGC dependency. Rules are built from client schema, sample data, profile results,
or policy documents — then handed to Claire in ICDQ, published as REST API endpoints, and
callable from any source system.

**Requires:** ICDQ enabled in your IDMC org.

**Does NOT require:** CDGC, MCC, Snowflake catalog source, or any prior import.

**Skill:** `/cdgc-dq-rules`

---

## When to use this flow vs the CDGC pipeline

| Situation | Use |
|-----------|-----|
| Client wants DQ rules callable from Databricks, Salesforce, or custom apps | This guide — standalone, no CDGC |
| Client wants DQ scores on every MCC scan, visible in CDGC catalog | `DQ_ICDQ_Deployment_Guide.md` — full pipeline |
| Client has CDGC set up and just needs rules linked to it | `/cdgc-dq-setup` directly |
| Client has client documents and wants a full governance + DQ package | `/cdgc-client-setup` |

**Key distinction:** Standalone rules execute on demand via REST API against any data source.
No catalog source, no MCC scan, no occurrence records required. This is the right path when
a customer has ICDQ but has not yet deployed CDGC, or wants rules that run outside the MCC
scan cycle.

---

## Inputs

Run `/cdgc-dq-rules` and provide as many of the following as you have. More context produces
better-targeted rules.

| Input | What it drives |
|-------|---------------|
| Schema / DDL (Snowflake SHOW COLUMNS, SQL CREATE TABLE, CSV/Excel data dictionary) | Column names, data types, nullable flags, PK/FK signals |
| Sample rows (10–100 rows, CSV or Excel) | Null rates, value ranges, format patterns, enum detection |
| Profile results (MCC export or manual — null %, distinct count, min/max, top values) | Same as sample rows, pre-computed |
| Existing rule specs (prior DQ rules, SLA docs, data quality standards) | Anchors rule names and logic to known constraints |
| Policy / regulatory docs (HIPAA, SOX, BCBS 239, GDPR, KYC requirements) | Populates `Regulatory_Driver` column, flags PHI/PII columns |

A schema alone is enough to get started. Combining schema + sample rows + policy docs
produces the richest output.

---

## Output — `{PREFIX}_IDQ_Rules.xlsx`

The skill generates a single xlsx file with two sheets.

### Sheet 1: `DQ Rules` — 10 columns (exact order)

| Column | Content |
|--------|---------|
| `Rule_ID` | Category prefix + sequence number (e.g. `CUST-001`, `PAT-003`) |
| `Category` | Completeness / Validity / Consistency / Uniqueness / Timeliness |
| `Rule_Name` | Plain-English rule name — matches `Name` in File 13 if used downstream with `/cdgc-dq-setup` |
| `Description` | What the rule validates and why it matters |
| `Target_Fields` | Snowflake column name(s) the rule applies to |
| `Rule_Logic` | Pre-drafted SQL expression. Marked `[REVIEW]` if inferred from observed data. |
| `Severity` | Critical / High / Medium / Low |
| `Regulatory_Driver` | Regulatory framework mapped from policy docs (e.g. HIPAA, BCBS 239). Blank if none. |
| `Pass_Example` | Example of a passing value |
| `Fail_Example` | Example of a failing value |

### Sheet 2: `Summary`

Rule counts by dimension (Completeness, Validity, etc.) and confidence tier.

### Color coding

| Color | Meaning |
|-------|---------|
| White | High confidence — logic ready for Claire |
| Light yellow (`FFFFE0`) | Medium confidence — review recommended |
| Light orange (`FFD580`) | Logic inferred from observed data range — SE must confirm before use |
| Light red (`FFB3B3`) | Low confidence / placeholder — do not use without review |

---

## Rule_ID prefix conventions

Derive from the domain grouping in the schema. Common conventions:

**Healthcare:** `PAT` (patient), `ENC` (encounters), `LAB` (lab results), `MED` (medications),
`AI` (model outputs), `PHI` (compliance)

**Financial Services:** `CUST` (customer/KYC), `TXN` (transactions), `GL` (general ledger),
`RISK` (risk exposure), `REG` (regulatory), `MDL` (model outputs)

For other verticals: derive a 2–4 letter prefix from the domain name.

---

## [REVIEW] flags — what they mean

Rules marked `[REVIEW]` in `Rule_Logic` were inferred from observed data, not known constraints:

- **Range rules** — `BETWEEN {min} AND {max}` derived from sample or profile min/max. The observed
  range may not reflect the full valid range — a score of 98 observed in data may legitimately go
  to 100. Confirm the actual valid bounds before handing to Claire.

- **Valid value sets** — `IN ('val1', 'val2', ...)` derived from enum detection (distinct ≤ 20).
  The observed set may be incomplete — new valid values may exist that weren't in the sample.
  Confirm against an authoritative reference.

**Do not hand `[REVIEW]` rows to Claire without resolving them.** Orange rows in particular require
SE sign-off — incorrect logic produces misleading DQ scores.

---

## Handing off to Claire

Once `{PREFIX}_IDQ_Rules.xlsx` is reviewed and `[REVIEW]` rows are resolved:

1. Open **ICDQ** → create a project and folder for this client
2. Open **Claire** (AI assistant in ICDQ)
3. Provide `{PREFIX}_IDQ_Rules.xlsx` directly to Claire — Claire reads the file and builds all
   rules. No manual transcription.
4. After Claire builds the rules: verify each rule's output port is named **`Output`** exactly

**Critical:** The output port MUST be named `Output` (capital O, no trailing characters). Any
deviation causes CDGC to reject the occurrence with:
> "Specify a valid output port for the technical rule reference."

Verify: open one rule in ICDQ → Output tab → confirm port name is `Output`.

---

## Publishing rules as API endpoints

Once rules are built in ICDQ:

1. In ICDQ → **API Center** → enable each rule for API access
2. Rules are now callable as REST endpoints from any source system

```
POST https://<icdq-host>/api/v1/rules/<rule-id>/execute
Body: { "inputData": { "<column>": "<value>" } }
Response: { "result": "PASS" | "FAIL", "score": 0.0–1.0 }
```

This is the standalone path — no MCC scan, no CDGC occurrence record required.

---

## Connecting to CDGC later (optional)

If the client later wants DQ scores surfaced in CDGC on every MCC scan:

1. Run `/cdgc-setup` or `/cdgc-client-setup` to import the governance layer (14 files)
2. Run `/cdgc-dq-setup` — when asked if rules are already built, answer **yes** to skip Step 1
3. The MCC scan in Step 6 of `/cdgc-dq-setup` executes the rules and writes scores to CDGC

See `DQ_ICDQ_Deployment_Guide.md` for the full pipeline details.

---

## Key gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Claire builds wrong output port name | Default port name varies by rule type | After Claire generates rules, verify output port = `Output` before fetching IDs |
| `[REVIEW]` rule passes incorrectly | Observed range/enum was incomplete | Resolve all `[REVIEW]` rows before handing to Claire |
| Rule_Name mismatch with File 13 downstream | Rule_Name changed after generation | `patch_dq_template.py` joins on name — keep Rule_Name identical to File 13 `Name` if connecting to CDGC later |
| API endpoint returns 404 after enabling | "Enable for APIs" not saved | Re-open ICDQ API Center and confirm each rule shows as enabled |
| No `Regulatory_Driver` populated | No policy/regulatory docs provided | Re-run skill with policy docs added, or populate manually |
