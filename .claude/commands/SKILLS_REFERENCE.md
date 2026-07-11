# Informatica CDGC Kit — Skills & Scripts Reference

Full reference for all Claude Code skills and Python scripts in this repo. Skills are auto-loaded when you open this repo in Claude Code — no install required.

For a quick orientation, start with the root [README.md](../../README.md).
For users new to Terminal, see [QUICK_START.md](../../QUICK_START.md).

---

## Skill taxonomy

Skills fall into three categories:

| Category | Skills | Purpose |
|----------|--------|---------|
| **Setup** | `/cdgc-setup`, `/cdgc-client-setup`, `/cdgc-technical-setup`, `/cdgc-dq-setup` | Build and configure a full CDGC environment end-to-end |
| **Maintenance** | `/cdgc-wipe` | Manage an existing org |
| **Live (demo-only)** | `/cdgc-demo-live` | Demonstration scripts for use in front of a prospect — not for building environments |

**Live skills are for demonstration only.** They exist to showcase capabilities in a live setting and should not be used to build a real environment or prepare a client org. Use the Setup skills for all actual work.

---

## Setup skills — full environment deployment

### `/cdgc-setup`

Generate a complete, importable CDGC demo environment for any industry vertical. Produces 14 Excel files covering every major asset type, ready to bulk-import in order.

**Invoke:** `/cdgc-setup`

Claude asks for: customer name, industry vertical, regulatory concerns, primary domains, and output directory. Customer name + vertical is enough — all other values default.

**Supported verticals:** Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector & Government, Oil & Gas, Manufacturing

**What it produces:**

| # | File | Asset Type |
|---|------|-----------|
| 01 | `01_Domain.xlsx` | Domain |
| 02 | `02_Subdomain.xlsx` | Subdomain |
| 03 | `03_Regulation.xlsx` | Regulation |
| 04 | `04_Policy.xlsx` | Policy |
| 05 | `05_Legal_Entity.xlsx` | Legal Entity |
| 06 | `06_Business_Area.xlsx` | Business Area |
| 07 | `07_Geography.xlsx` | Geography |
| 08 | `08_System.xlsx` | System |
| 09 | `09_AI_System.xlsx` | AI System |
| 10 | `10_AI_Model.xlsx` | AI Model |
| 11 | `11_Business_Term.xlsx` | Business Term |
| 12 | `12_Data_Set.xlsx` | Data Set |
| 13 | `13_DQ_Rule_Template.xlsx` | DQ Rule Template |
| 14 | `14_Relationships.xlsx` | Cross-asset relationships |

Output: `~/Downloads/CDGC_Import_<ClientName>/`

**Import order:** Always `01 → 14` in sequence. Wait for **COMPLETED** before uploading the next file.

**Next step after import:** Run `/cdgc-dq-setup` to activate DQ execution.

**Full guide:** `CDGC_Demo_Setup_Guide.md`

---

### `/cdgc-client-setup`

Build a complete CDGC import package from documents the client already has — data dictionaries, policy PDFs, org charts, glossaries, Excel schemas. Parses the documents, scores confidence, generates a color-coded Review Workbook for approval, then produces all 14 import files.

**Two entry points:**
- `/cdgc-client-setup` — full flow: parse documents → Review Workbook → generate import files
- `/cdgc-client-setup resume <path>` — pick up from an edited Review Workbook

**Accepts:** CSV, Excel (multi-tab), PDF, Word, plain text

**Fallback options when a field can't be inferred:**
- **A** — TODO markers for manual review
- **B** — auto-fill from vertical defaults
- **C** — interactive gap interview

**Review Workbook color guide:**

| Color | Meaning |
|-------|---------|
| White | HIGH confidence — ready to import |
| Yellow | MEDIUM — spot-check recommended |
| Orange | LOW — review carefully |
| Red | TODO or conflict — action required |

**When to use vs `/cdgc-setup`:**

| Situation | Use |
|-----------|-----|
| Client has data dictionaries, policy PDFs, glossaries, or org charts | `/cdgc-client-setup` |
| No client documents, running a quick vertical demo | `/cdgc-setup` |
| Mid-engagement: client provided docs after initial demo | `/cdgc-client-setup` |
| Demonstrating the AI-assisted onboarding story | `/cdgc-client-setup` |

**Next step after import:** Run `/cdgc-dq-setup` to activate DQ execution.

**Full guide:** `CDGC_Client_Setup_Guide.md`

---

### `/cdgc-technical-setup`

Add real technical metadata to a governance environment already built with `/cdgc-setup` or `/cdgc-client-setup`. Connects Snowflake tables and columns to Business Terms, auto-classifies PII, fills governance gaps, and shows Technical Coverage in the live dashboard.

**Invoke:** `/cdgc-technical-setup`

**Sequence:**
```
Step 1  Load Snowflake sample data
Step 2  Create IDMC Snowflake connection
Step 3  Create MCC catalog source and run scan
Step 4  Add Business Names via Claire
Step 5  Link columns to Business Terms (initial pass)
Step 6  Governance pipeline — gap analysis and Business Names
Step 6b DQ Rule Occurrences — see /cdgc-dq-setup
Step 7  Launch dashboard and verify Technical Coverage
```

**Prerequisites:** `/cdgc-setup` or `/cdgc-client-setup` completed and imported.

**Financial Services validated:** end-to-end May 2026.

**Full guide:** `CDGC_Demo_Setup_Guide.md` (Technical section)

---

### `/cdgc-dq-setup`

Configure the full DQ execution pipeline — connects DQ Rule Templates to ICDQ rules, generates and imports DQ Rule Occurrences, links templates to occurrences, and verifies MCC executes and scores them.

**Invoke:** `/cdgc-dq-setup`

**Why this matters:** File 13 (DQ Rule Templates) defines *what* to measure. Without this skill, MCC has no occurrences to execute and no DQ scores ever appear in the catalog. This step is what makes DQ real.

**Sequence:**
```
Step 1  Build ICDQ rules with Claire         ← human action required
Step 2  Fetch ICDQ artifact IDs
Step 3  Patch DQ Rule Template (File 13)
Step 4  Import patched template
Step 5  Generate DQ Rule Occurrences (File 15) — post-scan, environment-specific
Step 6  Import occurrences
Step 7  Link templates to occurrences
Step 8  Run MCC scan                          ← human action required
        Verify: real DQ scores appear in CDGC
```

All DQ scores produced by this skill are real — executed by ICDQ against live Snowflake data.

**Prerequisites:** Files 01–14 imported, ICDQ enabled, MCC catalog source configured, Snowflake scan completed.

**Full guide:** `DQ_ICDQ_Deployment_Guide.md`

---

## Maintenance skills

### `/cdgc-wipe`

Wipe all governance assets from a CDGC org. Authenticates via IDMC, scans all 13 asset types, shows total count, then deletes in dependency order (children before parents). Requires typing `CONFIRM` before anything is deleted.

**Invoke:** `/cdgc-wipe`

**Deletes in order:** DQ Rule Templates → Business Terms → Data Sets → AI Models → AI Systems → Systems → Business Areas → Legal Entities → Geographies → Policies → Regulations → Subdomains → Domains

**Warning:** Irreversible. For sandbox and demo orgs only.

---

## Live skills — demonstration only

**These skills are for use in front of a prospect during a live demo. They are not for building environments or preparing client orgs.**

### `/cdgc-demo-live`

Walks through a live demonstration of a pre-built CDGC environment — navigating the UI, showing governance chains, and telling the CDGC story. References the FCB Financial Services demo org.

**Use when:** You are in a live customer meeting demonstrating CDGC.

**Do not use when:** You are actually building an environment for a customer. Use the Setup skills instead.

---

## Recommended skill sequence

For a complete CDGC environment with real DQ execution:

```
/cdgc-setup           ← governance foundation (14 files)
/cdgc-technical-setup ← Snowflake scan, column linking, Technical Coverage
/cdgc-dq-setup        ← ICDQ rules, occurrences, real DQ scores
```

For a client-specific environment:
```
/cdgc-client-setup    ← parse client docs, generate 14 files
/cdgc-technical-setup ← technical metadata layer
/cdgc-dq-setup        ← DQ execution pipeline
```

---

## Python scripts

### `cdgc_dashboard.py`
**Live 7-tab governance dashboard.** Opens automatically in your browser. Connects to your CDGC org via REST API and displays live data.

**Tabs:**
- Overview — asset counts and governance health score
- Business Glossary — all terms with lifecycle, domain, CDE flag
- Policies & Regs — policies and regulations with type and lifecycle
- DQ Rules — rule templates with criticality, dimension, and automation flag
- AI Assets — AI Systems and AI Models
- Workflows — 4 pre-built multi-step API orchestration workflows
- API Explorer — live endpoint browser with Try-It capability

**Run:** `python3 cdgc_dashboard.py`
**Requires:** `pip install flask requests`
**Full guide:** `CDGC_Dashboard_Guide.md`

---

### `cdgc_api_import.py`
**Automated API import.** Authenticates to IDMC and imports all 14 Excel files in dependency order via REST API. Polls for COMPLETED status after each file and prints a verification scan at the end.

**Run:** `python3 cdgc_api_import.py`
**Requires:** Excel files already generated by `/cdgc-setup` or `/cdgc-client-setup`

---

### `cdgc_create_dq_occurrences.py`
**Generate File 15 (DQ Rule Occurrences).** Reads patched File 13, queries live CDGC for all scanned columns matching each rule's Input Port Name, and builds `15_DQ_Rule_Occurrence.xlsx` with the correct Primary Data Element path for each column. Run after MCC scan — PDE paths require post-scan catalog data.

**Run:** `python3 cdgc_create_dq_occurrences.py`

---

### `link_dq_templates_to_occurrences.py`
**Link DQ Rule Templates to occurrences.** Sets the `relatedRuleTemplateRuleInstance` relationship for all 40 templates across 77 occurrences via PATCH API. Name-based matching (many-to-one). Idempotent — safe to re-run.

**Run:** `python3 link_dq_templates_to_occurrences.py`

---

### `audit_dq_links.py`
**Audit all template→occurrence links.** Queries the CDGC neighborhood for every template, compares actual linked occurrences against File 15, and reports OK / MISSING / EXTRA per template. Run after `link_dq_templates_to_occurrences.py` to confirm clean state.

**Run:** `python3 audit_dq_links.py`

---

### `fetch_icdq_rule_ids.py`
**Fetch ICDQ artifact IDs.** Navigates the FRS API to the ICDQ project folder and writes `icdq_rules.csv` with each rule name and artifact ID. Uses IDS-SESSION-ID auth (not JWT).

**Run:** `python3 fetch_icdq_rule_ids.py`

---

### `patch_dq_template.py`
**Patch File 13 with ICDQ references.** Reads `icdq_rules.csv` and updates the DQ Rule Template xlsx with Measuring Method = `InformaticaCloudDataQuality`, Technical Rule Reference, Output Port Name = `Output`, and Operation = `Update`. Writes `13_DQ_Rule_Template_PATCHED.xlsx`.

**Run:** `python3 patch_dq_template.py`

---

### `cdgc_wipe.py`
**Standalone API wipe.** Same logic as `/cdgc-wipe` but runs without Claude Code.

**Run:** `python3 cdgc_wipe.py`

---

### `cdgc_discover_classtypes.py`
**Org state diagnostic.** Prints a count of all asset types currently in the org. Use before import to confirm starting state, and after to verify counts.

**Run:** `python3 cdgc_discover_classtypes.py`

---

### `cdgc_check_bt.py`
**Business Term inspector.** Fetches the full API response for a single Business Term by externalId. Useful for debugging why a term looks wrong in the dashboard or UI.

**Run:** `python3 cdgc_check_bt.py`

---

### `cdgc_job_detail.py`
**Import job debugger.** Fetches full detail on a failed import job, including per-row error messages.

**Run:** `python3 cdgc_job_detail.py`

---

### `count_dq_occurrences.py`
**Count DQ occurrences.** Counts all DQ Rule Occurrences in the org. Use to confirm expected total before running MCC scan.

**Run:** `python3 count_dq_occurrences.py`

---

### `check_dq_links.py`
**Spot-check a single template.** Shows the CDGC neighborhood for one DQ Rule Template — confirms occurrence links and DQ tab state.

**Run:** `python3 check_dq_links.py`

---

### `cdgc_delete_dq_occurrences.py`
**Delete all DQ occurrences.** Deletes all DQ Rule Occurrences via REST API. Run before re-importing occurrences with Operation=Create to avoid duplicate errors.

**Run:** `python3 cdgc_delete_dq_occurrences.py`

---

### `unlink_wrong_dq_template_links.py`
**Remove incorrect template→occurrence links.** Removes links created by a previous numeric 1:1 mapping run. Hardcoded to the FCB environment — adapt if needed for other clients.

**Run:** `python3 unlink_wrong_dq_template_links.py`

---

### `install_cdgc_deps.sh`
**One-step dependency installer.** Installs all required Python packages.

**Run:** `bash install_cdgc_deps.sh`

---

## Import method (all skills)

**Option A — Manual UI:**
CDGC UI → Gear icon → Import → Upload file → Auto-map → Import → wait for COMPLETED → next file

**Option B — API automated:**
Use `cdgc_api_import.py` or choose API at approval time in `/cdgc-client-setup` or `/cdgc-setup`

Always import one file at a time, in order 01 → 14. Never skip files or import out of order.
