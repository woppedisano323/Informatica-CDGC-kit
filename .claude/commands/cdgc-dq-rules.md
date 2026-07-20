---
description: Generate a Claire-ready DQ rules file from client schema, sample data, profile results, or existing rule specs — without any CDGC dependency. Rules are built in ICDQ and published as API endpoints callable from any source system (Databricks, Salesforce, custom apps). Use this when the client wants ICDQ-powered data quality without the full CDGC governance layer.
---

# CDGC DQ Rules — Standalone

This skill generates a Claire-ready `{PREFIX}_IDQ_Rules.xlsx` file for clients who want ICDQ-powered data quality rules without the full CDGC governance layer. Rules built from this file are published as API endpoints in ICDQ and can be called from any source system.

---

## When to use this skill vs `/cdgc-client-setup`

| Situation | Use |
|-----------|-----|
| Client wants DQ rules callable from any source (Databricks, Salesforce, etc.) | `/cdgc-dq-rules` — standalone, no CDGC required |
| Client wants DQ rules connected to CDGC governance + MCC scoring | `/cdgc-client-setup` — generates DQ rules as part of the full 14-file package |
| Client already has CDGC set up and just needs rules built | `/cdgc-dq-setup` — connects existing ICDQ rules to the CDGC pipeline |

**Key distinction:** Standalone rules are independent of CDGC. They execute on demand via REST API against any data source — no catalog source, no MCC scan, no occurrences required. This is the right path when a customer has ICDQ but has not yet deployed CDGC, or wants rules that run outside the MCC scan cycle.

---

## Intake

When invoked, greet the user:

```
Welcome to the DQ Rules Generator!

I'll analyze your client's data and produce a Claire-ready rules file —
with recommended rules, pre-drafted logic, and regulatory drivers.

What do you have? Provide as many as you have — more context = better rules:

  A. Schema / DDL — Snowflake SHOW COLUMNS output, SQL CREATE TABLE, or data dictionary (CSV or Excel)
  B. Sample rows — 10–100 rows of actual data (CSV or Excel)
  C. Profile results — null %, distinct count, min/max, top values (MCC export or manual)
  D. Existing rule specs — prior DQ rules, SLA docs, or data quality standards
  E. Policy / regulatory docs — HIPAA, BCBS 239, SOX, KYC requirements, etc.

You don't need all of these — even a schema alone is enough to get started.

Also:
  - Client/project name (used for the file prefix)
  - Output directory (default: ~/Downloads/)
```

Wait for the user's response before proceeding.

---

## Step 1 — Parse inputs

Write and execute a Python script to parse each provided input and extract DQ signals per column.

### From schema / DDL
- Column name, data type, nullable flag, primary key flag
- Table name and schema — used for domain grouping and Rule_ID prefix assignment
- Inline comments or descriptions if present

### From sample rows
- Null rate per column (nulls / total rows)
- Distinct value count and ratio (distinct / total)
- For numeric columns: min, max, mean
- For string columns: min/max length, common format patterns (regex candidates)
- For date columns: whether any values are in the future
- Enum detection: if distinct count ≤ 20, capture all unique values as candidate valid value set

### From profile results
- Accept MCC profile export format: Table, Column, NullCount, DistinctCount, MinValue, MaxValue, TopValues
- Also accept any reasonable tabular format — infer column mapping by header name
- Null % drives completeness rule candidates
- Min/Max drives range validity candidates
- TopValues drives valid value set candidates

### From existing rule specs
- Extract: rule name, column(s) targeted, condition, severity, regulatory reference
- Use as anchors — prefer existing names over generated ones

### From policy / regulatory docs
- Extract regulatory frameworks referenced (HIPAA, SOX, BCBS 239, GDPR, KYC, etc.)
- Map to column names where possible — these populate the `Regulatory_Driver` column

Print extraction summary:
```
Signals extracted:
  Tables: N  |  Columns analyzed: N
  Null rate signals: N columns
  Range signals: N columns
  Format/pattern signals: N columns
  Valid value set signals: N columns
  Existing rules found: N
  Regulatory drivers mapped: N columns

Recommended rules: N
  Completeness: N  |  Validity: N  |  Consistency: N  |  Uniqueness: N  |  Timeliness: N
```

---

## Step 2 — Generate rule recommendations

Apply these patterns based on available signals:

### Completeness
**Trigger:** null rate > 0% on a column that appears critical (PK, FK, code field, regulatory field)
**Logic:** `{COLUMN} IS NOT NULL`
**Severity:** Critical if PK or regulatory driver present, High otherwise

### Validity — range
**Trigger:** numeric column with min/max from profile or sample
**Logic:** `{COLUMN} BETWEEN {min} AND {max}`
**Note:** Mark `[REVIEW]` — observed range is a starting point, not a validated constraint. SE must confirm before handing to Claire.

### Validity — format
**Trigger:** string column where sample values show a consistent pattern
**Patterns detected:**
- 9-digit numeric strings → `REGEXP_LIKE({COL}, '^[0-9]{9}$')` (SSN)
- ISO date strings → `TRY_TO_DATE({COL}) IS NOT NULL`
- Email → `REGEXP_LIKE({COL}, '^[^@]+@[^@]+\.[^@]+$')`
- ICD-10 → `REGEXP_LIKE({COL}, '^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$')`
- NPI (10-digit) → `REGEXP_LIKE({COL}, '^[0-9]{10}$')`
- 3-letter uppercase → `LENGTH({COL}) = 3 AND {COL} = UPPER({COL})` (currency code)

### Validity — valid value set
**Trigger:** enum detection (distinct count ≤ 20)
**Logic:** `{COLUMN} IN ('{val1}', '{val2}', ...)`
**Note:** Mark `[REVIEW]` — observed values may not be the complete valid set.

### Validity — date not future
**Trigger:** date column with event-type name (ENCOUNTER_DATE, BIRTH_DATE, TRANSACTION_DATE, etc.)
**Logic:** `{COLUMN} <= CURRENT_DATE()`

### Uniqueness
**Trigger:** column named ID/KEY or distinct count ≈ total rows
**Logic:** `COUNT(*) = COUNT(DISTINCT {COLUMN})`

### Consistency
**Trigger:** two columns that should balance (debit/credit, begin/end date, amount/total)
**Logic:** `{COL_A} = {COL_B}` or `{COL_A} <= {COL_B}`

---

## Step 3 — Generate {PREFIX}_IDQ_Rules.xlsx

Write and execute a Python/openpyxl script to produce the output file.

**File:** `{PREFIX}_IDQ_Rules.xlsx`
**Location:** user-specified directory or `~/Downloads/`

### Sheet 1: `DQ Rules` — 10 columns (exact order)

| Column | Content |
|--------|---------|
| `Rule_ID` | Category prefix + sequence (e.g. `PAT-001`, `CUST-001`) |
| `Category` | Completeness / Validity / Consistency / Uniqueness / Timeliness |
| `Rule_Name` | Generated from pattern (e.g. `Patient ID Not Null`, `ICD-10 Code Format Validity`) |
| `Description` | Plain-English description of what the rule validates and why |
| `Target_Fields` | Snowflake column name(s) |
| `Rule_Logic` | Pre-drafted SQL. Mark `[REVIEW]` if derived from observed data. |
| `Severity` | Critical / High / Medium / Low |
| `Regulatory_Driver` | Framework from policy docs. Blank if none found. |
| `Pass_Example` | Example of a passing value |
| `Fail_Example` | Example of a failing value |

### Sheet 2: `Summary` — rule count by dimension and confidence

### Color coding
- White — high confidence, logic ready for Claire
- Light yellow (`FFFFE0`) — medium confidence, review recommended
- Light orange (`FFD580`) — logic derived from observed data — SE must confirm
- Light red (`FFB3B3`) — low confidence / placeholder only

### Rule_ID category prefix conventions

**Healthcare:** PAT (patient), ENC (encounters), LAB (lab results), MED (medications), AI (model outputs), PHI (compliance)

**Financial Services:** CUST (customer/KYC), TXN (transactions), GL (general ledger), RISK (risk exposure), REG (regulatory), MDL (model outputs)

For other verticals: derive 2–4 letter prefix from domain name, confirm with user before generating.

---

## Step 4 — Present results and next steps

Print:
```
✓ Generated: {PREFIX}_IDQ_Rules.xlsx  ({N} rules)
  Ready for Claire: {N}  (white + yellow rows)
  Needs SE review:  {N}  (orange + red rows)

Rules marked [REVIEW]:
  [list columns where range/enum logic was inferred from observed data]
  [list any rules where valid constraint is unknown — confirm before use]
```

Then:
```
Next steps:

  1. Open {PREFIX}_IDQ_Rules.xlsx — review any [REVIEW] rows and confirm Rule_Logic
  2. Open ICDQ → create a project and folder for this client
  3. Open Claire → provide all rule definitions from the DQ Rules sheet at once (not one by one)
  4. For each rule Claire builds: verify the output port is named 'Output' exactly
  5. In ICDQ API Center: enable each rule for API access
  6. Rules are now callable as REST endpoints from any source system

To connect these rules to CDGC governance and get scores on every MCC scan instead,
run /cdgc-client-setup — it generates the same rules file as part of the full 14-file package.
```
