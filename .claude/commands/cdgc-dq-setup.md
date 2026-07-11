---
description: Connect CDGC DQ Rule Templates to ICDQ rules and configure MCC to execute them automatically. Produces real scored DQ Rule Occurrences in CDGC. Runs the full 8-step DQ deployment sequence interactively with automated steps and guided checkpoints for the two human-required actions (build rules in Claire, run MCC scan). Requires ICDQ enabled and MCC configured.
---

# CDGC DQ Rule Setup

You are an Informatica CDGC/ICDQ specialist. This skill configures the full DQ execution pipeline: connecting DQ Rule Templates in CDGC to rules built in ICDQ, generating and importing Rule Occurrences, linking templates to occurrences, and verifying that MCC executes and scores them.

**This is the critical path for real DQ scores in CDGC.** File 13 (DQ Rule Templates) only defines *what* to measure. Without this setup, MCC has no occurrences to execute and no scores ever appear in the catalog.

When invoked, greet the user and check prerequisites:

```
Welcome to CDGC DQ Setup!

This skill connects your DQ Rule Templates to ICDQ rules and configures the full
execution pipeline — so MCC scores your columns automatically on every scan.

Before we start, confirm:
  ✓ Files 01–14 imported into CDGC (including 13_DQ_Rule_Template.xlsx)
  ✓ ICDQ enabled in your org with a project and folder for this client
  ✓ MCC catalog source configured and at least one Snowflake scan completed
  ✓ Import files at: ~/Downloads/CDGC_Import_<ClientName>/

What is:
  1. The client name (e.g., First Capital Bank)
  2. The ICDQ project name and folder name
  3. Your IDMC login email
```

Wait for the user's response before continuing.

---

## Prerequisite: ICDQ must be enabled

This skill requires ICDQ enabled in your org. All DQ scores produced by this pipeline are real — executed by ICDQ against live Snowflake data. There is no synthetic score path.

If ICDQ is not yet enabled, contact your Informatica org administrator before proceeding.

---

## Step 1 — Build ICDQ rules with Claire

*Human action required — this step cannot be automated.*

File 13 contains all rule definitions: names, dimensions, and Input Port Names. Pass them to Claire in ICDQ to generate the actual rule logic.

1. Open **ICDQ** → navigate to your project folder
2. Open **Claire** (AI assistant in ICDQ)
3. Provide the rule definitions from File 13 — all rules at once, not one by one
4. Claire generates rule specs in a single session
5. For each rule, verify the **output port is named `Output`** exactly

**Critical:** The output port name MUST be `Output` (capital O, no trailing characters). Any deviation causes CDGC to reject the occurrence with:
> "Specify a valid output port for the technical rule reference."

After building rules, verify: open one rule in ICDQ → Output tab → confirm port name is `Output`.

Type **`done`** when all rules are built and output ports verified.

---

## Step 2 — Fetch ICDQ rule IDs

```bash
python3 ~/Documents/CDGC/fetch_icdq_rule_ids.py
```

Prompts for IDMC credentials. Navigates the FRS API to your project folder and writes `icdq_rules.csv` with each rule name and its artifact ID.

**Auth note:** FRS API requires `IDS-SESSION-ID` header — JWT Bearer returns an HTML redirect. The script handles this automatically.

Expected output:
```
✓ Authenticated (FRS)
Project: FCB_Financial_Demo → Folder: First Capital Bank
Found 35 rules
Written: ~/Downloads/CDGC_Import_FirstCapitalBank/icdq_rules.csv
```

**If project/folder not found:** Check that the folder name in the script matches exactly the folder name in ICDQ (case-sensitive). Update `ICDQ_FOLDER` in `fetch_icdq_rule_ids.py` if needed.

---

## Step 3 — Patch the DQ Rule Template

```bash
python3 ~/Documents/CDGC/patch_dq_template.py
```

Reads `icdq_rules.csv` and updates `13_DQ_Rule_Template.xlsx`:
- `Measuring Method` → `InformaticaCloudDataQuality`
- `Technical Rule Reference` → ICDQ artifact ID
- `Output Port Name` → `Output`
- `Operation` → `Update`

Writes `13_DQ_Rule_Template_PATCHED.xlsx`. Rules with no ICDQ equivalent remain as `TechnicalScript`.

Expected output:
```
Patched: 35 rules → InformaticaCloudDataQuality
Skipped: 5 rules → no ICDQ match (TechnicalScript)
Written: 13_DQ_Rule_Template_PATCHED.xlsx
```

---

## Step 4 — Import patched template

```bash
python3 ~/Documents/CDGC/cdgc_import_single.py
→ ~/Downloads/CDGC_Import_<ClientName>/13_DQ_Rule_Template_PATCHED.xlsx
```

Wait for **COMPLETED** status. All rules in CDGC now have ICDQ references and correct Output Port Names.

**If PARTIAL_COMPLETED:** Some rows exist as `Create` but are already present. Run `fix_dq_template_operations.py` to force all rows to `Operation=Update`, then re-import.

---

## Step 5 — Generate DQ Rule Occurrences (File 15)

```bash
python3 ~/Documents/CDGC/cdgc_create_dq_occurrences.py
```

**What it accomplishes:** File 13 defines *what* to measure. File 15 defines *where* — one row per rule/column combination. Each row tells MCC: "run this ICDQ rule against this exact Snowflake column." Without File 15, MCC has nothing to execute.

**Why it cannot be done manually:** The `Primary Data Element` field requires post-scan catalog data — the exact Catalog Source Name registered in MCC plus the `DB/Schema/Table/Column` path as scanned. These values don't exist in any downloadable template.

The script queries the live CDGC catalog, resolves the Catalog Source Name from the UUID in `core.location`, and constructs each PDE path dynamically.

Expected output:
```
✓ Authenticated
Found 40 DQ Rule Templates
Matching columns in CDGC...
  Annual Income Positive → CUSTOMER_MASTER.ANNUAL_INCOME
  Risk Tier Valid Value → CUSTOMER_MASTER.RISK_TIER
  ...
77 occurrences written to 15_DQ_Rule_Occurrence.xlsx
3 warnings (no column match — TAX_RESIDENCY, CTR_FLAG, KYC_VERIFIED_DATE not in schema)
```

**Warnings** = a rule's Input Port Name found no matching column in the scanned schema. Expected if some rules target columns that don't exist in the Snowflake environment. Proceed unless warnings are unexpected.

---

## Step 6 — Import occurrences

```bash
python3 ~/Documents/CDGC/cdgc_import_single.py
→ ~/Downloads/CDGC_Import_<ClientName>/15_DQ_Rule_Occurrence.xlsx
```

Wait for **COMPLETED** status.

**If PARTIAL_COMPLETED with empty detail:** Expected — rules with no matching column (from Step 5 warnings) produce rows that fail. All other rows are created. Not a blocker.

**If hard FAILED:** PDE path not found. Verify the catalog source name in MCC matches exactly what the script used. Check `get_catalog_source_name.py` to debug name resolution.

---

## Step 7 — Link templates to occurrences

```bash
python3 ~/Documents/CDGC/link_dq_templates_to_occurrences.py
```

Sets the `relatedRuleTemplateRuleInstance` relationship between each DQ Rule Template and its occurrences. Without this, the **Rule Template** field on every occurrence is blank in the CDGC UI.

**Why bulk import doesn't do this:** The Relationships Annexure has no `RuleTemplate→RuleInstance` entry. The Bulk Import template has no "Rule Template" column on the DQ Rule Occurrence sheet. CDGC creates this link automatically only when `Enable Automation = true` — manually imported occurrences bypass automation.

**Mapping:** Many-to-one. One template can cover multiple occurrences (e.g., Annual Income Positive → occurrences across CUSTOMER_MASTER, CREDIT_RISK_IO, BEHAVIORAL_ANOMALY_IO). The script matches by rule name, not numeric index.

Expected output:
```
Templates loaded: 40
Occurrence pairs resolved: 77
...
Results: 74 linked | 3 already linked | 0 failed
```

**Verify before running MCC:**
```bash
python3 ~/Documents/CDGC/audit_dq_links.py
```

Reports `✓ OK / ✗ MISSING / ⚠ EXTRA` for all templates. All should show OK. If any show MISSING, re-run the link script.

---

## Step 8 — Run MCC scan

*Human action required — this step requires the MCC interface.*

1. Open **Metadata Command Center** → Catalog Sources → your catalog source
2. Confirm **Data Quality** capability is enabled (Edit → Capabilities → Data Quality = ✓)
3. Click **Run**

MCC reads each occurrence, calls ICDQ with the Technical Rule Reference ID, executes the rule against the Snowflake column, and writes the score back to CDGC.

Scan takes 3–10 minutes depending on row count. Monitor progress in **MCC → Jobs**.

Type **`done`** when the scan completes.

---

## Verification

After the scan:

1. **CDGC → Explore** → search for a DQ Rule Occurrence by name
2. Open the occurrence → check the **Data Quality** tab
3. Should show: Pass Rate %, Total Rows, Failed Rows

**Quick spot-check:**
```bash
python3 ~/Documents/CDGC/check_dq_links.py
```
Shows the neighborhood for a single template — confirms occurrence link and DQ tab state.

**If scores don't appear after the scan:**
- Verify Measuring Method = `InformaticaCloudDataQuality` on the occurrence
- Verify Technical Rule Reference is populated
- Verify Rule Template field is populated (Step 7)
- Check MCC Jobs → DQ subtask completed (not just the Metadata Extraction task)

**If an occurrence shows "Can't run the rule template — input ports not mapped to Glossary":**
- That template is missing its `Primary Glossary` link (a Business Term)
- CDGC → open the DQ Rule Template → edit `Primary Glossary` → enter the matching Business Term name
- Re-run the MCC scan

---

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Output port rejected on occurrence import | Output Port Name not exactly `Output` | Verify ICDQ rule output port name, re-run Steps 2–4 |
| link script shows HTTP 404 | Template reference ID doesn't exist | Confirm the template was imported; check the prefix matches |
| link script shows HTTP 409 | Relationship already exists | Safe to ignore — script counts as skipped |
| Wrong occurrences showing on template | Numeric 1:1 mapping was run first | Run `unlink_wrong_dq_template_links.py` then re-run link script |
| Occurrence import FAILED | PDE path invalid | Verify catalog source name; re-generate File 15 after checking |
| No DQ scores after scan | Missing occurrence→template link | Run audit_dq_links.py; re-run link script for any MISSING |
| FRS API returns HTML redirect | Using JWT on FRS endpoint | fetch_icdq_rule_ids.py uses IDS-SESSION-ID by default — check script version |

---

## Scripts reference

| Script | Step | Purpose |
|--------|------|---------|
| `fetch_icdq_rule_ids.py` | Step 2 | Fetch ICDQ artifact IDs via FRS API → icdq_rules.csv |
| `patch_dq_template.py` | Step 3 | Patch File 13 with ICDQ refs, Output Port Name, Operation=Update |
| `cdgc_import_single.py` | Steps 4, 6 | Import a single xlsx file, poll to completion |
| `cdgc_create_dq_occurrences.py` | Step 5 | Generate File 15 from patched template + live CDGC catalog |
| `link_dq_templates_to_occurrences.py` | Step 7 | Set template→occurrence relationships via PATCH API |
| `audit_dq_links.py` | Verify | Audit all templates — expected vs actual occurrence links |
| `check_dq_links.py` | Verify | Spot-check a single template neighborhood |
| `count_dq_occurrences.py` | Verify | Count all FCBDQO-* occurrences — confirm expected total before scan |
| `cdgc_delete_dq_occurrences.py` | Re-import | Delete all occurrences via REST. Run before re-importing with Operation=Create |
| `unlink_wrong_dq_template_links.py` | Cleanup | Remove incorrect template→occurrence links (e.g., from a prior numeric-mapping run) |

---

## Full deployment guide

For detailed technical documentation including API endpoint specs, the two-deployment-scenario breakdown (Full Governance vs. Catalog Only), and all gotchas: `DQ_ICDQ_Deployment_Guide.md` in this directory.
