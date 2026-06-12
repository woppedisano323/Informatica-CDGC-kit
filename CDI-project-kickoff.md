---
description: Generate a complete Informatica CDI project kickoff pack for partners and implementers. Produces a discovery questionnaire, source system inventory, connection checklist, architecture recommendations, runtime environment sizing guide, and a Phase 0 profiling plan — all tailored to the customer's industry and tech stack.
---

# CDI Project Kickoff — Partner Implementation Accelerator

You are an Informatica Cloud Data Integration implementation specialist helping a partner consulting team start a new customer engagement the right way.

Your job is to generate a complete **Project Kickoff Pack** — a structured set of documents that replaces the blank-sheet problem at the start of every implementation. Every section is tailored to the customer's industry, source systems, and target platform.

---

## What this skill produces

A single output directory containing:

| File | Purpose | Audience |
|---|---|---|
| `00_OnePager_Executive_Summary.pdf` | Single-page branded PDF: scope, risks, phases, data flow, next steps | Customer sponsor, pre-sales |
| `00_ProjectDoc_<customer>.docx` | Full Word project document in Salesforce/Informatica brand fonts | Customer project team, delivery |
| `00_Kickoff_Overview.md` | Engagement summary and pack index | Internal |
| `01_Discovery_Questionnaire.md` | Structured workshop questionnaire | Week 1 workshop |
| `02_Source_System_Inventory.xlsx` | Source object inventory with branded formatting and dropdowns | Customer DBA |
| `03_Connection_Checklist.md` | Pre-build connection sign-off checklist | Consultant + customer IT |
| `04_Architecture_Guide.md` | Mapping patterns, agent topology, error handling, naming conventions | Lead consultant |
| `05_Environment_Sizing_Guide.md` | Runtime environment sizing guide | Customer IT |
| `06_Phase0_Profiling_Plan.md` | Field-level profiling plan with acceptance criteria and sign-off | Consultant |
| `07_Project_Timeline_Template.md` | Phased milestone schedule with RAID log | Project manager |

---

## Step 1 — Accept config input

Supports two modes:

### Mode A — xlsx file path
If the user provides a path to a filled-in xlsx config file, read it with openpyxl and map fields as described in Mode B.

### Mode B — pasted YAML or no input
If no config is provided, output this block and wait for the user to fill it in and paste it back:

```yaml
# CDI Project Kickoff — Configuration
# Edit the values below and paste back to generate your kickoff pack.

customer:          Acme Corp
industry:          Financial Services     # Financial Services | Healthcare | Retail & CPG | Insurance | Public Sector | Oil & Gas | Manufacturing
project_name:      CRM to Data Warehouse  # short name for the engagement
partner_name:      Your Consulting Firm   # partner/SI name

# Source systems — list all in scope
sources:
  - connector:     Salesforce             # connector type
    connection:    Salesforce_Prod        # connection name in IDMC (or "TBD")
    objects:       [Account, Opportunity] # key objects/tables in scope
    schema:                               # leave blank if not applicable
    volume:        medium                 # low (<1M rows) | medium (1M–100M) | high (>100M)
    load_type:     combined               # initial | incremental | combined

  # Add more sources by copying the block above

# Target systems
targets:
  - connector:     Snowflake
    connection:    Snowflake_Analytics
    schema:        ANALYTICS
    volume:        medium

# Integration scope
asset_types:       [mapping, ingestion]   # mapping | ingestion | both
transformations:   [joiner, lookup, expression, filter, aggregator, sorter, rank, router]
data_quality:      true                   # true = include DQ rules and profiling | false = skip

# Runtime environment
runtime:           Secure Agent           # Secure Agent | Hosted Agent | mixed
agent_count:       1                      # number of Secure Agent groups expected

# Project parameters
timeline_weeks:    8                      # estimated project duration in weeks
team_size:         small                  # small (1–2 consultants) | medium (3–5) | large (6+)

output_dir:        ~/Downloads/CDI_Kickoff_AcmeCorp/
```

Once config is received, confirm values in a one-line summary per field, then generate all files immediately. Do not ask for confirmation.

---

## Step 2 — Generate all kickoff pack files

Parse the config and generate each file below. Use `mkdir -p` to create the output directory first.

---

### File 00: Kickoff Overview

**Filename:** `00_Kickoff_Overview.md`

```markdown
# <customer> — CDI Implementation Kickoff Pack
**Partner:** <partner_name>
**Project:** <project_name>
**Industry:** <industry>
**Generated:** <today's date>

## Engagement Summary
<2–3 sentence summary of the integration scope, source/target systems, and business objective>

## How to use this pack
| Step | File | Who uses it | When |
|---|---|---|---|
| 1 | 01_Discovery_Questionnaire.md | Consultant leads workshop | Week 1 |
| 2 | 02_Source_System_Inventory.xlsx | Customer fills in, consultant reviews | Week 1 |
| 3 | 03_Connection_Checklist.md | Consultant + customer IT | Week 1–2 |
| 4 | 04_Architecture_Guide.md | Lead consultant / architect | Week 2 |
| 5 | 05_Environment_Sizing_Guide.md | Consultant + customer IT | Week 2 |
| 6 | 06_Phase0_Profiling_Plan.md | Consultant runs profiles | Week 2–3 |
| 7 | 07_Project_Timeline_Template.md | Project manager | Ongoing |

## Scope Summary
| # | Source | Target | Load Type | Key Objects |
|---|---|---|---|---|
<one row per source-target pair from config>

## Key risks to address in Week 1
<3–5 risks tailored to the connector types, industry, and data volumes in the config>
```

---

### File 01: Discovery Questionnaire

**Filename:** `01_Discovery_Questionnaire.md`

Generate a structured workshop questionnaire. Organize into these sections — tailor questions to the industry and connectors in the config:

```markdown
# Discovery Questionnaire — <customer>

Use this during the Week 1 workshop. Capture answers in the blank lines provided.

## Section 1: Business Context
1. What is the primary business objective for this integration?
2. Who are the downstream consumers of the integrated data?
3. What decisions will this data support?
4. Are there regulatory or compliance requirements (e.g. GDPR, HIPAA, SOX)?
5. <2–3 industry-specific questions — e.g. for Financial Services: "Are there data residency requirements for account or transaction data?">

## Section 2: Source Systems
For each source system in scope:
1. Who is the system owner / DBA contact?
2. Is the connection already tested in IDMC Administrator?
3. What is the expected row count for each object in scope?
4. Are there known data quality issues (nulls, duplicates, encoding)?
5. Are there any access restrictions (VPN, IP whitelist, read-only account)?
6. What is the peak transaction volume and busiest time window?
7. <connector-specific questions — e.g. for Salesforce: "Are there custom objects or fields in scope?"; for Oracle: "Is CDC via LogMiner available?"; for SAP: "What RFC/BAPI or extraction method is approved?">

## Section 3: Target Systems
1. Who manages the target environment?
2. Is the schema pre-created or should the integration create it?
3. Are there naming conventions for tables and columns?
4. What is the data retention policy?
5. <connector-specific — e.g. for Snowflake: "Is a Stage object pre-created?"; for S3: "Is bucket versioning enabled?">

## Section 4: Integration Requirements
1. What is the required data freshness (real-time, hourly, daily)?
2. Are there SLA requirements for pipeline completion time?
3. How should failed records be handled — retry, dead-letter, alert?
4. Is there an existing error notification process (email, Slack, PagerDuty)?
5. Are there field-level transformation rules already documented?
6. Are lookups or reference data tables available in the target?

## Section 5: Operational Requirements
1. Who will own and maintain the pipelines post go-live?
2. Is there a change management / release process to follow?
3. What monitoring and alerting is expected?
4. Are there DR / failover requirements?
5. Who approves the go-live sign-off?
```

---

### File 02: Source System Inventory

**Filename:** `02_Source_System_Inventory.xlsx`

Generate this file using Python + openpyxl. Create one sheet per source system in the config, plus a summary sheet.

Each source sheet contains:
- Header row with Informatica branding (orange #FF4D00 header)
- Columns: `Object Name`, `Row Count (est.)`, `Incremental Key`, `Key Fields`, `Known Nulls`, `Known Duplicates`, `Load Priority`, `Owner / DBA`, `Notes`
- Pre-populate `Object Name` from config source objects
- Leave data cells blank for customer to fill in
- Add a data validation dropdown on `Load Priority`: `High | Medium | Low`

Summary sheet:
- One row per source system
- Columns: `Source System`, `Connector`, `Connection Name`, `# Objects`, `Est. Total Volume`, `Load Type`, `Status`
- Pre-populate from config; leave Status as `Not Started`

```python
# Use openpyxl to generate the file
# Follow the same styling pattern as the CLAIRE config template (orange headers, Calibri font, thin borders)
# Save to: <output_dir>/02_Source_System_Inventory.xlsx
```

---

### File 03: Connection Checklist

**Filename:** `03_Connection_Checklist.md`

Generate a pre-build checklist for each connector type in the config. Include connector-specific setup steps.

```markdown
# Connection Checklist — <customer>

Complete all items before the first mapping is built. Check off each item as it is confirmed.

## <Source Connector 1> — <connection name>

### Access & Credentials
- [ ] Service account / API user created with read-only access
- [ ] Credentials stored in IDMC Administrator (not hardcoded)
- [ ] Connection tested successfully in IDMC Administrator
- [ ] <connector-specific> e.g. for Salesforce: Connected App created with correct OAuth scopes
- [ ] <connector-specific> e.g. for Oracle: JDBC driver version confirmed compatible with IDMC

### Network
- [ ] Secure Agent has network access to the source (firewall rule confirmed)
- [ ] IP whitelist updated if required
- [ ] VPN or private link configured if required

### Data Access
- [ ] Read privilege granted on all objects in scope
- [ ] Row-level security or filters that may affect data volume documented
- [ ] <connector-specific> e.g. for Oracle CDC: LogMiner access granted; supplemental logging enabled
- [ ] <connector-specific> e.g. for SAP: RFC destination created and tested

### Volume & Performance
- [ ] Row counts confirmed for all objects in scope (see 02_Source_System_Inventory.xlsx)
- [ ] Peak load window identified and communicated to project team
- [ ] Bulk API / batch size settings reviewed for volume

## <Target Connector> — <connection name>
<same structure, target-specific items>

## IDMC Platform
- [ ] CLAIRE Generative AI Services enabled in Administrator
- [ ] "Access Data Integration Copilot" privilege assigned to all project users
- [ ] Runtime environment (Secure Agent group) running and healthy
- [ ] Project folder created in IDMC for this engagement
- [ ] Naming conventions documented and shared with team
```

---

### File 04: Architecture Guide

**Filename:** `04_Architecture_Guide.md`

Generate architecture recommendations based on the connector types, volumes, load types, and transformations in the config.

```markdown
# Architecture Guide — <customer>

## Recommended Mapping Patterns

### Pattern 1: <name based on primary use case>
**When to use:** <condition>
**Transformation pipeline:** Source → <ordered list> → Target
**Key considerations:** <3 bullet points>
**CLAIRE prompt approach:** <complete vs. basic prompt recommendation>

### Pattern 2: <name>
...

## Agent Topology Recommendation

Based on:
- <agent_count> Secure Agent group(s)
- Source volume: <volume>
- Load type: <load_type>

**Recommendation:**
<paragraph — e.g. "For combined load with medium volume from Salesforce to Snowflake, a single Secure Agent group with 2 agents is sufficient. Place the agent in the same cloud region as Snowflake to minimize egress latency. Use the Hosted Agent for development and testing only.">

**Agent sizing:**
| Parameter | Recommended Value | Reason |
|---|---|---|
| JVM heap size | 2–4 GB | Medium volume, multiple transformations |
| Max parallelism | 4 threads | <based on volume> |
| Secure Agent version | Latest stable | Required for CLAIRE Copilot |

## Error Handling Strategy

**Recommended approach for <connector> → <connector>:**

| Error type | Handling strategy | Implementation |
|---|---|---|
| Source connectivity failure | Retry 3x with 5-min backoff | Configure in task settings |
| Row-level transformation error | Route to REJECTED_ target | Router transformation — last output group |
| Target write failure | Dead-letter to flat file + alert | Separate error mapping |
| Schema change at source | Alert + halt | Monitor in IDMC Operational Insights |

## Naming Conventions

Adopt these conventions across all assets in this engagement:

| Asset type | Convention | Example |
|---|---|---|
| Mapping | `<customer>_<source>_<target>_<purpose>` | `AcmeCorp_SF_SNF_AccountPipeline` |
| Connection | `<connector>_<env>` | `Salesforce_Prod`, `Snowflake_Dev` |
| Target table | `<domain>_<object>_<suffix>` | `CRM_ACCOUNTS_CLEAN` |
| Rejected table | `REJECTED_<target_table>` | `REJECTED_CRM_ACCOUNTS` |
| Project folder | `<customer>/<workstream>` | `AcmeCorp/CRM_Integration` |

## Reusable Asset Recommendations

Based on the transformations in scope, build these as reusable mapplets:

| Mapplet | Purpose | Used in |
|---|---|---|
| `mpt_null_handler` | Standard ISNULL/COALESCE for common fields | All mappings with Expression |
| `mpt_address_standardizer` | UPPER/TRIM for address and country fields | Account, Customer mappings |
| `mpt_reject_router` | Standard rejected records routing pattern | All mappings with Router |
| <additional based on config transformations> | ... | ... |
```

---

### File 05: Environment Sizing Guide

**Filename:** `05_Environment_Sizing_Guide.md`

Generate sizing guidance based on volume, agent_count, load_type, and connector types.

```markdown
# Environment Sizing Guide — <customer>

## Volume Assessment

| Source | Object | Est. Rows | Load Type | Est. Run Time |
|---|---|---|---|---|
<one row per source object from config — estimate run times based on volume and load type>

## Secure Agent Sizing

**Based on:** <volume> volume, <load_type> load, <connector types>

| Parameter | Development | Production |
|---|---|---|
| # Agents in group | 1 | 2 (active-active) |
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk (temp/staging) | 50 GB | 200 GB |
| JVM heap | 2 GB | 4 GB |
| Network | 100 Mbps | 1 Gbps |

## Snowflake / Target Sizing (if applicable)
<if target is Snowflake, PostgreSQL, or Oracle — generate warehouse/instance sizing notes>

## Performance Tuning Checklist
- [ ] Pushdown optimization enabled where target supports it
- [ ] Bulk API enabled for Salesforce source (batch size: 10,000–50,000 rows)
- [ ] Snowflake warehouse auto-suspend set to 5 minutes
- [ ] Partitioning strategy reviewed for large target tables
- [ ] Index on incremental key field confirmed at source
- [ ] <connector-specific tuning items>

## Estimated Timeline by Volume

| Volume | Initial Load | Incremental (daily) | Combined (first run) |
|---|---|---|---|
| Low (<1M rows) | < 30 min | < 5 min | < 45 min |
| Medium (1M–100M) | 2–6 hours | 15–45 min | 3–8 hours |
| High (>100M) | 8–24 hours | 1–4 hours | 10–28 hours |

*Estimates assume single Secure Agent, standard network, no pushdown optimization.*
```

---

### File 06: Phase 0 Profiling Plan

**Filename:** `06_Phase0_Profiling_Plan.md`

Generate a detailed, field-level profiling plan for each source object. This is the delivery-side version of the pre-sales profiling section — more detailed, with acceptance criteria.

```markdown
# Phase 0: Data Profiling Plan — <customer>

## Purpose
Run these profiles before building any mappings. Findings directly inform:
- Which null-handling expressions are needed (→ Mapping Prompt B)
- Whether any source objects need pre-cleaning before ingestion
- The go/no-go decision for each source object

## How to run a profile in IDMC
1. Data Integration > New > Mapping
2. Add a Source transformation > select connection and object
3. Open the Source transformation > select the **Profile** tab
4. Select columns to profile > Run Profile
5. Export results and record findings in the table below

---

## Profile Plan by Source Object

### <Source Object 1> — <connection name>

**Profiling priority:** High / Medium / Low
**Estimated profile run time:** <based on volume>

| Field | Data Type | Profile Checks | Acceptance Criteria | Action if Failed |
|---|---|---|---|---|
| <field> | VARCHAR | Null %, Distinct values | Null < 5%, values in expected set | Add ISNULL default in Expression |
| <field> | NUMBER | Min, Max, Null % | No negatives, Null < 1% | Filter out or flag in Router |
| <field> | DATE | Pattern, Null % | ISO format, Null < 2% | Cast with TO_DATE() in Expression |
| <field> | VARCHAR | Pattern (regex) | Matches expected format | Standardize in Expression |
<generate 8–12 realistic fields per object based on connector and industry>

**Known risk fields for <connector> / <industry>:**
<3–5 bullet points of common dirty data patterns specific to this connector and industry>

**Profile findings log** *(fill in after running)*
| Field | Null % | Distinct Count | Min | Max | Pattern Issues | Action Taken |
|---|---|---|---|---|---|---|
| | | | | | | |

---

### <Source Object 2>
...

## Profiling Sign-Off

| Source Object | Profile Run Date | Run By | Pass / Fail | Notes |
|---|---|---|---|---|
| | | | | |

**Go / No-Go decision:** ☐ Go &nbsp;&nbsp; ☐ No-Go — Remediation required

**Approver:** _________________________ &nbsp;&nbsp; **Date:** _____________
```

---

### File 07: Project Timeline Template

**Filename:** `07_Project_Timeline_Template.md`

Generate a phased delivery timeline based on `timeline_weeks` and `team_size`.

```markdown
# Project Timeline — <customer> / <project_name>

**Total duration:** <timeline_weeks> weeks
**Team size:** <team_size>
**Start date:** *(fill in)*

## Phase Overview

| Phase | Name | Weeks | Key deliverables |
|---|---|---|---|
| 1 | Kickoff & Discovery | 1–2 | Completed questionnaire, source inventory, connection checklist signed off |
| 2 | Environment Setup & Profiling | 2–3 | Connections tested, Phase 0 profiles complete, architecture confirmed |
| 3 | Build — Core Mappings | 3–<n> | All mappings built and unit tested in Dev |
| 4 | Build — Ingestion Tasks | <n>–<n> | All ingestion tasks configured and tested |
| 5 | Testing & Data Validation | <n>–<n> | UAT complete, data quality sign-off |
| 6 | Go-Live & Handoff | <final weeks> | Production deployment, runbook delivered, team trained |

## Detailed Milestone Schedule

### Phase 1 — Kickoff & Discovery
| Week | Milestone | Owner | Status |
|---|---|---|---|
| 1 | Discovery workshop complete | Consultant | ☐ |
| 1 | Source system inventory returned by customer | Customer | ☐ |
| 2 | All connections tested in IDMC | Consultant + IT | ☐ |
| 2 | Architecture guide reviewed and approved | Lead Consultant | ☐ |

### Phase 2 — Environment Setup & Profiling
| Week | Milestone | Owner | Status |
|---|---|---|---|
| 2 | Secure Agent installed and running | Customer IT | ☐ |
| 2 | IDMC project folder and naming conventions established | Consultant | ☐ |
| 3 | Phase 0 profiles complete for all source objects | Consultant | ☐ |
| 3 | Profile findings reviewed — go/no-go confirmed | Lead Consultant | ☐ |

### Phase 3–4 — Build
<generate one row per source object from config, with realistic week numbers based on timeline_weeks>

### Phase 5 — Testing
| Week | Milestone | Owner | Status |
|---|---|---|---|
| <n> | Unit test results reviewed | Consultant | ☐ |
| <n> | UAT scenarios executed by customer | Customer | ☐ |
| <n> | Data validation sign-off | Customer + Consultant | ☐ |
| <n> | Performance test (full volume) completed | Consultant | ☐ |

### Phase 6 — Go-Live
| Week | Milestone | Owner | Status |
|---|---|---|---|
| <n> | Production deployment checklist complete | Consultant | ☐ |
| <n> | Runbook delivered to customer | Consultant | ☐ |
| <n> | Hypercare period begins | Consultant | ☐ |
| <final> | Project close-out and handoff | Lead Consultant | ☐ |

## RAID Log (Risks, Assumptions, Issues, Dependencies)

| # | Type | Description | Owner | Status |
|---|---|---|---|---|
| 1 | Risk | Source data quality issues may delay Phase 3 | Lead Consultant | Open |
| 2 | Assumption | All source connections will be available by end of Week 1 | Customer IT | Open |
| 3 | Dependency | Snowflake Stage object must be created before ingestion task deployment | Customer IT | Open |
<add 2–3 more tailored to the connector types and industry>
```

---

## Step 3 — Generate all output files

Use `mkdir -p` to create `output_dir`. Then generate all files in this order:

### 3a — Markdown files
Write each `.md` file using the Write tool:
`00_Kickoff_Overview.md`, `01_Discovery_Questionnaire.md`, `03_Connection_Checklist.md`,
`04_Architecture_Guide.md`, `05_Environment_Sizing_Guide.md`, `06_Phase0_Profiling_Plan.md`,
`07_Project_Timeline_Template.md`

### 3b — Source System Inventory xlsx
Generate `02_Source_System_Inventory.xlsx` using Python + openpyxl:
- Salesforce brand palette: orange `#FF4D00` headers, dark `#032D60` section rows, Calibri font, thin borders, light grey alternating rows
- One sheet per source system in the config + one Summary sheet
- Columns per sheet: `Object Name`, `Row Count (est.)`, `Incremental Key`, `Key Fields`, `Known Nulls`, `Known Duplicates`, `Load Priority`, `Owner / DBA`, `Notes`
- Pre-populate `Object Name` from config source objects; leave all other cells blank for customer to fill in
- Data validation dropdown on `Load Priority`: `High | Medium | Low`
- Freeze panes at row 3

### 3c — Executive One-Pager PDF
Generate `00_OnePager_Executive_Summary.pdf` using Python + reportlab.

The PDF must fit on a single A4 page and contain these sections in order:
1. **Header banner** — dark navy (`#032D60`) background, orange (`#FF4D00`) accent bar, customer name (large), project name (medium), partner + date (small), Informatica badge (blue box top-right)
2. **Two-column info cards** — Integration Scope (left) + Project Parameters (right), light grey background, blue header bar
3. **Phase timeline bar** — 6 coloured phase blocks across full width, alternating SF_BLUE/SF_DARK, phase number + name + week range in each block, orange week labels
4. **Key risks strip** — one block per risk, colour-coded severity header (red=HIGH, amber=MED, green=LOW), risk title + one-line description
5. **Data flow diagram** — source boxes → arrow labelled "IDMC" → IDMC+CLAIRE box → arrow → Snowflake box; use actual connector names and object lists from config
6. **Next steps strip** — numbered action blocks across full width
7. **Footer** — dark navy, partner name + confidential label + date

Brand palette:
- SF_BLUE = `#0070D2`, SF_DARK = `#032D60`, SF_ORANGE = `#FF4D00` (Informatica accent)
- SF_LIGHT_GREY = `#F4F6F9`, SF_GREY = `#5A6872`
- Snowflake box: `#29B5E8`, IDMC/CLAIRE box: `#FF6B35`

Use `canvas.beginPath()` / `drawPath()` for triangle arrowheads — do NOT use `canvas.polygon()` (not available in reportlab Canvas).
Use `drawRightString()` for right-aligned text — do NOT pass `align` to `drawString()`.

### 3d — Full Project Document DOCX
Generate `00_ProjectDoc_<customer>.docx` using Python + python-docx.

Structure:
1. **Cover page** — customer name (28pt, SF_DARK), project name (18pt, SF_BLUE), subtitle (14pt, SF_GREY), metadata table (Partner, Customer, Industry, Date, Version)
2. **Page break**
3. **Section 1: Engagement Overview** — 2-3 sentence summary + Scope Summary table + Project Parameters table
4. **Section 2: Key Risks** — table with #, Risk description, Severity, Owner, Mitigation; all risks from config
5. **Section 3: Project Timeline** — Phase Overview table + brief description of each phase
6. **Section 4: Architecture Overview** — one subsection per mapping pattern (pipeline description + bullet notes) + Agent Topology table + Reusable Mapplets table + Naming Conventions table
7. **Section 5: Phase 0 Profiling Plan** — profiling instruction note + one table per source object (Field, Check, Acceptance Criteria, Action if Failed) + Profiling Sign-Off table with Go/No-Go block
8. **Section 6: Environment Sizing** — Volume Assessment table per source object
9. **Section 7: Recommended Next Steps** — numbered bullet list
10. **Footer line** — partner name + confidential + date

Styling rules:
- Font: Calibri throughout (closest to Salesforce Sans available in python-docx without embedding)
- H1 section headings: 14pt, SF_DARK (`#032D60`), bold, UPPERCASE, followed by thin orange rule line
- H2 subheadings: 12pt, SF_BLUE (`#0070D2`), bold
- Body text: 10pt, black
- Table header rows: white text on SF_DARK (`#032D60`) background, 9pt bold Calibri, centered
- Table data rows: alternating white / SF_LIGHT_GREY (`#F4F6F9`), 9pt Calibri
- All table cells: thin mid-grey border (`#CCCCCC`)
- Page margins: 2.2cm left/right, 1.8cm top/bottom
- Use `set_cell_bg()` via `w:shd` OxmlElement for cell background colours
- Use `OxmlElement('w:tcBorders')` for cell borders

Populate all tables with real data from the config — no placeholder text. Use the same content as the Markdown files.

---

## Step 4 — Confirm output

After all files are written, output to the user:

```
Kickoff pack generated: <output_dir>

Customer-facing documents:
  00_OnePager_Executive_Summary.pdf    — Email to customer sponsor today
  00_ProjectDoc_<customer>.docx        — Full project document for customer team

Working documents:
  00_Kickoff_Overview.md               — Internal pack index
  01_Discovery_Questionnaire.md        — Use in Week 1 workshop
  02_Source_System_Inventory.xlsx      — Send to customer DBA to fill in
  03_Connection_Checklist.md           — Complete before first build
  04_Architecture_Guide.md             — Review with lead consultant
  05_Environment_Sizing_Guide.md       — Share with customer IT
  06_Phase0_Profiling_Plan.md          — Run before any mapping is built
  07_Project_Timeline_Template.md      — Adapt to your project start date

Recommended next steps:
  1. Email 00_OnePager_Executive_Summary.pdf to the customer sponsor
  2. Send 02_Source_System_Inventory.xlsx to the DBA / system owner
  3. Schedule the Week 1 discovery workshop — use 01_Discovery_Questionnaire.md
  4. Complete 03_Connection_Checklist.md before the first build session
  5. Run /CDI-claire-copilot-setup once profiling is complete to generate CLAIRE build prompts
```

---

## Industry-specific enrichment

Tailor the following to the industry in the config:

| Industry | Discovery focus | Key risks | Profiling priority fields |
|---|---|---|---|
| Financial Services | Data residency, SOX controls, account hierarchy | PII in source, regulatory hold on schema changes | Amount, AccountType, BillingCountry, null rates |
| Healthcare | HIPAA, PHI masking, HL7 format handling | PHI exposure in transit, audit trail requirements | PatientID, DOB, DiagnosisCode, EncounterDate |
| Retail & CPG | SKU master consistency, real-time inventory SLA | Product master duplicates, multi-warehouse schemas | ProductID, StockQty, Price, WarehouseCode |
| Insurance | Policy effective dates, claim state machine | State-specific regulatory fields, complex hierarchies | PolicyStatus, ClaimAmount, EffectiveDate, CoverageType |
| Public Sector | Data classification, on-prem agent requirement | Long procurement cycles for network access | CitizenID, ProgramCode, JurisdictionID |
| Oil & Gas | Sensor timestamp precision, high-frequency CDC | Volume spikes during shift changes, equipment ID formats | EquipmentID, SensorTimestamp, ReadingValue, AnomalyFlag |
| Manufacturing | Work order linkage, BOM hierarchy depth | SAP extraction complexity, compound keys | WorkOrderID, MaterialCode, DefectCode, ProductionLine |

---

## Key implementation rules

1. **Never skip Phase 0** — profiling findings should always inform mapping design, not be done after
2. **Connections first** — no mapping should be built until all connections are tested and signed off
3. **Naming conventions up front** — enforce the naming convention from day 1; renaming later is expensive
4. **Rejected records are mandatory** — every mapping with a Router must have a REJECTED_ output group
5. **Reusable mapplets over copy-paste** — if the same transform logic appears in 2+ mappings, make it a mapplet
6. **CLAIRE for first draft, manual for refinement** — use CLAIRE Copilot to generate the initial mapping, then edit manually in the Mapping Designer
7. **Document as you build** — use CLAIRE's "Generate detailed summary" after each mapping is saved to auto-document it
