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
  1. The client name (e.g., Acme Financial)
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
python3 ~/Documents/CDGC/fetch_icdq_rule_ids.py --client <client> --csv
```

Replace `<client>` with the config name (e.g., `mhn`, `fcb`). Loads FRS host, project, and folder from `clients/<client>.json` — no manual prompts. Writes `icdq_rules.csv` to the script directory.

**Auth note:** FRS API requires `IDS-SESSION-ID` header — JWT Bearer returns an HTML redirect. The script handles this automatically.

Expected output:
```
✓ Loaded config: Meridian Health Network
✓ Authenticated
Project: MHN_Healthcare_Demo → Folder: Meridian Healthcare Network
Found 11 rules
✓ Written to .../icdq_rules.csv
```

**If project/folder not found:** Names are case-sensitive. Verify exact spelling in ICDQ before re-running.

---

## Step 3 — Patch the DQ Rule Template

```bash
python3 ~/Documents/CDGC/patch_dq_template.py --client <client>
```

Reads `icdq_rules.csv` and updates `13_DQ_Rule_Template.xlsx`:
- `Measuring Method` → `InformaticaCloudDataQuality`
- `Technical Rule Reference` → ICDQ artifact ID
- `Output Port Name` → `DQ_RESULT`
- `Operation` → `Update`

Shows a proposed match table and requires you to type `CONFIRM` before writing. Writes `13_DQ_Rule_Template_PATCHED.xlsx`. Rules with no ICDQ equivalent remain as `TechnicalScript`.

Expected output:
```
Matched: 11   Left as TechnicalScript: 4
✓ Saved: .../13_DQ_Rule_Template_PATCHED.xlsx
```

---

## Step 4 — Import patched template

```bash
python3 ~/Documents/CDGC/cdgc_import_single.py
→ ~/Downloads/CDGC_Import_<ClientName>/13_DQ_Rule_Template_PATCHED.xlsx
```

Wait for **COMPLETED** status. All rules in CDGC now have ICDQ references and correct Output Port Names.

**If PARTIAL_COMPLETED:** Some rows exist as `Create` but are already present. Force all rows to `Operation=Update` in the xlsx and re-import.

---

## Step 5 — Generate, import, and link occurrences

```bash
python3 ~/Documents/CDGC/cdgc_create_dq_occurrences.py --client <client>
```

This single script runs three phases automatically after a CONFIRM prompt:

**Phase 1 — Generate File 15 (DQ Rule Occurrences)**

File 13 defines *what* to measure. File 15 defines *where* — one row per rule/column combination. Each row tells MCC: "run this ICDQ rule against this exact Snowflake column." Without File 15, MCC has nothing to execute.

The `Primary Data Element` field requires post-scan catalog data — the exact Catalog Source Name registered in MCC plus the `DB/Schema/Table/Column` path as scanned. These values don't exist in any downloadable template. The script queries the live CDGC catalog, resolves the Catalog Source Name from the UUID in `core.location`, and constructs each PDE path dynamically.

**Phase 2 — Preview and confirm**

After matching rules to columns, the script shows a preview table and asks:
```
This script will now:
  1. Write   15_DQ_Rule_Occurrence.xlsx  (77 rows)
  2. Import  via CDGC bulk import API (POST → poll to COMPLETED)
  3. Link    77 template→occurrence relationships via PATCH API

Proceed? [yes/no]:
```

**Phase 3 — Import File 15 and link templates**

After confirmation, the script:
- Submits File 15 to the CDGC bulk import API and polls until COMPLETED
- PATCHes all template→occurrence relationships (`relatedRuleTemplateRuleInstance`)

**Why linking is required:** Bulk import does not create the Rule Template → Rule Occurrence relationship. The Bulk Import template has no "Rule Template" column on the DQ Rule Occurrence sheet, and the Relationships Annexure has no `RuleTemplate→RuleInstance` entry. CDGC creates this link automatically only when `Enable Automation = true` — manually imported occurrences bypass automation. Without this link, the **Rule Template** field on every occurrence is blank in the CDGC UI.

**Mapping:** Many-to-one. One template can cover multiple occurrences (the same rule may apply to matching columns across multiple tables). Matched by rule name — the part before ` — ` in the occurrence name.

Expected final output:
```
Import:   COMPLETED
Linked:   74 | Already linked: 3 | Failed: 0
```

**Verify:**
```bash
python3 ~/Documents/CDGC/audit_dq_links.py
```
Reports OK / MISSING / EXTRA per template. All should show OK.

**Warnings** = a rule's Input Port Name found no matching column in the scanned schema. Expected if some rules target columns not in the Snowflake environment. Those rows produce PARTIAL_COMPLETED on import — all other rows are created and linked. Not a blocker.

**If you need to re-run:** Delete existing occurrences first, then re-run with Create (default):
```bash
python3 ~/Documents/CDGC/cdgc_delete_dq_occurrences.py
python3 ~/Documents/CDGC/cdgc_create_dq_occurrences.py
```

**Standalone fallback:** `link_dq_templates_to_occurrences.py` is available as a standalone script if you need to re-link without re-generating File 15 (e.g., after a partial failure in Phase 3).

---

## Step 6 — Verify MCC catalog source settings

*Human action required — MCC configuration is GUI only.*

Before running the scan, verify the catalog source has the correct capabilities enabled.

MCC → Catalog Sources → your catalog source → **Edit**

### Capabilities — enable exactly these 5:

| Capability | Enable | Notes |
|---|---|---|
| Metadata Extraction | ✓ | Tables/columns — required |
| Data Profiling | ✓ | Row counts, null %, distinct values — **required for DQ scores to appear** |
| Data Quality | ✓ | Executes ICDQ rules — requires Profiling ON |
| Data Classification | ✓ | Auto-detects PII/PHI (SSN, DOB, email) |
| Glossary Association | ✓ | Auto-links columns to Business Terms |
| Relationship Discovery | — | Skip — requires an inference model to be configured first |
| Lineage Discovery | — | Skip — no views/stored procs in demo schema |
| Data Observability | — | Skip — needs multiple scan runs to build baseline |
| Writeback | — | Skip — can modify Snowflake; risky for demo |

### Runtime environment

Data Profiling requires a **Dedicated Secure Agent** — it does not work with:
- Hosted Agent (serverless) — profiling not supported
- Shared Secure Agent — results write to wrong org context

If only a hosted or shared agent is available, DQ score tabs will remain empty after the scan. Escalate to your org admin before proceeding.

### Schema filter

Confirm the filter covers all client schemas, e.g. for MHN:
```
TEST_DB.MHN_CLINICAL
TEST_DB.MHN_AI
TEST_DB.MHN_COMPLIANCE
```

**Critical:** Re-editing a catalog source resets all capability checkboxes to defaults. Re-verify all 5 are checked after any configuration change before running.

### Run the scan

Click **Run**. MCC reads each occurrence, calls ICDQ with the Technical Rule Reference ID, executes the rule against the Snowflake column, and writes the score back to CDGC.

Scan takes 5–15 minutes with Profiling + DQ enabled. Monitor progress in **MCC → Jobs**.

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
- Verify Rule Template field is populated (Step 5 linked correctly)
- Check MCC Jobs → DQ subtask completed (not just the Metadata Extraction task)

**If an occurrence shows "Can't run the rule template — input ports not mapped to Glossary":**
- That template is missing its `Primary Glossary` link (a Business Term)
- CDGC → open the DQ Rule Template → edit `Primary Glossary` → enter the matching Business Term name
- Re-run the MCC scan

---

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Output port rejected on occurrence import | Output Port Name not exactly `Output` | Verify ICDQ rule output port name in ICDQ, re-run Steps 2–4 |
| link script shows HTTP 404 | Template reference ID doesn't exist | Confirm the template was imported; check the prefix matches |
| link script shows HTTP 409 | Relationship already exists | Safe to ignore — script counts as skipped |
| Wrong occurrences showing on template | Numeric 1:1 mapping was run first | Run `unlink_wrong_dq_template_links.py` then re-run link script |
| Occurrence import FAILED | PDE path invalid | Verify catalog source name; re-generate File 15 after checking |
| No DQ scores after scan | Missing occurrence→template link | Run audit_dq_links.py; re-run link script for any MISSING |
| No DQ scores after scan | Data Profiling not enabled on catalog source | Edit catalog source → enable Data Profiling → re-run scan |
| Profiling tab empty after scan | Hosted or shared agent used | Data Profiling requires a dedicated Secure Agent — escalate to org admin |
| Capabilities reset unexpectedly | Catalog source re-edited | Re-editing resets checkboxes — re-verify all 5 capabilities before every scan |
| FRS API returns HTML redirect | Using JWT on FRS endpoint | fetch_icdq_rule_ids.py uses IDS-SESSION-ID by default — check script version |

---

## Scripts reference

| Script | Step | Purpose |
|--------|------|---------|
| `fetch_icdq_rule_ids.py` | Step 2 | Fetch ICDQ artifact IDs via FRS API → icdq_rules.csv |
| `patch_dq_template.py` | Step 3 | Patch File 13 with ICDQ refs, Output Port Name, Operation=Update |
| `cdgc_import.py` | Step 4 | Import a single xlsx file, poll to completion |
| `cdgc_create_dq_occurrences.py` | Step 5 | **Three-phase pipeline:** generate File 15 → import via API → PATCH all template→occurrence links. Replaces the former Steps 5–7. |
| `link_dq_templates_to_occurrences.py` | Fallback | Standalone link-only script — use if Phase 3 of Step 5 failed and File 15 is already imported |
| `audit_dq_links.py` | Verify | Audit all templates — expected vs actual occurrence links |
| `check_dq_links.py` | Verify | Spot-check a single template neighborhood |
| `count_dq_occurrences.py` | Verify | Count all occurrences by prefix — confirm expected total before scan |
| `cdgc_delete_dq_occurrences.py` | Re-import | Delete all occurrences via REST. Run before re-importing with Operation=Create |
| `unlink_wrong_dq_template_links.py` | Cleanup | Remove incorrect template→occurrence links (e.g., from a prior numeric-mapping run) |

---

## Full deployment guide

For detailed technical documentation including API endpoint specs, the two-deployment-scenario breakdown (Full Governance vs. Catalog Only), and all gotchas: `DQ_ICDQ_Deployment_Guide.md` in this directory.
