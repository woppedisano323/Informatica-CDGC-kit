# CDGC Architecture Reference

> **What this is:** A mental model document — not a how-to. It explains *why* CDGC is built the way it is, why each piece depends on the one before it, and why the common mistakes happen. Read this once and the rest of the guides make sense.

---

## The Three-Layer Stack

CDGC is not one system — it's three systems that depend on each other:

```
┌─────────────────────────────────────────────────────┐
│  CDGC  —  Governance Layer                          │
│  Domains, Terms, Policies, Regulations, DQ Rules    │
│  "What things mean, who owns them, what rules apply"│
└──────────────────────┬──────────────────────────────┘
                       │ MCC writes metadata + scores up here
┌──────────────────────▼──────────────────────────────┐
│  MCC  —  Technical Catalog Layer                    │
│  Scanned databases, tables, columns, lineage        │
│  "What physically exists in your data systems"      │
└──────────────────────┬──────────────────────────────┘
                       │ MCC calls ICDQ to execute rules
┌──────────────────────▼──────────────────────────────┐
│  ICDQ  —  Rule Execution Layer                      │
│  Rule logic, input/output ports, execution engine   │
│  "How to actually test whether data is good"        │
└─────────────────────────────────────────────────────┘
```

**The dependency flows upward.** You cannot score a column without a scanned column (MCC). You cannot execute a rule without an ICDQ artifact. You cannot link governance context to a score without Business Terms and Policies already in CDGC. This is why the setup sequence exists — it's not bureaucratic, it's architectural.

---

## The Import File Sequence — Why Order Matters

The 14 import files (01–14) are not arbitrary. Each file creates assets that later files reference. CDGC enforces referential integrity: if you try to import a Business Term before its Domain exists, the import fails.

```
01 Domain           ← root governance container
02 Subdomain        ← requires Domain
03 Regulation       ← standalone, but referenced by Policy
04 Policy           ← requires Regulation + Domain
05 Legal Entity     ← standalone
06 Business Area    ← requires Legal Entity
07 Geography        ← standalone
08 System           ← data source (e.g. "Snowflake Production")
09 AI System        ← requires System
10 AI Model         ← requires AI System
11 Business Term    ← requires Domain, Subdomain, Policy
12 Data Set         ← requires System, Business Term
13 DQ Rule Template ← requires Business Term (Primary Glossary)
14 Relationships    ← links everything together
```

**Why this matters later:** File 13 (DQ Rule Template) has a `Primary Glossary` field. That field links the rule to a Business Term — which is what enables CDGC to trace a DQ failure back to a Policy and Domain owner. If Business Terms (File 11) don't exist yet, `Primary Glossary` stays blank, and you get the error: *"Can't run the rule template — input ports not mapped to Glossary"* when MCC tries to execute the rule.

---

## Reference IDs — What They Are and When They Matter

Every asset you import must have a `Reference ID`. This is the external identifier that CDGC uses to reference the asset across files and API calls.

**The UUID question:** CDGC assigns an internal UUID (e.g. `a6SFXtekQAhjnxRmm8wYqe`) to every asset after import. This UUID is what the internal APIs use — the Search API returns it, the relationship PATCH API accepts it as `{assetId}`. Your human-readable Reference ID (e.g. `FCBBT-1`) and the CDGC UUID coexist. Most API calls can use either `?scheme=external` (Reference ID) or the raw UUID path.

**When the UUID matters:**
- Phase 3b of the DQ occurrence pipeline — the PATCH endpoint uses `scheme=external` with your Reference ID
- MCC lineage views — MCC resolves catalog source UUIDs internally; `verify_pdes.py` can break on sub-orgs because it tries to reverse-lookup the UUID and gets the raw UUID back instead of the display name
- The FRS API (ICDQ rule IDs) — returns artifact IDs that look like UUIDs and must be stored exactly as returned; these become `Technical Rule Reference` in File 13

**Rule of thumb:** Your Reference IDs are for you and for the import files. UUIDs are for API calls. Keep both, but know which one an endpoint expects.

---

## Business Terms — Why They Are the Foundation

Business Terms (File 11) are the central node in the governance graph. Everything meaningful connects through them:

```
Policy ──────────────┐
Domain ──────────────┼──► Business Term ◄─── DQ Rule Template (Primary Glossary)
Regulation ──────────┘         │
                               │
                         Data Set / Column (MCC links here after scan)
```

**Why they matter for DQ specifically:**

A DQ Rule Template has a `Primary Glossary` field that points to a Business Term. When MCC executes a DQ rule and produces a score, it attributes that score to the column — and through the column to the Business Term — and through the Business Term to the Policy and Domain. This is what makes the DQ story real in a demo: a failing DQ score is not just a number, it is a traceable policy violation with an owner.

If `Primary Glossary` is blank when MCC runs, the rule still executes and scores — but CDGC cannot complete the governance chain. In a customer demo, the score appears orphaned.

**The other reason Business Terms matter:** MCC's auto-classification uses them. When MCC scans a Snowflake column named `DATE_OF_BIRTH`, it looks for a Business Term with that name (or similar) and suggests a link. If Business Terms are rich and well-named, classification becomes mostly automatic. If they're sparse or generic, every column needs manual linking.

---

## The Data Catalog (MCC) — What a Scan Actually Does

When you click Run in MCC, it executes up to five distinct tasks in sequence:

```
1. Metadata Extraction     — reads table/column names, data types, constraints
2. Data Profiling          — samples rows: min, max, null%, distinct count, frequency
3. Data Classification     — matches column names/samples to Business Terms and PII tags
4. Data Quality            — reads DQ occurrences, calls ICDQ, writes scores back
5. Lineage Discovery       — parses SQL views to build column-level data lineage
```

Each task is independent. You can run Metadata Extraction without DQ. But DQ requires that Metadata Extraction has run at least once — the scanned column assets must exist in CDGC before File 15 (DQ Rule Occurrences) can reference them.

**Why scan order matters for DQ:** The `Primary Data Element` field in File 15 contains:

```
<CatalogSourceName>://<Database>/<Schema>/<Table>/<Column>
```

The `CatalogSourceName` is the name you registered in MCC (e.g. `FCB_Financial_Snowflake`). The `Database/Schema/Table/Column` path is exactly what MCC cataloged during Metadata Extraction. If you generate File 15 before the scan, none of those paths exist yet and every import row fails. This is why `cdgc_create_dq_occurrences.py` queries the live CDGC catalog at runtime — it cannot be pre-filled.

**What MCC is NOT:** MCC is not a query engine. It does not hold data. It scans, catalogs, and delegates — Metadata Extraction reads schemas, DQ delegates execution to ICDQ, Lineage reads SQL text from views. All results are written back to CDGC as asset attributes.

---

## DQ Rule Templates vs. DQ Rule Occurrences — The Core Distinction

This is the most important concept to internalize. It is also the most commonly confused.

| | DQ Rule Template (File 13) | DQ Rule Occurrence (File 15) |
|---|---|---|
| **What it is** | The rule definition — what to measure and how | The execution instance — where to apply the rule |
| **Analogous to** | A test specification | A test execution record |
| **How many** | One per business rule | One per rule/column combination |
| **Created by** | `/cdgc-setup` skill | `cdgc_create_dq_occurrences.py` (post-scan) |
| **Key field** | `Input Port Name` — column name to target | `Primary Data Element` — exact column path |
| **ICDQ artifact** | `Technical Rule Reference` — the ICDQ rule ID | Inherited from template |
| **MCC reads this?** | No — MCC reads Occurrences | Yes — this is what MCC executes |

**The many-to-one relationship:** One template can produce many occurrences. A rule named "Date of Birth Valid" with `Input Port Name = DATE_OF_BIRTH` will produce one occurrence for every table in the scanned schema that has a `DATE_OF_BIRTH` column. This is why 40 templates in the FCB environment produced 77 occurrences — many rules applied to multiple tables.

**Why File 15 cannot be downloaded from the CDGC GUI:** The Bulk Import template in CDGC includes a DQ Rule Occurrence sheet — but it has no mechanism to pre-populate the `Primary Data Element` field. That field requires the scanned catalog path, which only exists after MCC runs. There is no workaround for this. The script is the only practical way to generate it at scale.

---

## The relatedRuleTemplateRuleInstance Relationship — Why It Doesn't Auto-Create

After you import File 15 successfully, every occurrence exists as an asset in CDGC. But the **Rule Template** field on each occurrence is blank. This is the link between the template and its occurrences — and bulk import does not create it.

**Why not?** CDGC creates this link automatically only when `Enable Automation = true` is set on the template. That setting tells CDGC: "whenever a new occurrence matching this template appears, link it automatically." Manually imported occurrences bypass this automation path — they arrive via the bulk import API, not through the automation engine.

**What happens without the link:** In the CDGC UI, the DQ Rule Occurrence shows an empty **Rule Template** field. In a demo, this looks broken. More critically, it means you can't navigate from an occurrence back to its template — the governance chain is incomplete.

**How to create it:** A `PATCH` call per occurrence:

```
PATCH /data360/content/v1/assets/{templateRefId}?scheme=external

[{"operation": "add", "segment": "relationship",
  "items": [{"fromExternalIdentity": "<template-ref-id>",
             "toExternalIdentity":   "<occurrence-ref-id>",
             "association": "com.infa.ccgf.models.governance.relatedRuleTemplateRuleInstance"}]}]
```

HTTP 409 means the link already exists — safe to ignore. `cdgc_create_dq_occurrences.py` Phase 3b does this automatically for all occurrences after import. `link_dq_templates_to_occurrences.py` is the standalone fallback if Phase 3 failed.

---

## ICDQ and Claire — Why This Step Is a Human Gate

ICDQ is where rule logic actually lives. A DQ Rule Template in CDGC says "measure completeness of DATE_OF_BIRTH." ICDQ is where the actual SQL or expression that implements that test is defined and compiled.

**Why Claire is required:** Claire is ICDQ's AI assistant. Given a rule definition (name, description, dimension, Input Port Name), Claire generates the rule specification — the actual expression logic. This cannot be scripted today because:

1. Claire interprets natural-language rule descriptions to produce correct logic
2. The output requires human review — Claire can misinterpret ambiguous descriptions
3. The output port must be named exactly `Output` — this has to be verified per rule

**The artifact ID is what connects CDGC to ICDQ:** After Claire builds the rules, `fetch_icdq_rule_ids.py` navigates the FRS API to retrieve each rule's artifact ID. That ID becomes the `Technical Rule Reference` field in the patched File 13. When MCC reads a DQ Occurrence during a scan, it extracts `Technical Rule Reference`, calls ICDQ's execution API with that ID, and ICDQ runs the rule against the column data. The score returned is written back to CDGC.

**The FRS API vs. the IDMC JWT API:** These are different auth contexts. Standard CDGC API calls use `Authorization: Bearer <JWT>`. The FRS API (which exposes ICDQ project structure) requires `IDS-SESSION-ID`. Using a JWT on an FRS endpoint returns an HTML redirect — it does not fail with an auth error, it silently returns the wrong thing. This is a common source of confusion.

---

## Lineage — How MCC Builds It and Why Views Matter

Column-level data lineage in CDGC comes from MCC parsing SQL view definitions. This is why the Snowflake schemas include lineage views like `V_SEPSIS_TRAINING_PIPELINE` and `V_FRAUD_TRAINING_PIPELINE` — they are not for querying, they are for lineage discovery.

```sql
-- MCC reads this view definition and builds:
-- SEPSIS_RISK_FEATURES.HEART_RATE → SEPSIS_RISK_IO.HEART_RATE (column-level lineage)
CREATE VIEW MODEL_REGISTRY.V_SEPSIS_TRAINING_PIPELINE AS
  SELECT sf.HEART_RATE, sf.LACTATE_LEVEL ...
  FROM TRAINING_DATA.SEPSIS_RISK_FEATURES sf
```

MCC parses the SQL text of each view during the Lineage Discovery task, walks the column references, and creates lineage edges in CDGC. The result: in CDGC you can see that a model output column traces back to specific feature columns, which trace back to source tables. For AI assets (AI Models, AI Systems imported in Files 09 and 10), this lineage is what makes the AI governance story tangible — you can show exactly where a model's training data came from.

**Why this requires Lineage Discovery capability to be enabled in MCC:** Metadata Extraction only reads table/column structure. Lineage is a separate task that requires parsing SQL. If you run a scan without enabling Lineage Discovery, no lineage edges are created.

---

## The Complete Flow — Start to Finish

```
1. /cdgc-setup
   Generate 14 import files for the vertical
   Files 01–10: governance foundation (Domains → AI Models)
   File 11: Business Terms — the central governance node
   File 12: Data Sets — connects systems to governance
   File 13: DQ Rule Templates — defines what to measure
   File 14: Relationships — wires the governance graph
   Import 01 → 14 in order, wait for COMPLETED each time

2. /cdgc-technical-setup
   Run cdgc_snowflake_setup.py — creates Snowflake schemas + loads realistic data
   Create MCC catalog source (Snowflake connection)
   Run MCC scan: Metadata Extraction + Profiling + Classification + Lineage
     → Snowflake columns now exist as assets in CDGC
     → Business Terms get suggested links to columns (auto-classification)
     → Lineage edges built from view SQL
   Link columns to Business Terms (validate or accept MCC suggestions)

3. /cdgc-dq-setup
   Step 1: Build ICDQ rules with Claire  ← human gate
     → Claire generates rule logic from File 13 definitions
     → Verify output port = "Output" on each rule
   Step 2: fetch_icdq_rule_ids.py  → icdq_rules.csv
   Step 3: patch_dq_template.py   → File 13 patched with ICDQ artifact IDs
   Step 4: Import patched File 13  → rules now have Technical Rule Reference
   Step 5: cdgc_create_dq_occurrences.py
     Phase 1: query live CDGC catalog → build File 15 (one row per rule/column)
     Phase 2: CONFIRM prompt
     Phase 3a: import File 15 via API → poll to COMPLETED
     Phase 3b: PATCH all relatedRuleTemplateRuleInstance relationships
   Step 6: Run MCC scan (enable Data Quality capability)  ← human gate
     → MCC reads each occurrence → calls ICDQ → score returned → written to column
     
4. Result
   CDGC column asset → Data Quality tab → real pass rate %
   Score traceable: Column → Business Term → Policy → Domain → Owner
```

---

## Why Each Step Enables the Next

| Step completed | What it unlocks |
|---|---|
| Files 01–07 imported | Governance taxonomy exists — Terms have somewhere to belong |
| Files 08–10 imported | Systems and AI assets exist — Data Sets can reference them |
| File 11 imported | Business Terms exist — DQ Templates can have Primary Glossary; MCC can auto-classify |
| File 12 imported | Data Sets exist — bridge between governance and technical catalog |
| File 13 imported | DQ Rule Templates exist — but MCC cannot execute them yet (no ICDQ refs, no Occurrences) |
| MCC scan completed | Column assets exist — File 15 PDE paths can be constructed; Business Term links can be validated |
| ICDQ rules built | Artifact IDs available — templates can be patched |
| File 13 patched + reimported | Technical Rule Reference populated — MCC now knows which ICDQ rule to call |
| File 15 imported + linked | Occurrences exist with full governance chain — MCC can execute and score |
| MCC DQ scan | Scores written — governance chain complete, DQ tab populated |

---

## Common Mistakes and Why They Happen

| Mistake | Why it happens | What to check |
|---|---|---|
| File 15 import fails entirely | Generated before MCC scan — PDE paths don't exist yet | Always run Metadata Extraction scan before generating File 15 |
| "Specify a valid output port" on occurrence import | ICDQ rule output port is not named `Output` exactly | Open rule in ICDQ → Output tab → rename port |
| Rule Template field blank on occurrence | Phase 3b didn't run or failed | Run `link_dq_templates_to_occurrences.py` |
| DQ scores never appear after scan | Measuring Method = TechnicalScript, not InformaticaCloudDataQuality | Re-run patch_dq_template.py and reimport File 13 |
| "Can't run rule — input ports not mapped to Glossary" | Primary Glossary blank on the DQ Rule Template | Open template in CDGC → edit Primary Glossary → add Business Term |
| FRS API returns HTML | Using JWT Bearer on FRS endpoint | Use IDS-SESSION-ID header for all FRS/ICDQ calls |
| PARTIAL_COMPLETED on File 15 import | Some Input Port Names matched no scanned column | Expected — those rules have no matching column. All other rows created. |
| Wrong occurrences linked to template | Numeric index matching was used instead of name-based | Run `unlink_wrong_dq_template_links.py`, then re-run link script |
| Lineage not appearing in CDGC | Lineage Discovery capability not enabled in MCC | Edit catalog source → Capabilities → enable Lineage Discovery → re-scan |
| Business Term auto-classification suggestions missing | Scan completed but Terms don't match column name patterns | Review Business Term naming — column name and term name should align |

---

## Key Vocabulary Quick Reference

| Term | What it means in practice |
|---|---|
| **Catalog Source** | The named connection registered in MCC — not the database. `FCB_Financial_Snowflake` is a Catalog Source; `TEST_DB` is the database it points to. The Catalog Source Name is what appears in PDE paths. |
| **Primary Data Element (PDE)** | The full path to a physical column: `CatalogSource://DB/Schema/Table/Column`. Required on every DQ Occurrence. Can only be constructed after a scan. |
| **Reference ID** | Your human-readable external identifier (e.g. `FCBBT-1`). Used in import files and `?scheme=external` API calls. |
| **UUID** | CDGC's internal identifier assigned at import time. Required for some API calls where `scheme=external` is not available. |
| **Technical Rule Reference** | The ICDQ artifact ID stored on a DQ Rule Template. MCC passes this ID to ICDQ's execution engine when running a scan. |
| **Input Port Name** | The column name a DQ rule targets — must match the actual Snowflake column name exactly (case-insensitive). This is why Snowflake schema column names must be defined before writing DQ rules. |
| **Output Port Name** | Must be `Output` (capital O) on every ICDQ rule. Non-negotiable — any other value causes CDGC to reject the occurrence. |
| **Enable Automation** | When true on a DQ Rule Template, CDGC auto-links new occurrences to the template. Manually imported occurrences bypass this. |
| **FRS API** | Informatica's internal file/rule storage API — used to navigate ICDQ project structure and retrieve artifact IDs. Requires `IDS-SESSION-ID` auth, not JWT. |
| **PARTIAL_COMPLETED** | An import job status meaning some rows succeeded and some failed. Not always an error — expected on File 15 when some Input Port Names have no matching scanned column. |
