---
description: Build and import a full CDGC (Cloud Data Governance & Catalog) demo environment for any industry vertical. Supports Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector, Oil & Gas, and Manufacturing. Generates all 14 import files covering every major asset type. Choose manual UI upload or fully automated API import with job polling. API method validated end-to-end May 2026.
---

# CDGC Demo Environment Setup

You are an Informatica CDGC specialist. Your job is to generate a complete, importable demo environment using the official Informatica bulk import format.

When invoked, greet the user with this introduction and ask ONLY the first question — wait for their answer before continuing:

```
Welcome to the CDGC Demo Environment Builder!

I'll generate a complete set of 14 ready-to-import Excel files for your CDGC org — covering Domains, Business Terms, Policies, Regulations, Systems, AI assets, Data Sets, DQ Rules, and Relationships — all tailored to the industry vertical of your choice.

To get started: what's the name and industry for this demo?
This can be a real customer (e.g., "First Capital Bank — Financial Services") or a fictional demo company (e.g., "Acme Financial — Financial Services"). Either works perfectly.
```

Once the user answers, ask for the context details in Step 1a. After they respond, ask for the email separately in Step 1b. Do NOT ask about import method until after the files have been generated.

## What this skill produces

14 Excel files, imported in order, covering every major asset type in CDGC:

| # | File | Asset Type | Notes |
|---|------|-----------|-------|
| 01 | `01_Domain.xlsx` | Domain | Top-level data governance domains |
| 02 | `02_Subdomain.xlsx` | Subdomain | Must reference parent Domain by `Name \| Reference ID` |
| 03 | `03_Regulation.xlsx` | Regulation | Regulatory frameworks (BCBS 239, CCAR, etc.) |
| 04 | `04_Policy.xlsx` | Policy | Data governance policies |
| 05 | `05_Legal_Entity.xlsx` | Legal Entity | Corporate legal entities |
| 06 | `06_Business_Area.xlsx` | Business Area | Organizational units |
| 07 | `07_Geography.xlsx` | Geography | Geographic regions and jurisdictions |
| 08 | `08_System.xlsx` | System | Source/target systems |
| 09 | `09_AI_System.xlsx` | AI System | AI applications and agents |
| 10 | `10_AI_Model.xlsx` | AI Model | Machine learning models |
| 11 | `11_Business_Term.xlsx` | Business Term | Glossary terms |
| 12 | `12_Data_Set.xlsx` | Data Set | Logical data sets |
| 13 | `13_DQ_Rule_Template.xlsx` | Data Quality Rule Template | DQ rule definitions |
| 14 | `14_Relationships.xlsx` | Relationships | Cross-asset linkages |

---

## Step 1a — Gather context details

The intro already collected the company name and vertical. Now ask for these three items together:

1. **Key regulatory concerns** — e.g., BCBS 239, GDPR, SOX (or "use defaults")
2. **Primary data domains** — e.g., Customer, Transactions, Risk (or "use defaults")
3. **Output directory** — default: `~/Downloads/CDGC_Import_<CompanyName>/`

If the user says "use defaults", apply the vertical defaults below.

---

## Step 1b — Ask for the IDMC email (separate message, after Step 1a)

After the user responds to Step 1a, ask for the email on its own — do not bundle it with anything else:

```
One critical detail before I generate the files:

What is your IDMC login email?

Every asset in all 14 files requires a real, valid user email in the Governance Owner and Governance Administrator fields. If this email doesn't match an actual user in your CDGC org, the import will fail silently with no clear error message — this is one of the most common demo blockers.

Your own login email is the safest choice — you're guaranteed to already exist in the org.
```

Use the provided email for every `Stakeholder: Governance Owner` and `Stakeholder: Governance Administrator` column across all 14 files. Do not leave these blank or use a placeholder.

---

## Step 2 — Generate the import files

Use Python + openpyxl to generate all 11 files. Follow every rule below exactly — CDGC is strict about format.

### Universal rules (apply to every sheet)

- Sheet name must match exactly (see column specs below)
- Column order must match the template exactly — CDGC reads positionally
- `Operation` column must be `Create` for all new records
- `Lifecycle` must be one of: `Draft`, `In Review`, `Published`, `Obsolete`
- Boolean fields (`Critical Data Element`, `Enable Automation`) must be lowercase: `true` / `false`
- Remove all empty sheets before saving — CDGC rejects files with header-only sheets
- Do NOT include an Instructions or Annexure sheet
- Reference IDs are required for relationships — always derive a **customer-specific prefix** from the customer name initials (2–4 uppercase letters). Examples: "Maple Hills Network" → `MHN`, "First Capital Bank" → `FCB`, "Pacific Northwest Health" → `PNH`. Confirm the prefix with the user before generating files. Apply it consistently to ALL reference IDs across all 14 files using these stems: `{P}DOM-N`, `{P}SD-N`, `{P}REG-N`, `{P}POL-N`, `{P}LE-N`, `{P}BA-N`, `{P}GEO-N`, `{P}SYS-N`, `{P}AISYS-N`, `{P}AIM-N`, `{P}BT-N`, `{P}DS-N`, `{P}DQR-N`. Do NOT use CDGC's auto-generated prefixes (`DOM-`, `BT-`, `POL-`): they collide with system-generated IDs and are rejected on create.
- Parent references use format `Display Name | Reference ID` (e.g., `Customer & KYC | RKFDOM-5`)
- **Single parent rule:** CDGC enforces exactly one parent per asset. Populate only one parent column per row — leave all other parent columns blank. Violating this fails every row in the file with "There are multiple parents with this asset."
- **Stakeholder columns** (`Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`) must contain a real email address of a user in the org. Blank or placeholder values block UI import entirely with no clear error message.

---

### Sheet specs and column order

#### Domain
Sheet name: `Domain`
Columns (in order): `Reference ID`, `Name`, `Description`, `Alias Names`, `Lifecycle`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- No `Critical Data Element` column on Domain

#### Subdomain
Sheet name: `Subdomain`
Columns: `Reference ID`, `Name`, `Description`, `Alias Names`, `Business Logic`, `Examples`, `Lifecycle`, `Security Level`, `Operation`, `Parent: Subdomain`, `Parent: Domain`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- `Parent: Domain` format: `Domain Name | <PREFIX>DOM-X` (e.g., `Customer & KYC | RKFDOM-1`)
- `Parent: Subdomain`: populate only for nested subdomains — leave blank for top-level
- Single parent rule applies: populate either `Parent: Domain` or `Parent: Subdomain`, never both

#### Regulation
Sheet name: `Regulation`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Issuing Body`, `Regulation Type`, `Regulation URL`, `Operation`
- `Regulation Type` valid values: `Industry Standard`, `Government Regulation`, `Internal Policy`

#### Policy
Sheet name: `Policy`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Policy Type`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- `Policy Type` valid values: `Data Standards`, `Business Rule`, `Technical Standards`, `Conduct Standards`

#### Legal Entity
Sheet name: `Legal Entity`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Operation`

#### Business Area
Sheet name: `Business Area`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`

#### Geography
Sheet name: `Geography`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Operation`

#### System
Sheet name: `System`
Columns: `Reference ID`, `Name`, `Description`, `Asset ID`, `Lifecycle`, `Long Name`, `System Purpose`, `System Type`, `Operation`, `Parent: System`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- `System Type` valid value: `Software Application`
- `Asset ID`: use same value as Reference ID
- `Long Name`: full descriptive system name
- `System Purpose` valid values (confirmed on suborg): `Core Client & Transaction Processing`, `Master Data Management`, `Data Quality`, `Warehouse & DataMart`, `Reporting Layer`, `Finance Function`, `Management Reporting`, `Risk Function`, `Regulatory Reporting`, `Sales Reporting`
- Do NOT use `Operational`, `Analytical`, or `Reporting` — these are rejected on suborg accounts

#### AI System
Sheet name: `AI System`
Columns: `Reference ID`, `Name`, `Description`, `AI System Type`, `Development Stage`, `Lifecycle`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- `AI System Type` valid values: `AI Application`, `AI Agent`, `Retrieval System`, `Conversational`
- `Development Stage` valid values: `In Development`, `Validation`, `Production`
- `Lifecycle` must be `Published` — `In Review`, `Active`, and `Draft` are rejected on import

#### AI Model
Sheet name: `AI Model`
Columns: `Reference ID`, `Name`, `Description`, `AI Model Purpose`, `Architecture Type`, `Bias`, `Drift`, `Environment`, `Input`, `Libraries`, `Lifecycle`, `Model Format`, `Model Rules`, `Output`, `Source Model Repository`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- `Architecture Type` valid values: `Decision Trees`, `Logistic Regression`, `Linear Regression`, `Others`
- `Bias` / `Drift`: numeric values only (0–100) — text strings are rejected
- `Model Format` valid values: `Docker`, `ONNX`, `Other`
- `Lifecycle` must be `Published` — `In Review`, `Active`, and `Draft` are rejected on import

#### Business Term
Sheet name: `Business Term`
Columns: `Reference ID`, `Name`, `Description`, `Alias Names`, `Business Logic`, `Critical Data Element`, `Examples`, `Format Type`, `Format Description`, `Lifecycle`, `Security Level`, `Classifications`, `Reference Data`, `Operation`, `Parent: Subdomain`, `Parent: Business Term`, `Parent: Metric`, `Parent: Domain`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- **Single parent rule:** populate `Parent: Subdomain` only — leave `Parent: Domain` blank. Domain association is inherited through the Subdomain.
- `Parent: Subdomain` format: `Subdomain Name | <PREFIX>SD-X` (e.g., `Customer Identity | RKFSD-1`)
- `Critical Data Element`: `true` or `false`
- `Parent: Business Term`, `Parent: Metric`, `Parent: Domain`: leave blank
- `Format Type` valid values: `Number`, `Decimal`, `Percentage`, `Text`, `Fraction`, `Time`, `Date`, `Datetime` — do NOT use `String`, `Boolean`, or `Integer` (rejected on import; use `Text` for string/boolean, `Number` for integer)
- `Classifications`: leave blank on import — classification assets don't exist yet at this stage. Run `/cdgc-technical-setup` Step 7 after MCC scan to link them via `cdgc_link_classifications.py`
- `Reference Data`: leave blank — requires Reference 360 assets in the org; populating this fails import with "Invalid reference Id"

#### Data Set
Sheet name: `Data Set`
Columns: `Reference ID`, `Name`, `Description`, `Lifecycle`, `Operation`, `Parent: AI System`, `Parent: System`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- **Single parent rule:** populate `Parent: System` OR `Parent: AI System` — never both on the same row
- `Parent: System` format: `System Name | <PREFIX>SYS-X` (e.g., `Core Banking System | RKFSYS-1`)
- Populating `Parent: System` automatically creates the `System → Data Set (is a Strategic Source for)` relationship — do NOT include this relationship in the Relationships file or it will cause "Parent already exists" errors

#### Data Quality Rule Template
Sheet name: `Data Quality Rule Template`
Columns: `Reference ID`, `Name`, `Description`, `Criticality`, `Dimension`, `Enable Automation`, `Frequency`, `Input Port Name`, `Lifecycle`, `Measuring Method`, `Output Port Name`, `Technical Description`, `Technical Rule Reference`, `Target`, `Threshold`, `Primary Glossary`, `Secondary Glossary`, `Operation`, `Stakeholder: Governance Owner`, `Stakeholder: Governance Administrator`
- **Column header is `Output Port Name` (correct English spelling). Use `DQ_RESULT` as the value for all rows — this is what the CDGC import engine expects. Do NOT use `Output` or `PASS_FAIL` as the value — those cause silent FAILED jobs with `tasks: []`.**
- `Criticality` valid values: `High`, `Medium`, `Low`
- `Dimension` valid values: `Accuracy`, `Validity`, `Completeness`, `Consistency`, `Uniqueness`, `Timeliness` — do NOT use `Conformity` (rejected)
- `Enable Automation`: `true` or `false`
- `Frequency` valid values: `Daily`, `Weekly`, `Monthly` ONLY — do NOT use `Hourly`, `On Demand`, or `Real-time` (all rejected on import)
- `Measuring Method`: use `TechnicalScript` for demo environments — allows SQL/expression in `Technical Description`. Do NOT use `InformaticaCloudDataQuality` — it requires a `Technical Rule Reference` (a live CDQE rule ID from the org) and will fail without one.
- `Target` / `Threshold`: numeric values only (e.g., `100`, `0`) — no percent sign, no `%`
- `Primary Glossary`: **name only** (e.g., `Social Security Number`) — do NOT use `Name | RefID` format (rejected). This links the DQ Rule to the Business Term; the relationship appears on both sides in the CDGC UI. DQ Rule Templates must be imported after Business Terms — glossary links are validated on import.

#### Relationships
Sheet name: `Relationships`
Columns: `Source Asset`, `Source Asset Type`, `Target Asset`, `Target Asset Type`, `Relationship Type`, `Operation`
- All asset references must use Reference IDs (e.g., `RKFPOL-1`, `RKFBT-23`) — display names will fail silently
- Valid relationship types:
  - Policy → Business Term: `is Regulating`
  - Policy → Domain: `is Regulating`
  - Data Set → Business Term: `is Defined by`
  - Business Term → Business Term: `is Related to`
- **Do NOT include** `System → Data Set (is a Strategic Source for)` — this is auto-created by `Parent: System` in the Data Set import. Including it here will cause "Parent already exists" errors that abort the entire batch.
- **Import last** — all referenced assets must exist first

---

## Step 3 — Vertical defaults

Select the matching vertical based on the customer's industry from Step 1. Adapt all names to the specific customer.

---

### Financial Services

Use for banks, credit unions, capital markets, insurance, and fintech customers.

### Domains (4)
- `Customer & KYC` — customer identity, onboarding, KYC compliance
- `Transactions` — payment transactions, trade settlement
- `General Ledger` — accounting entries, financial reporting
- `Risk & Regulatory` — credit risk, market risk, regulatory reporting

### Subdomains (9)
- Customer & KYC: Customer Identity, KYC & Compliance, Customer Segmentation
- Transactions: Payment Processing, Trade Settlement
- General Ledger: Accounting Entries, Financial Close
- Risk & Regulatory: Credit Risk, Regulatory Reporting

### Regulations (7)
BCBS 239, CCAR, FATCA, BSA/AML, SOX, MiFID II, GDPR

### Policies (5)
- Data Quality Standards (Data Standards)
- Customer Data Privacy Policy (Conduct Standards)
- Regulatory Reporting Policy (Business Rule)
- Data Retention Policy (Technical Standards)
- GL Reconciliation Policy (Business Rule)

### Systems (4) — use valid System Purpose values only
- Core Banking System (System Purpose: `Core Client & Transaction Processing`)
- Risk Management Platform (System Purpose: `Risk Function`)
- Regulatory Reporting System (System Purpose: `Regulatory Reporting`)
- Data Warehouse (System Purpose: `Warehouse & DataMart`)

### Data Sets (5)
- Customer Master (Customer & KYC)
- Transaction History (Transactions)
- GL Entry Register (General Ledger)
- Risk Exposure Data (Risk & Regulatory)
- Regulatory Submissions (Risk & Regulatory)

### Business Terms — 31 across all 4 domains

**Customer & KYC:** Customer ID, Social Security Number, Date of Birth, Email Address, Phone Number, KYC Status, Tax Residency Country, Country of Citizenship, Credit Score

**Transactions:** Transaction ID, Transaction Amount, Transaction Type, Transaction Date, Post Date, Currency Code, CTR Flag, Batch ID

**General Ledger:** GL Balance, GL Account Number, Subledger Balance, Debit Amount, Credit Amount, Entry Status

**Risk & Regulatory:** Capital Ratio, Risk-Weighted Asset, Probability of Default, Loss Given Default, Exposure at Default, BCBS 239 Principle, CCAR, Y-9C Report

### DQ Rule Templates (10)
- SSN Not Null (Completeness, High)
- SSN Format Validity (Validity, High)
- Credit Score Range 300–850 (Validity, High)
- Tax Residency Required for Non-US (Completeness, High)
- Transaction Amount Not Zero (Completeness, High)
- Currency Code ISO 4217 (Validity, High)
- CTR Flag for Transactions >$10K (Completeness, High)
- GL Subledger Balance Match (Consistency, High)
- GL Entry Not Zero (Validity, High)
- Debit Credit Balance per Batch (Consistency, High)

### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Healthcare

Use for hospitals, health systems, payers, and life sciences customers.

#### Domains (4)
- `Patient` — patient identity, demographics, medical history
- `Clinical` — diagnoses, procedures, medications, lab results
- `Claims & Billing` — insurance claims, reimbursements, payer data
- `Compliance & Privacy` — HIPAA, PHI governance, audit trails

#### Subdomains (9)
- Patient: Patient Identity, Patient Demographics, Medical History
- Clinical: Diagnoses & Procedures, Medications, Lab Results
- Claims & Billing: Claims Processing, Payer Management
- Compliance & Privacy: PHI Governance, Audit & Reporting

#### Regulations (6)
- HIPAA Privacy Rule (Government Regulation, Issuing Body: U.S. Department of Health & Human Services)
- HIPAA Security Rule (Government Regulation, Issuing Body: U.S. Department of Health & Human Services)
- HITECH Act (Government Regulation, Issuing Body: U.S. Congress)
- CMS Conditions of Participation (Government Regulation, Issuing Body: Centers for Medicare & Medicaid Services)
- HL7 FHIR (Industry Standard, Issuing Body: Health Level Seven International)
- ICD-10 (Industry Standard, Issuing Body: World Health Organization)

#### Policies (5)
- PHI Data Protection Policy (Conduct Standards)
- Data Quality Standards (Data Standards)
- Minimum Necessary Use Policy (Business Rule)
- Data Retention & Disposal Policy (Technical Standards)
- Breach Notification Policy (Business Rule)

#### Systems (4) — use valid System Purpose values only
- Electronic Health Record (System Purpose: `Core Client & Transaction Processing`)
- Claims Management System (System Purpose: `Core Client & Transaction Processing`)
- Clinical Data Warehouse (System Purpose: `Warehouse & DataMart`)
- Regulatory Reporting System (System Purpose: `Regulatory Reporting`)

#### Data Sets (5)
- Patient Master (Patient)
- Clinical Encounters (Clinical)
- Claims Register (Claims & Billing)
- Lab Results (Clinical)
- Compliance Audit Log (Compliance & Privacy)

#### Business Terms — 28 across all 4 domains

**Patient:** Patient ID, Medical Record Number (MRN), Date of Birth, Gender, Insurance Member ID, Primary Care Provider, Consent Status

**Clinical:** Diagnosis Code (ICD-10), Procedure Code (CPT), Medication Name, Lab Test Code, Lab Result Value, Encounter Date, Attending Physician

**Claims & Billing:** Claim ID, Claim Amount, Payer ID, National Provider Identifier (NPI), Remittance Amount, Denial Reason Code, Service Date

**Compliance & Privacy:** PHI Indicator, De-identification Status, Consent Type, Audit Event Type

#### DQ Rule Templates (10)
- MRN Not Null (Completeness, High)
- ICD-10 Code Format Validity (Validity, High)
- CPT Code Format Validity (Validity, High)
- NPI Format Check (Validity, High)
- Claim Amount Not Zero (Completeness, High)
- PHI Flag Required (Completeness, High)
- Encounter Date Not Future (Validity, High)
- Lab Result Value Range (Validity, Medium)
- Consent Status Populated (Completeness, High)
- Duplicate Patient Check (Uniqueness, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Retail & CPG

Use for retailers, consumer goods, e-commerce, and grocery customers.

#### Domains (4)
- `Customer` — customer identity, loyalty, segmentation
- `Product` — product catalog, pricing, attributes
- `Supply Chain` — inventory, suppliers, logistics
- `Transactions` — POS, e-commerce, returns

#### Subdomains (9)
- Customer: Customer Identity, Loyalty & Segmentation, Customer Service
- Product: Product Catalog, Pricing & Promotions
- Supply Chain: Inventory Management, Supplier Management
- Transactions: Point of Sale, E-Commerce, Returns & Refunds

#### Regulations (5)
GDPR, CCPA, PCI-DSS, California Proposition 65, GS1 Standards

#### Policies (5)
- Customer Data Privacy Policy (Conduct Standards)
- Product Data Standards (Data Standards)
- Inventory Accuracy Policy (Business Rule)
- PCI Compliance Policy (Technical Standards)
- Data Retention Policy (Technical Standards)

#### Systems (4) — use valid System Purpose values only
- Point of Sale System (System Purpose: `Core Client & Transaction Processing`)
- E-Commerce Platform (System Purpose: `Core Client & Transaction Processing`)
- ERP / Inventory System (System Purpose: `Master Data Management`)
- Customer Data Platform (System Purpose: `Warehouse & DataMart`)

#### Data Sets (5)
- Customer Master (Customer)
- Product Catalog (Product)
- Transaction History (Transactions)
- Inventory Ledger (Supply Chain)
- Supplier Register (Supply Chain)

#### Business Terms — 28 across all 4 domains

**Customer:** Customer ID, Email Address, Loyalty Tier, Customer Lifetime Value, Opt-In Status, Date of Birth, Segment Code

**Product:** SKU, Product Name, Category, Unit Price, UPC Barcode, Brand, Margin

**Supply Chain:** Supplier ID, Lead Time, Reorder Point, Stock on Hand, Purchase Order Number, Warehouse Location

**Transactions:** Transaction ID, Transaction Amount, Transaction Date, Payment Method, Store ID, Return Flag, Discount Amount

#### DQ Rule Templates (10)
- Customer Email Format (Validity, High)
- SKU Not Null (Completeness, High)
- UPC Barcode Format (Validity, High)
- Unit Price Not Zero (Completeness, High)
- Transaction Amount Not Negative (Validity, High)
- Stock on Hand Not Negative (Validity, High)
- Duplicate Customer Email (Uniqueness, High)
- Lead Time Reasonable Range (Validity, Medium)
- Opt-In Status Populated (Completeness, High)
- Discount Not Exceed Price (Consistency, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Insurance

Use for property & casualty, life, health insurance carriers, reinsurance, and insurance brokerage customers.

#### Domains (4)
- `Policy & Underwriting` — policy lifecycle, risk assessment, coverage
- `Claims` — claims intake, adjudication, settlement, fraud
- `Customer` — policyholder identity, agents, beneficiaries
- `Risk & Compliance` — actuarial data, regulatory filings, reserving

#### Subdomains (9)
- Policy & Underwriting: Policy Administration, Underwriting & Rating, Renewals
- Claims: Claims Intake, Claims Adjudication, Fraud Detection
- Customer: Policyholder Management, Agent & Broker Management
- Risk & Compliance: Actuarial Reserving, Regulatory Reporting

#### Regulations (7)
- Solvency II (Industry Standard, Issuing Body: European Insurance and Occupational Pensions Authority)
- NAIC Model Laws (Industry Standard, Issuing Body: National Association of Insurance Commissioners)
- IFRS 17 (Industry Standard, Issuing Body: International Accounting Standards Board)
- State DOI Regulations (Government Regulation, Issuing Body: State Departments of Insurance)
- GDPR (Government Regulation, Issuing Body: European Union)
- CCPA (Government Regulation, Issuing Body: State of California)
- Anti-Money Laundering (AML) (Government Regulation, Issuing Body: FinCEN / FATF)

#### Policies (5)
- Underwriting Data Quality Standards (Data Standards)
- Claims Data Integrity Policy (Business Rule)
- Customer Data Privacy Policy (Conduct Standards)
- Actuarial Data Standards (Technical Standards)
- Regulatory Reporting Policy (Business Rule)

#### Systems (4) — use valid System Purpose values only
- Policy Administration System (System Purpose: `Core Client & Transaction Processing`)
- Claims Management System (System Purpose: `Core Client & Transaction Processing`)
- Actuarial Modeling Platform (System Purpose: `Risk Function`)
- Regulatory Reporting System (System Purpose: `Regulatory Reporting`)

#### Data Sets (5)
- Policyholder Master (Customer)
- Policy Register (Policy & Underwriting)
- Claims Register (Claims)
- Actuarial Reserve Data (Risk & Compliance)
- Regulatory Submissions (Risk & Compliance)

#### Business Terms — 28 across all 4 domains

**Policy & Underwriting:** Policy Number, Coverage Type, Premium Amount, Deductible, Policy Effective Date, Policy Expiration Date, Underwriting Score

**Claims:** Claim ID, Claim Date, Claim Amount, Loss Type, Claim Status, Settlement Amount, Fraud Indicator

**Customer:** Policyholder ID, Date of Birth, Risk Profile, Agent ID, Beneficiary Name, Contact Preference, KYC Status

**Risk & Compliance:** Loss Ratio, Combined Ratio, Actuarial Reserve Amount, Solvency Capital Requirement, Reinsurance Treaty ID, Regulatory Filing Date, Risk Classification

#### DQ Rule Templates (10)
- Policy Number Not Null (Completeness, High)
- Premium Amount Not Zero (Completeness, High)
- Policy Date Range Valid (Validity, High)
- Claim Amount Not Negative (Validity, High)
- Loss Ratio Range Check (Validity, High)
- Fraud Indicator Populated (Completeness, High)
- Deductible Not Exceed Coverage (Consistency, High)
- Policyholder DOB Not Future (Validity, High)
- Duplicate Claim Check (Uniqueness, High)
- Reserve Amount Not Negative (Validity, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Public Sector & Government

Use for federal, state, and local government agencies, defense, and public utilities customers.

#### Domains (4)
- `Citizen Services` — citizen identity, benefits, case management
- `Program & Operations` — grants, contracts, agency programs
- `Financial Management` — appropriations, expenditures, audit
- `Compliance & Reporting` — regulatory filings, oversight, FOIA

#### Subdomains (9)
- Citizen Services: Citizen Identity, Benefits Administration, Case Management
- Program & Operations: Grants Management, Contract Management
- Financial Management: Budget & Appropriations, Expenditure Tracking
- Compliance & Reporting: Regulatory Reporting, Audit & Oversight

#### Regulations (7)
- FISMA (Government Regulation, Issuing Body: U.S. Congress / NIST)
- FedRAMP (Government Regulation, Issuing Body: U.S. General Services Administration)
- OMB Circular A-123 (Government Regulation, Issuing Body: U.S. Office of Management and Budget)
- NIST SP 800-53 (Industry Standard, Issuing Body: National Institute of Standards and Technology)
- Privacy Act of 1974 (Government Regulation, Issuing Body: U.S. Congress)
- FOIA (Government Regulation, Issuing Body: U.S. Congress)
- ATO (Authority to Operate) (Industry Standard, Issuing Body: Federal Agency ISSO)

#### Policies (5)
- Data Quality Standards (Data Standards)
- Personally Identifiable Information (PII) Policy (Conduct Standards)
- Records Retention Policy (Technical Standards)
- Federal Reporting Compliance Policy (Business Rule)
- Data Access & Classification Policy (Technical Standards)

#### Systems (4) — use valid System Purpose values only
- Case Management System (System Purpose: `Core Client & Transaction Processing`)
- Financial Management System (System Purpose: `Finance Function`)
- Grants Management System (System Purpose: `Core Client & Transaction Processing`)
- Data Analytics Platform (System Purpose: `Warehouse & DataMart`)

#### Data Sets (5)
- Citizen Registry (Citizen Services)
- Benefits Register (Citizen Services)
- General Ledger (Financial Management)
- Grants & Contracts Register (Program & Operations)
- Compliance Submissions (Compliance & Reporting)

#### Business Terms — 28 across all 4 domains

**Citizen Services:** Citizen ID, Social Security Number, Benefits Eligibility Status, Case ID, Case Worker ID, Program Enrollment Date, Benefit Amount

**Program & Operations:** Grant ID, Contract ID, Agency Code, Program Name, Award Amount, Period of Performance, Vendor ID

**Financial Management:** Appropriation Code, Object Class Code, Obligation Amount, Expenditure Amount, Fund Code, Fiscal Year, Budget Authority

**Compliance & Reporting:** FOIA Request ID, Audit Finding, Compliance Status, Report Submission Date, Classification Level, PII Indicator

#### DQ Rule Templates (10)
- Citizen ID Not Null (Completeness, High)
- SSN Format Validity (Validity, High)
- Benefits Eligibility Status Valid (Validity, High)
- Obligation Amount Not Negative (Validity, High)
- Expenditure Not Exceed Appropriation (Consistency, High)
- Grant Award Amount Not Zero (Completeness, High)
- PII Indicator Required (Completeness, High)
- Fiscal Year Format Valid (Validity, High)
- Compliance Status Populated (Completeness, High)
- Duplicate Citizen Record Check (Uniqueness, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Oil & Gas

Use for upstream exploration & production, midstream pipeline, downstream refining, oilfield services, and integrated energy companies.

#### Domains (4)
- `Assets & Operations` — wells, facilities, equipment, production data
- `HSE & Compliance` — health, safety, environment, regulatory permits
- `Supply Chain & Procurement` — vendors, materials, logistics, contracts
- `Finance & Commercial` — production accounting, trading, revenue, joint ventures

#### Subdomains (9)
- Assets & Operations: Well Management, Facility & Equipment, Production Reporting
- HSE & Compliance: Incident Management, Environmental Permits, Regulatory Reporting
- Supply Chain & Procurement: Vendor Management, Materials & Inventory
- Finance & Commercial: Production Accounting, Joint Venture Accounting

#### Regulations (7)
- BSEE Regulations (Government Regulation, Issuing Body: Bureau of Safety and Environmental Enforcement)
- EPA Clean Air Act (Government Regulation, Issuing Body: U.S. Environmental Protection Agency)
- EPA Clean Water Act (Government Regulation, Issuing Body: U.S. Environmental Protection Agency)
- PHMSA Pipeline Safety Regulations (Government Regulation, Issuing Body: Pipeline and Hazardous Materials Safety Administration)
- OSHA Process Safety Management (Government Regulation, Issuing Body: Occupational Safety and Health Administration)
- SEC Regulation S-X (Government Regulation, Issuing Body: U.S. Securities and Exchange Commission)
- EITI Standard (Industry Standard, Issuing Body: Extractive Industries Transparency Initiative)

#### Policies (5)
- Asset Data Quality Standards (Data Standards)
- HSE Incident Reporting Policy (Business Rule)
- Environmental Compliance Data Policy (Conduct Standards)
- Production Accounting Standards (Technical Standards)
- Vendor & Contract Data Policy (Business Rule)

#### Systems (4) — use valid System Purpose values only
- SCADA / Historian (System Purpose: `Core Client & Transaction Processing`)
- Enterprise Asset Management System (System Purpose: `Master Data Management`)
- Production Accounting System (System Purpose: `Finance Function`)
- HSE Management System (System Purpose: `Regulatory Reporting`)

#### Data Sets (5)
- Well Master (Assets & Operations)
- Production Volume Register (Assets & Operations)
- HSE Incident Log (HSE & Compliance)
- Vendor & Contract Register (Supply Chain & Procurement)
- Joint Venture Ledger (Finance & Commercial)

#### Business Terms — 28 across all 4 domains

**Assets & Operations:** Well ID, API Well Number, Field Name, Production Zone, Daily Oil Production (BOE), Water Cut Percentage, Wellhead Pressure, Run Ticket Number

**HSE & Compliance:** Incident ID, Incident Severity, Lost Time Injury (LTI), Process Safety Event, Environmental Release Volume, Permit Number, Spill Indicator

**Supply Chain & Procurement:** Vendor ID, Purchase Order Number, Material Number, Lead Time (Days), Contract Value, Approved Vendor Indicator, Inventory On-Hand

**Finance & Commercial:** AFE Number, Joint Venture ID, Working Interest Percentage, Royalty Rate, Revenue Deduction Code, Production Month, Net Revenue Interest

#### DQ Rule Templates (10)
- API Well Number Format (Validity, High)
- Daily Production Not Negative (Validity, High)
- Run Ticket Not Null (Completeness, High)
- Incident Severity Populated (Completeness, High)
- Permit Number Not Null (Completeness, High)
- Environmental Release Volume Not Negative (Validity, High)
- Working Interest Percentage Range 0–100 (Validity, High)
- Royalty Rate Range 0–100 (Validity, High)
- AFE Number Not Null (Completeness, High)
- Duplicate Well Record Check (Uniqueness, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

### Manufacturing

Use for discrete manufacturing, process manufacturing, industrial equipment, automotive, aerospace & defense, and consumer goods production customers.

#### Domains (4)
- `Product & Engineering` — product definitions, BOMs, specifications, engineering change orders
- `Production & Operations` — work orders, production runs, shop floor, OEE
- `Quality` — quality control, non-conformance, inspections, certifications
- `Supply Chain` — suppliers, raw materials, inventory, logistics, demand planning

#### Subdomains (9)
- Product & Engineering: Product Master, Bill of Materials, Engineering Change Management
- Production & Operations: Work Order Management, Shop Floor Operations
- Quality: Quality Control, Non-Conformance Management, Supplier Quality
- Supply Chain: Supplier Management, Inventory & Warehousing, Demand & Supply Planning

#### Regulations (6)
- ISO 9001 Quality Management (Industry Standard, Issuing Body: International Organization for Standardization)
- ISO 14001 Environmental Management (Industry Standard, Issuing Body: International Organization for Standardization)
- OSHA General Industry Standards (Government Regulation, Issuing Body: Occupational Safety and Health Administration)
- EPA Toxic Release Inventory (Government Regulation, Issuing Body: U.S. Environmental Protection Agency)
- ITAR (Government Regulation, Issuing Body: U.S. Department of State)
- RoHS / REACH (Government Regulation, Issuing Body: European Union)

#### Policies (5)
- Product Data Quality Standards (Data Standards)
- Quality Management Policy (Business Rule)
- Non-Conformance Reporting Policy (Business Rule)
- Environmental & Compliance Data Policy (Conduct Standards)
- Supplier Data Standards (Technical Standards)

#### Systems (4) — use valid System Purpose values only
- ERP / Manufacturing Execution System (System Purpose: `Core Client & Transaction Processing`)
- Product Lifecycle Management System (System Purpose: `Master Data Management`)
- Quality Management System (System Purpose: `Regulatory Reporting`)
- Supply Chain Planning Platform (System Purpose: `Warehouse & DataMart`)

#### Data Sets (5)
- Product Master (Product & Engineering)
- Bill of Materials (Product & Engineering)
- Work Order Register (Production & Operations)
- Non-Conformance Register (Quality)
- Supplier & Material Master (Supply Chain)

#### Business Terms — 28 across all 4 domains

**Product & Engineering:** Part Number, Part Description, Revision Level, Unit of Measure, Bill of Materials (BOM), Engineering Change Order (ECO) Number, Product Classification Code

**Production & Operations:** Work Order Number, Routing Step, Machine ID, Planned Cycle Time, Actual Cycle Time, Overall Equipment Effectiveness (OEE), Shift Code

**Quality:** Inspection Lot Number, Non-Conformance Report (NCR) Number, Defect Code, Defect Quantity, Corrective Action Status, First Pass Yield, Certificate of Conformance Number

**Supply Chain:** Supplier ID, Raw Material Number, Reorder Point, Safety Stock Level, Purchase Order Number, Goods Receipt Number, Lead Time (Days)

#### DQ Rule Templates (10)
- Part Number Not Null (Completeness, High)
- BOM Revision Level Populated (Completeness, High)
- Work Order Routing Complete (Completeness, High)
- Actual Cycle Time Not Negative (Validity, High)
- OEE Range 0–100 (Validity, High)
- NCR Defect Code Populated (Completeness, High)
- First Pass Yield Range 0–100 (Validity, High)
- Supplier ID Not Null (Completeness, High)
- Safety Stock Not Negative (Validity, High)
- Duplicate Part Number Check (Uniqueness, High)

#### Relationships (25)
- Policy → Business Term `is Regulating`: 8 key linkages
- Policy → Domain `is Regulating`: 4 (one per domain)
- System → Data Set `is a Strategic Source for`: 5
- Data Set → Business Term `is Defined by`: 8

---

## Step 3b — Generate HTML viewers (run immediately after files are written)

After all 14 xlsx files are written, run the HTML generation script from `/cdgc-demo-live` (the section labeled "HTML Output — run immediately after delivery script"). Fill in `COMPANY_NAME` and `NEW_PREFIX` from what the user provided.

This produces two files and opens both in the browser:
- `CDGC_<CompanyName>_Preview.html` — standalone file browser, record counts in sidebar
- `CDGC_Review_Workbook_<PREFIX>_v1.html` — Import Preview tab (default) + Overview & TODOs tab, sidebar shows both record count and issue badge

Then open both:
```bash
open ~/Downloads/CDGC_<CompanyName>_Preview.html
open ~/Downloads/CDGC_Review_Workbook_<PREFIX>_v1.html
```

---

## Step 4 — Choose import method and import

Now that the files are generated, ask the user how they would like to import them:

```
Your 14 import files are ready, along with two interactive HTML viewers:

  📋 CDGC_<CompanyName>_Preview.html       — Browse all 14 files
  📝 CDGC_Review_Workbook_<PREFIX>_v1.html — Action items and per-file review (open in browser)

How would you like to load them into CDGC?

  A) Manual UI (default)
     Upload each file yourself via the CDGC UI.
     Works in all environments. No credentials needed.

  B) API (automated)
     I'll import all 14 files programmatically and poll until complete.
     Requires your IDMC org URL, username, and password.
     Not available for SAML-only orgs without API access enabled.

If you're unsure, choose A — the files are ready to upload at any time.
```

Store the choice as `IMPORT_METHOD` (A or B). If B, also collect:
- `ORG_URL` — the base API URL for the user's pod (e.g., `https://idmc-api.dmp-us.informaticacloud.com`)
- `LOGIN_URL` — the IDMC login URL for the user's region (e.g., `https://dmp-us.informaticacloud.com`)
- `USERNAME` — IDMC username (email)
- `PASSWORD` — IDMC password

Inform the user: credentials are used only for this session to generate the JWT token and are not stored anywhere.

### Known reasons API import may not work

| Reason | Recommendation |
|--------|---------------|
| No Import privilege in Administrator | Ask org admin to grant Import privilege, or use Option A |
| SAML-only org with no local user accounts | API auth requires a local IDMC account — use Option A |
| Pod URL unknown | Find it in IDMC → Administrator → Organization → Pod URL |
| Firewall or network restrictions blocking outbound HTTPS | Use Option A |
| API rate limit hit (120 calls/min, 10,000/day) | The 14-file import uses ~14–28 calls — well within limits under normal use |
| JWT token expired mid-import (30 min TTL) | Script handles this by re-authenticating if a 401 is returned |

Branch on `IMPORT_METHOD`:

---

### Option A — Manual UI import

Tell the user to import files in this exact order:

```
01_Domain.xlsx              ← no dependencies
02_Subdomain.xlsx           ← depends on Domains
03_Regulation.xlsx          ← no dependencies
04_Policy.xlsx              ← no dependencies
05_Legal_Entity.xlsx        ← no dependencies
06_Business_Area.xlsx       ← no dependencies
07_Geography.xlsx           ← no dependencies
08_System.xlsx              ← no dependencies
09_AI_System.xlsx           ← no dependencies
10_AI_Model.xlsx            ← depends on AI Systems
11_Business_Term.xlsx       ← depends on Subdomains
12_Data_Set.xlsx            ← depends on Systems / AI Systems
13_DQ_Rule_Template.xlsx    ← depends on Business Terms
14_Relationships.xlsx       ← depends on ALL above
```

**Import method:** CDGC UI → Gear icon → Import → Upload file → Map columns (auto-maps if headers match) → Import

**One file at a time** — wait for COMPLETED status before uploading the next file. Do not combine sheets into one workbook.

**Import 14_Relationships.xlsx last** — all referenced assets must exist first.

**There is no file 15 in the template package.** DQ Rule Occurrences (which bind a DQ Rule
Template to a specific physical column) are generated after the MCC scan — not imported as
part of the 14-file package. Their Primary Data Element paths contain the MCC catalog source
name and exact DB/Schema/Table/Column, which only exist post-scan. Run
`cdgc_create_dq_occurrences.py` after the MCC scan to generate and import the occurrence
file. See `/cdgc-technical-setup` Step 6b for the full DQ sequence.

---

### Option B — API import

Write and execute a Python script that:

1. **Authenticates** using the two-step JWT flow:
   - POST to `<LOGIN_URL>/identity-service/api/v1/Login` with username/password → get `sessionId` and `orgId`
   - GET `<LOGIN_URL>/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234` with `IDS-SESSION-ID: <sessionId>` cookie → get JWT access token

2. **Imports each file in order** by POSTing to:
   `POST <ORG_URL>/data360/content/import/v1/assets`
   Headers: `Authorization: Bearer <jwt_token>`, `X-INFA-ORG-ID: <orgId>`
   Body: multipart form — `file=@<path_to_xlsx>`, `config={"validationPolicy": "CONTINUE_ON_ERROR_WARNING"}`
   Capture the `jobId` from the response.

3. **Polls each job** until complete:
   `GET <ORG_URL>/data360/observable/v1/jobs/<jobId>`
   Poll every 5 seconds. Terminal statuses: `COMPLETED`, `FAILED`, `COMPLETED_WITH_ERRORS`.
   Print status updates inline.

4. **Handles token expiry** — if any request returns HTTP 401, re-authenticate and retry once before failing.

5. **Stops on hard failure** — if a job returns `FAILED`, stop and report which file failed and the error message. Do not proceed to the next file, as downstream files may depend on it.

6. **Reports a summary** on completion:
   ```
   Import complete — 14 files processed
     ✓ 01_Domain.xlsx              — COMPLETED
     ✓ 02_Subdomain.xlsx           — COMPLETED
     ...
     ✓ 14_Relationships.xlsx       — COMPLETED
   ```

#### Script structure

This is the validated, hardened version — tested end-to-end May 2026. Also available as `cdgc_api_import.py` in the repo.

Key design decisions:
- **`requests` multipart with explicit XLSX content type** — curl subprocess format was rejected server-side (jobs returned COMPLETED with `tasks:[]`); `requests` with explicit content types is the only working approach
- **`poll_job` circuit breaker** — 72 polls max (6 minutes), 502/503/504 retry, empty response handling
- **Post-import verification scan** — reuses existing JWT to confirm actual counts per asset type

```python
import requests
import getpass
import time
import sys
import json
from pathlib import Path

LOGIN_URL  = "https://dmp-us.informaticacloud.com"
ORG_URL    = "https://idmc-api.dmp-us.informaticacloud.com"
IMPORT_DIR = Path("~/Downloads/CDGC_Import_<CustomerName>/").expanduser()

FILES_IN_ORDER = [
    "01_Domain.xlsx",
    "02_Subdomain.xlsx",
    "03_Regulation.xlsx",
    "04_Policy.xlsx",
    "05_Legal_Entity.xlsx",
    "06_Business_Area.xlsx",
    "07_Geography.xlsx",
    "08_System.xlsx",
    "09_AI_System.xlsx",
    "10_AI_Model.xlsx",
    "11_Business_Term.xlsx",
    "12_Data_Set.xlsx",
    "13_DQ_Rule_Template.xlsx",
    "14_Relationships.xlsx",
]

def authenticate(username, password):
    resp = requests.post(
        f"{LOGIN_URL}/identity-service/api/v1/Login",
        json={"username": username, "password": password},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["sessionId"]
    org_id = data["orgId"]
    resp = requests.get(
        f"{LOGIN_URL}/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=1234",
        headers={"IDS-SESSION-ID": session_id},
        cookies={"USER_SESSION": session_id},
        timeout=30
    )
    resp.raise_for_status()
    token_data = resp.json()
    jwt_token = token_data.get("token") or token_data.get("jwt_token") or token_data.get("access_token")
    print(f"  ✓ Authenticated — orgId: {org_id}")
    return jwt_token, org_id

def import_file(jwt_token, org_id, filepath):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-INFA-ORG-ID": org_id,
    }
    with open(filepath, "rb") as f:
        files = {
            "file": (filepath.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "config": (None, '{"validationPolicy":"CONTINUE_ON_ERROR_WARNING"}', "application/json"),
        }
        resp = requests.post(
            f"{ORG_URL}/data360/content/import/v1/assets",
            headers=headers,
            files=files,
            timeout=60)
    if resp.status_code == 401:
        return None, "401"
    if not resp.text.strip():
        return None, "Empty response from import endpoint"
    try:
        data = resp.json()
    except Exception:
        return None, f"Invalid response: {resp.text[:200]}"
    if resp.status_code not in (200, 201, 202):
        return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
    job_id = data.get("jobId") or data.get("id")
    if job_id:
        return job_id, None
    return None, f"No jobId in response: {resp.text[:300]}"

def poll_job(jwt_token, org_id, job_id, filename):
    url = f"{ORG_URL}/data360/observable/v1/jobs/{job_id}"
    headers = {"Authorization": f"Bearer {jwt_token}", "X-INFA-ORG-ID": org_id}
    terminal = {"COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED", "PARTIAL_SUCCESS"}
    dots = 0
    for attempt in range(72):  # max 6 minutes
        try:
            resp = requests.get(url, headers=headers, timeout=30)
        except requests.exceptions.RequestException:
            time.sleep(5)
            continue
        if resp.status_code in (429, 502, 503, 504):
            time.sleep(10)
            continue
        if not resp.text.strip():
            time.sleep(5)
            continue
        try:
            data = resp.json()
        except Exception:
            time.sleep(5)
            continue
        status = data.get("status", "UNKNOWN")
        if status in terminal:
            print(f"\r  [{filename}] {status}          ")
            if status in ("COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED", "PARTIAL_SUCCESS"):
                print(f"  ⚠ Detail: {json.dumps(data.get('errors', data.get('detail', '')))[:300]}")
            return status, data
        print(f"\r  [{filename}] {status}{'.' * (dots % 4)}   ", end="", flush=True)
        dots += 1
        time.sleep(5)
    print(f"\r  [{filename}] TIMEOUT — job did not complete in 6 minutes")
    return "TIMEOUT", {}

# ── Main ──────────────────────────────────────────────────────────────────────

print("\nCDGC API Import")
print("───────────────────────────────────────────")
username = input("IDMC Username: ")
password = getpass.getpass("IDMC Password: ")

print("\nAuthenticating...")
jwt_token, org_id = authenticate(username, password)

results = []
for fname in FILES_IN_ORDER:
    fpath = IMPORT_DIR / fname
    if not fpath.exists():
        print(f"\nSKIP — file not found: {fpath}")
        results.append((fname, "SKIPPED"))
        continue

    print(f"\nImporting {fname}...")
    job_id, err = import_file(jwt_token, org_id, fpath)

    if err == "401":
        print("  Token expired — re-authenticating...")
        jwt_token, org_id = authenticate(username, password)
        job_id, err = import_file(jwt_token, org_id, fpath)

    if err:
        print(f"  FAILED to submit: {err}")
        results.append((fname, "SUBMIT_FAILED"))
        print(f"\nFATAL — stopping import. Fix {fname} and retry.")
        sys.exit(1)

    status, detail = poll_job(jwt_token, org_id, job_id, fname)
    results.append((fname, status))

    if status in ("FAILED", "TIMEOUT"):
        print(f"\nFATAL — {fname} {status}. Stopping import.")
        print(json.dumps(detail)[:500])
        sys.exit(1)

print("\n── Import Summary ──────────────────────────────────────────")
for fname, status in results:
    icon = "✓" if status == "COMPLETED" else "⚠" if status == "COMPLETED_WITH_ERRORS" else "✗"
    print(f"  {icon}  {fname:<45} {status}")
print("────────────────────────────────────────────────────────────")

# ── Verification scan ─────────────────────────────────────────────────────────
print("\nVerifying assets in org...\n")
time.sleep(3)

VERIFY_TYPES = [
    ("Domains",           "com.infa.ccgf.models.governance.Domain"),
    ("Subdomains",        "com.infa.ccgf.models.governance.Subdomain"),
    ("Regulations",       "com.infa.ccgf.models.governance.Regulation"),
    ("Policies",          "com.infa.ccgf.models.governance.Policy"),
    ("Legal Entities",    "com.infa.ccgf.models.governance.LegalEntity"),
    ("Business Areas",    "com.infa.ccgf.models.governance.BusinessArea"),
    ("Geographies",       "com.infa.ccgf.models.governance.Geography"),
    ("Systems",           "com.infa.ccgf.models.governance.System"),
    ("AI Systems",        "com.infa.ccgf.models.governance.AISystem"),
    ("AI Models",         "com.infa.ccgf.models.governance.AIModel"),
    ("Business Terms",    "com.infa.ccgf.models.governance.BusinessTerm"),
    ("Data Sets",         "com.infa.ccgf.models.governance.DataSet"),
    ("DQ Rule Templates", "com.infa.ccgf.models.governance.RuleTemplate"),
]

h_s = {"Authorization": f"Bearer {jwt_token}", "X-INFA-ORG-ID": org_id, "Content-Type": "application/json"}
grand_total = 0
for label, ct in VERIFY_TYPES:
    for attempt in range(3):
        r = requests.post(
            f"{ORG_URL}/data360/search/v1/assets?knowledgeQuery=*&segments=summary",
            headers=h_s,
            json={"from": 0, "size": 100,
                  "filterSpec": [{"type": "simple", "attribute": "core.classType", "values": [ct]}]},
            timeout=30)
        if not r.text.strip():
            time.sleep(2)
            continue
        try:
            body = r.json()
            count = len(body.get("hits", []))
            break
        except Exception:
            time.sleep(2)
            continue
    else:
        count = "?"
    grand_total += count if isinstance(count, int) else 0
    icon = "✓" if isinstance(count, int) and count > 0 else "⚠"
    print(f"  {icon}  {label:<25}: {count}")
    time.sleep(0.3)

print(f"\n  Total assets in org: {grand_total}")
print("────────────────────────────────────────────────────────────\n")
```

Fill in `IMPORT_DIR` from the customer name collected in Step 1. `LOGIN_URL` and `ORG_URL` default to `dmp-us` — change the pod region prefix if the customer is on a different pod (e.g., `dmp-eu`).

**Note:** AI Systems and AI Models will show `⚠ 0` in the verification scan — classType search is broken on suborg for those two types. Verify counts in the CDGC UI directly.

---

## Step 5 — Confirmation checklist

After all imports, verify in the CDGC UI. Then launch the **CDGC Live Dashboard** for a real-time view of all governance assets:

```
cd ~/Documents/CDGC && python3 cdgc_dashboard.py
```

You will be prompted for your IDMC username and password — use the same credentials you use to log into CDGC. Opens at http://localhost:8080 automatically once authenticated — shows live asset counts, Business Glossary, Policies, DQ Rules, AI Assets, Workflows, and API Explorer connected directly to your org.

- [ ] Glossary tab shows expected Domains with nested Subdomains
- [ ] Business Terms visible under each Subdomain
- [ ] Policies visible in Glossary
- [ ] Regulations visible in Glossary
- [ ] Systems and AI Systems visible in Glossary
- [ ] AI Models visible in Glossary
- [ ] Data Sets visible in Glossary
- [ ] DQ Rule Templates visible — search by name to confirm
- [ ] Relationships: open a Policy → Relationships tab → should show linked Business Terms
- [ ] Relationships: open a Data Set → Relationships tab → should show linked Business Terms
- [ ] System → Data Set relationships: open any System → Relationships tab → should show linked Data Sets (auto-created via Parent: System)

---

## Common errors and fixes

| Error | Fix |
|-------|-----|
| `Enter a valid value from [Create, Update, Delete]` | Operation column missing or wrong position |
| `The parent is invalid or not present` | Parent asset doesn't exist yet — check import order |
| `There are multiple parents with this asset` | Two parent columns populated on same row — leave all parent columns blank except one |
| `Imported file contains empty values` | Remove header-only sheets from the workbook |
| Pre-validation failure (empty error CSV) | Usually multiple parents on a row — check all parent columns |
| Business Terms not visible after import | Populate `Parent: Subdomain`, not `Parent: Domain` — single parent rule |
| `Parent already exists` on Relationships | `System → Data Set` already created by Parent: System in Data Set import — remove that row from Relationships |
| `Missing field: Technical Rule Reference` | `InformaticaCloudDataQuality` measuring method requires a live CDQE rule ID — change to `TechnicalScript` |
| DQ Rule Template file shows PARTIAL_COMPLETED | `Frequency` contains `Real-time` — not a valid value. Change to `Daily` or `On Demand` |
| `Invalid Primary Glossary` | `Name \| RefID` format used — use name only (e.g., `Social Security Number`) |
| Stakeholder prompt blocking import | Stakeholder field empty or not a real org user email — populate with valid email |
| Reference ID rejected on create | Prefix collides with CDGC auto-generated IDs — use customer-specific prefix (e.g., `RKFBT-`) |
| DQ Rule Template score not showing on Business Term | Expected — scores require: (1) MCC scan with Data Quality enabled, (2) 15_DQ_Rule_Occurrence.xlsx imported (generated by `cdgc_create_dq_occurrences.py` post-scan), (3) scores injected via `cdgc_dq_scores.py`. See `/cdgc-technical-setup` Step 6b. |
| Policy Type / System Type / System Purpose invalid value | Check valid values in column specs above — suborg rejects `Operational`, `Analytical`, `Reporting` for System Purpose |
| Relationship fails silently | Must use Reference IDs (e.g., `RKFBT-23`), not display names |

---

## What's next — DQ execution

Importing File 13 (DQ Rule Templates) creates rule *definitions* in CDGC, but no scores
will ever appear until rules are connected to ICDQ and bound to specific catalog columns.

**To complete the DQ pipeline, run:**
```
/cdgc-dq-setup
```

This skill covers the full 8-step sequence:
1. Build ICDQ rules with Claire
2. Fetch ICDQ artifact IDs
3. Patch File 13 with ICDQ references
4. Re-import the patched template
5. Generate File 15 (DQ Rule Occurrences) — post-scan, environment-specific
6. Import occurrences
7. Link templates to occurrences
8. Run MCC scan → real scores appear in CDGC

DQ is the third pillar of the CDGC demo story — governance + technical metadata + data quality.
Without `/cdgc-dq-setup`, columns have no DQ scores and the Data Quality tab is empty.

---

## Sharing this skill

This skill is a Markdown file at `~/.claude/commands/cdgc-setup.md`.

**To share with a colleague:**
1. Send them the file — they save it to `~/.claude/commands/cdgc-setup.md` on their machine
2. They type `/cdgc-setup` in any Claude Code session to invoke it

**To publish to a team:**
- Add the file to a shared git repo under `.claude/commands/cdgc-setup.md` at the repo root
- Anyone who clones the repo and opens Claude Code in that directory gets the skill automatically
- This is the recommended approach for Salesforce team / partner enablement

**To publish to a plugin marketplace** (advanced):
- Package as a Claude Code plugin with a `plugin.json` manifest
- Distribute via a private marketplace URL
- Team members install via `claude plugin add <marketplace-url>`
