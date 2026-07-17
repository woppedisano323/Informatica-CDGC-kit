# Informatica CDGC Kit

An accelerator for Informatica Cloud Data Governance & Catalog (CDGC). Stand up a complete governed environment for any industry vertical — including real DQ scores executed by ICDQ against live Snowflake data — with no manual data entry. Use it for demo environments or to accelerate real client onboarding.

---

## What can I do with this?

| I want to… | Use this |
|------------|----------|
| Build a full CDGC environment for a vertical | `/cdgc-setup` skill |
| Connect DQ rules to ICDQ and get real scores | `/cdgc-dq-setup` skill |
| Accelerate onboarding from client's own documents | `/cdgc-client-setup` skill |
| Wipe an org and start fresh | `/cdgc-wipe` skill |
| Import 14 Excel files via API (no UI clicks) | `cdgc_import_single.py` |
| Diagnose a failed import job | `check_job.py` |

---

## Getting started

```bash
# 1. Clone the repo
git clone https://github.com/woppedisano323/Informatica-CDGC-kit.git
cd Informatica-CDGC-kit

# 2. Install Python dependencies (one time)
pip install openpyxl requests

# 3. Open in Claude Code
claude .

# 4. Start with a skill
/cdgc-setup
```

---

## Skills

Skills live in `.claude/commands/` and are auto-loaded when you open this repo in Claude Code.

| Skill | What it does |
|-------|-------------|
| `/cdgc-setup` | Generate a complete CDGC environment for any industry vertical. Produces 14 ready-to-import Excel files covering Domains, Business Terms, Policies, Regulations, Systems, AI Assets, Data Sets, and DQ Rule Templates. |
| `/cdgc-dq-setup` | Deploy the full DQ execution pipeline — connects DQ Rule Templates to ICDQ rules, generates and imports Rule Occurrences, links templates to occurrences, and configures MCC to execute and score them automatically. Produces real DQ scores in CDGC. |
| `/cdgc-client-setup` | Accelerate client onboarding from documents they already have — data dictionaries, policy PDFs, org charts, glossaries. Parses and scores confidence, generates a Review Workbook for human validation, then produces the 14 import files. |
| `/cdgc-wipe` | Wipe all governance assets from a CDGC org before reloading. Deletes in dependency order with explicit confirmation. |

---

## End-to-end flow

### Phase 1 — Governance layer

```
/cdgc-setup  →  14 Excel files generated  →  imported into CDGC via API
```

Covers all governance asset types: Domains, Subdomains, Regulations, Policies, Legal Entities,
Business Areas, Geographies, Systems, AI Systems, AI Models, Business Terms, Data Sets,
DQ Rule Templates, and Relationships.

### Phase 2 — Technical metadata

```
cdgc_snowflake_setup.py  →  Snowflake tables + sample data loaded
MCC Scan 1  →  columns cataloged in CDGC
```

### Phase 3 — DQ execution pipeline

```
/cdgc-dq-setup
  → Claire builds ICDQ rules
  → fetch_icdq_rule_ids.py --client <client>   (fetches artifact IDs)
  → patch_dq_template.py --client <client>     (patches File 13 with ICDQ refs)
  → cdgc_import_single.py                      (imports patched File 13)
  → cdgc_create_dq_occurrences.py --client <client>  (generates + imports File 15, links templates)
  → MCC Scan 2  →  ICDQ rules execute  →  real scores in CDGC
```

**Why two MCC scans?** Scan 1 discovers what columns exist. File 15 (occurrences) maps rules to those columns — it can only be generated after Scan 1. Scan 2 executes the rules. This is the correct pattern for any real customer deployment.

---

## Client config system

Each client environment is defined in `clients/<client>.json`. All scripts accept `--client <name>` — no manual prompts for hostnames, project names, directories, or prefixes.

```json
{
  "client_name": "Meridian Health Network",
  "prefix": "MHN",
  "frs_host": "usw1.dmp-us.informaticacloud.com",
  "icdq_project": "MHN_Healthcare_Demo",
  "icdq_folder": "Meridian Healthcare Network",
  "import_dir": "~/Downloads/CDGC_Import_MeridianHealthNetwork/",
  "occurrence_prefix": "MHNDQO",
  "catalog_source_name": "MHN_Healthcare_Snowflake",
  "snowflake_database": "TEST_DB",
  "snowflake_schemas": ["MHN_CLINICAL", "MHN_AI", "MHN_COMPLIANCE"]
}
```

To add a new client: copy an existing config from `clients/`, update the values, and save as `clients/<client>.json`.

---

## Industry verticals

| Vertical | Schemas | Story |
|----------|---------|-------|
| Financial Services | Core banking, training data, model registry | AML/KYC, credit risk, regulatory reporting (BCBS 239, CCAR, FATCA) |
| Healthcare | Clinical, AI, compliance | HEDIS quality measures + AI governance (sepsis risk, readmission prediction, medication adherence) aligned to ONC HTI-1 |

Pre-built demo templates for both verticals are in `demo_templates/`.

---

## Scripts reference

| Script | Purpose |
|--------|---------|
| `cdgc_snowflake_setup.py` | Load sample data into Snowflake — Financial Services or Healthcare vertical. Use `--drop` to reset. |
| `fetch_icdq_rule_ids.py` | Fetch ICDQ rule artifact IDs via FRS API → `icdq_rules.csv`. Use `--client` and `--csv`. |
| `patch_dq_template.py` | Patch File 13 with ICDQ artifact IDs, Output Port Name, and Operation=Update. Use `--client`. |
| `cdgc_create_dq_occurrences.py` | Three-phase pipeline: generate File 15 → import via API → link all template→occurrence relationships. Use `--client`. |
| `cdgc_import_single.py` | Import any single xlsx file into CDGC and poll for completion. |
| `audit_dq_links.py` | Audit all DQ Rule Templates — expected vs actual occurrence links. Use `--client`. |
| `count_dq_occurrences.py` | Count all occurrences by prefix in CDGC. Confirm expected total before MCC scan. |
| `link_dq_templates_to_occurrences.py` | Standalone link script — use if Phase 3 of `cdgc_create_dq_occurrences.py` failed. |
| `cdgc_delete_dq_occurrences.py` | Delete all occurrences by prefix via REST API. Run before re-importing with Operation=Create. |
| `unlink_wrong_dq_template_links.py` | Remove incorrect template→occurrence links before re-linking. |
| `cdgc_wipe.py` | Delete all governance assets from a CDGC org in dependency order. |
| `check_job.py` | Fetch full JSON for a CDGC import job by ID. Use to diagnose FAILED imports. |

---

## MCC catalog source settings

For any client, enable exactly these 5 capabilities:

| Capability | Enable |
|---|---|
| Metadata Extraction | ✓ |
| Data Profiling | ✓ |
| Data Quality | ✓ |
| Data Classification | ✓ |
| Glossary Association | ✓ |
| Relationship Discovery | — (requires inference model) |
| Lineage Discovery | — |
| Data Observability | — |
| Writeback | — |

**Critical:** Data Profiling requires a **Dedicated Secure Agent** — not a Hosted Agent (serverless) or shared agent. Without it, DQ score tabs remain empty after the scan.

---

## Prerequisites

- Python 3.8+ with `openpyxl` and `requests` installed
- Claude Code ([claude.ai/code](https://claude.ai/code))
- Informatica Cloud (IDMC) org with CDGC and ICDQ enabled
- MCC catalog source configured and pointed at your Snowflake environment
- Dedicated Secure Agent (required for Data Profiling + DQ execution)
- IDMC credentials — entered at runtime, never stored in files

---

## Guides

| Guide | Location |
|-------|----------|
| DQ + ICDQ + MCC Deployment Guide | `docs/DQ_ICDQ_Deployment_Guide.md` |
| Skills Reference | `.claude/commands/SKILLS_REFERENCE.md` |
