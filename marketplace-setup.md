---
description: Build and import a full IDMC Data Marketplace demo environment for any industry vertical. Supports Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector, Oil & Gas, and Manufacturing. Generates all 14 asset type import files in the correct Informatica bulk import format.
---

# IDMC Data Marketplace Demo Setup

You are an Informatica Data Marketplace specialist. Your job is to generate a complete, importable demo environment for a customer using the official Informatica bulk import format.

## What this skill produces

14 Excel files, imported in order, covering every major asset type in IDMC Data Marketplace:

| # | File | Asset Type | Notes |
|---|------|-----------|-------|
| 01 | `01_Category.xlsx` | Category | Top-level data product categories |
| 02 | `02_Cost_Center.xlsx` | Cost Center | Organizational cost centers |
| 03 | `03_Terms_of_Use.xlsx` | Terms of Use | Data usage license agreements |
| 04 | `04_Usage_Type.xlsx` | Usage Type | Consumer intent classifications |
| 05 | `05_Delivery_Format.xlsx` | Delivery Format | File/data format options |
| 06 | `06_Delivery_Method.xlsx` | Delivery Method | Delivery channel options |
| 07 | `07_Delivery_Template.xlsx` | Delivery Template | Reusable delivery configurations |
| 08 | `08_Data_Asset.xlsx` | Data Asset | Source data assets |
| 09 | `09_Data_Collection.xlsx` | Data Collection | Curated data products |
| 10 | `10_Data_Element.xlsx` | Data Element | Individual data fields |
| 11 | `11_Delivery_Target.xlsx` | Delivery Target | Collection + delivery config links |
| 12 | `12_Data_Asset_Collection.xlsx` | Data Asset → Data Collection | Asset-to-collection linkages |
| 13 | `13_Terms_Collection.xlsx` | Terms of Use → Data Collection | ToU-to-collection linkages |
| 14 | `14_Consumer_Access.xlsx` | Consumer Access | Access grants for consumers |

---

## Step 1 — Gather customer context

Ask the user for:

1. **Customer name** (e.g., First Capital Bank) — used to brand the demo data
2. **Industry vertical** (Financial Services, Healthcare, Retail & CPG, Insurance, Public Sector, Oil & Gas, Manufacturing)
3. **Output directory** (default: `~/Downloads/Marketplace_Import_<CustomerName>/`)

If the user says "use defaults" or provides a customer name only, proceed with Financial Services defaults.

---

## Step 2 — Generate the import files

Use Python + openpyxl to generate all 14 files. Define all valid values as extensible dictionaries at the top of the script so they can be easily extended:

```python
VALID_VALUES = {
    "data_asset_type":   ["Dataset", "API", "Report", "Model", "Stream", "File", "Service"],
    "terms_of_use_type": ["Restricted", "Controlled", "Accessible"],
    "delivery_type":     ["Automatic", "Manual"],
    "status":            ["Enabled", "Disabled"],
    "delivery_format":   ["CSV", "JSON", "Parquet", "Excel", "XML", "Avro", "HL7 FHIR JSON", "ORC", "HTML", "Tableau Report"],
    "delivery_method":   ["HTTPS Download", "SFTP", "S3 Bucket", "Azure Blob", "API Access", "JDBC", "Kafka"],
    "color":             ["posy", "lilac", "orchid", "sky", "mint", "peach", "lemon"],
}
```

### Universal rules

- Sheet name must match exactly (see column specs below)
- Column order must match exactly — Marketplace reads positionally
- `Status` for Terms of Use must be `Enabled` or `Disabled` — all other objects use `Active`
- Fields marked `*` in the template are required — never leave them blank
- Do NOT include a Predefined_Values sheet with data — leave it header-only or omit
- `Reference ID` column must be present (positional requirement) but leave all values **blank** — Marketplace auto-assigns Reference IDs; populating them triggers a warning from Metadata Command Center
- Linking tables (files 12, 13, 14) must reference names exactly as they appear in the source files

---

### Sheet specs and column order

#### Category
Sheet name: `Category`
Columns: `Reference ID`, `Name*`, `Description*`, `Status*`, `Category Owners`

#### Cost Center
Sheet name: `Cost Center`
Columns: `Cost Center Name*`, `Description`

#### Terms of Use
Sheet name: `Terms of Use`
Columns: `Reference ID`, `Name*`, `Description*`, `Status*`, `Type*`, `URI`
- `Status` valid values: `Enabled`, `Disabled`
- `Type` valid values: `Restricted`, `Controlled`, `Accessible`

#### Usage Type
Sheet name: `Usage Type`
Columns: `Reference ID`, `Name*`, `Description`, `Status*`, `Color`
- `Color` valid values: `posy`, `lilac`, `orchid`, `sky`, `mint`, `peach`, `lemon`

#### Delivery Format
Sheet name: `Delivery Format`
Columns: `Reference ID`, `Format Name*`, `Status*`

#### Delivery Method
Sheet name: `Delivery Method`
Columns: `Reference ID`, `Method Name*`, `Status*`

#### Delivery Template
Sheet name: `Delivery Template`
Columns: `Reference ID`, `Name*`, `Description*`, `Status*`, `Delivery Type*`, `Delivery Process`, `System*`, `Location*`, `Delivery Formats*`, `Delivery Methods*`, `Delivery Template Owners`, `Color`
- `Delivery Type` valid values: `Automatic`, `Manual`
- `Color` valid values: `posy`, `lilac`, `orchid`, `sky`, `mint`, `peach`, `lemon`
- `Delivery Formats` and `Delivery Methods` must match names in files 05 and 06

#### Data Asset
Sheet name: `Data Asset`
Columns: `Reference ID`, `Name*`, `Description*`, `Data Source*`, `Description Source`, `Type*`, `Source Path`, `Source Path Description`, `Technical Data Asset`, `URI`, `Status*`, `Linked Data Collections`
- `Type` valid values: `Dataset`, `API`, `Report`, `Model`, `Stream`, `File`, `Service`
- `Status` valid values: `Enabled`, `Disabled`

#### Data Collection
Sheet name: `Data Collection`
Columns: `Reference ID`, `Name*`, `Purpose*`, `Category*`, `Certified Uses`, `Data Owners`, `Technical Owners`, `Status*`
- `Category` must match a Name from file 01
- `Status` valid values: `Published`, `Unpublished`

#### Data Element
Sheet name: `Data Element`
Columns: `Reference ID`, `Name*`, `Description`, `Data Asset Name*`, `URI`, `Technical Type`, `Technical Name`, `Type`, `Status*`
- `Data Asset Name` must match a Name from file 08
- `Status` valid values: `Enabled`, `Disabled`
- `Technical Type` examples: `STRING`, `INTEGER`, `DECIMAL`, `DATE`, `BOOLEAN`
- `Type` examples: `Dimension`, `Measure`, `Attribute`, `Key`

#### Delivery Target
Sheet name: `Delivery Target`
Columns: `Data Collection Name*`, `Delivery Template*`, `Delivery Target Name*`, `Description*`, `Status*`, `System*`, `Location*`, `Delivery Format*`, `Delivery Method*`
- All referenced names must match exactly

#### Data Asset — Data Collection
Sheet name: `Data Asset - Data Collection`
Columns: `Data Asset Name*`, `Data Collection Name*`

#### Terms of Use — Data Collection
Sheet name: `Terms of Use - Data Collection`
Columns: `Terms Of Use Name*`, `Data Collection Name*`

#### Consumer Access
Sheet name: `Consumer Access`
Columns: `Reference ID`, `Status*`, `Data Collection Name*`, `Delivery Target Name*`, `Data User*`, `Date Access Granted*`, `Usage Context`
- `Status` valid values: `Available`, `Pending Withdrawn`, `Withdrawn`
- `Data User` must be the email address of an existing Marketplace user in the org — leave blank if unknown; do not use fictional emails
- `Date Access Granted` format: `MM/DD/YYYY`

---

## Step 3 — Vertical defaults

Select the matching vertical. All names should be adapted to the specific customer.

---

### Financial Services

Use for banks, credit unions, capital markets, and fintech customers.

#### Categories (4)
- `Customer & KYC` — customer identity and onboarding data products
- `Transactions` — payment and settlement data products
- `General Ledger` — accounting and financial reporting data products
- `Risk & Regulatory` — risk exposure and regulatory submission data products

#### Cost Centers (4)
- Retail Banking, Corporate Banking, Risk Management, Finance & Accounting

#### Terms of Use (4)
- `Internal Analytics Only` (Controlled) — For approved internal analytics use only; no external distribution
- `Regulatory Reporting Use` (Restricted) — Restricted to regulatory reporting workflows; must comply with BCBS 239
- `Partner Data Sharing Agreement` (Accessible) — Governs sharing of non-PII data with approved commercial partners
- `Internal Operations` (Controlled) — General internal operational use; no PII permitted outside approved systems

#### Usage Types (4) with colors
- `Analytics & Reporting` (sky) — Business intelligence and dashboard reporting
- `Risk Modeling` (orchid) — Quantitative risk model development and validation
- `Regulatory Compliance` (posy) — Regulatory submission and audit support
- `Customer Intelligence` (mint) — Customer segmentation and propensity modeling

#### Delivery Formats (6)
- CSV, JSON, Parquet, Excel, HTML, Tableau Report

#### Delivery Methods (4)
- HTTPS Download, S3 Bucket, SFTP, API Access

#### Delivery Templates (4)
- `Self-Service Download` (Manual) — System: Data Warehouse, Location: downloads.bank.internal
- `API Data Feed` (Automatic) — System: API Gateway, Location: api.bank.internal/v1/data
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.bank.internal/outbound
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://bank-data-products/

#### Data Collections (5) — with category, purpose, certified uses
- `Customer Master` (Customer & KYC) — Certified master record of all customers; purpose: single source of truth for customer identity; certified uses: KYC, onboarding, segmentation
- `Transaction History` (Transactions) — Full history of payment and settlement transactions; purpose: transaction analytics and reconciliation; certified uses: reconciliation, fraud detection, reporting
- `GL Entry Register` (General Ledger) — Accounting entries across all cost centers; purpose: financial close and reporting; certified uses: financial reporting, audit, GL reconciliation
- `Risk Exposure Data` (Risk & Regulatory) — Credit and market risk exposure by counterparty; purpose: risk monitoring and stress testing; certified uses: capital calculation, CCAR, stress testing
- `Regulatory Submissions` (Risk & Regulatory) — Compiled regulatory filings data; purpose: regulatory reporting; certified uses: BCBS 239, CCAR, FATCA reporting

#### Data Assets (5) — one per collection
- `Customer Master Dataset` (Dataset) — Source: Core Banking System
- `Transaction History Dataset` (Dataset) — Source: Core Banking System
- `GL Entry Register Dataset` (Dataset) — Source: Core Banking System
- `Risk Exposure Dataset` (Dataset) — Source: Risk Management Platform
- `Regulatory Submissions Dataset` (Dataset) — Source: Regulatory Reporting System

#### Data Elements (16) — mapped to data assets
**Customer Master Dataset:** Customer ID (Key, STRING), Social Security Number (Attribute, STRING), Date of Birth (Attribute, DATE), Email Address (Attribute, STRING), Credit Score (Measure, INTEGER)
**Transaction History Dataset:** Transaction ID (Key, STRING), Transaction Amount (Measure, DECIMAL), Transaction Date (Attribute, DATE), Currency Code (Attribute, STRING)
**GL Entry Register Dataset:** GL Account Number (Key, STRING), GL Balance (Measure, DECIMAL), Entry Status (Attribute, STRING)
**Risk Exposure Dataset:** Risk-Weighted Asset (Measure, DECIMAL), Capital Ratio (Measure, DECIMAL), Probability of Default (Measure, DECIMAL)
**Regulatory Submissions Dataset:** BCBS 239 Principle (Attribute, STRING), CCAR (Attribute, STRING)

#### Delivery Targets (5) — one per collection
Each collection gets one Delivery Target using `Self-Service Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one: each Dataset links to its corresponding Collection.

#### Terms of Use → Collection links (5)
- Customer Master → Internal Analytics Only
- Transaction History → Internal Analytics Only
- GL Entry Register → Internal Operations
- Risk Exposure Data → Regulatory Reporting Use
- Regulatory Submissions → Regulatory Reporting Use

#### Consumer Access (3) sample records
- Customer Master / data.analyst@bank.com / Analytics & Reporting
- Risk Exposure Data / risk.modeler@bank.com / Risk Modeling
- Regulatory Submissions / compliance.officer@bank.com / Regulatory Compliance

---

### Healthcare

Use for hospitals, health systems, payers, and life sciences customers.

#### Categories (4)
- `Patient` — patient identity and demographic data products
- `Clinical` — diagnoses, procedures, and lab data products
- `Claims & Billing` — claims and reimbursement data products
- `Compliance & Privacy` — PHI governance and audit data products

#### Cost Centers (4)
- Clinical Operations, Revenue Cycle Management, Health Information Management, Compliance & Privacy

#### Terms of Use (4)
- `HIPAA Compliant Use` (Restricted) — All access governed by HIPAA; PHI must not be disclosed outside covered entity
- `Internal Clinical Use` (Controlled) — For authorized clinical staff only; treatment purposes only
- `Research Data Agreement` (Controlled) — De-identified data for approved research; no re-identification permitted
- `Payer Data Sharing Agreement` (Accessible) — Governs claims data sharing with contracted payers under BAA

#### Usage Types (4) with colors
- `Clinical Analytics` (sky) — Clinical outcome and quality measure analysis
- `Population Health` (mint) — Risk stratification and care gap identification
- `Revenue Cycle Optimization` (peach) — Denial management and reimbursement analytics
- `Compliance Reporting` (posy) — HIPAA audit and regulatory submission support

#### Delivery Formats (4)
- CSV, HL7 FHIR JSON, Excel, Parquet

#### Delivery Methods (4)
- HTTPS Download, API Access, SFTP, S3 Bucket

#### Delivery Templates (4)
- `Secure Clinical Download` (Manual) — System: Clinical Data Warehouse, Location: downloads.health.internal/clinical
- `FHIR API Feed` (Automatic) — System: EHR API Gateway, Location: fhir.health.internal/R4
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.health.internal/outbound
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://health-data-products/

#### Data Collections (5)
- `Patient Master` (Patient) — Certified enterprise master patient index; purpose: patient identity resolution; certified uses: care coordination, registration, identity matching
- `Clinical Encounters` (Clinical) — Complete encounter history including diagnoses and procedures; purpose: clinical analytics; certified uses: quality measures, population health, clinical research
- `Claims Register` (Claims & Billing) — All submitted and adjudicated claims; purpose: revenue cycle management; certified uses: denial management, payer contracting, regulatory reporting
- `Lab Results` (Clinical) — Laboratory test orders and results; purpose: clinical decision support; certified uses: clinical analytics, population health, lab quality
- `Compliance Audit Log` (Compliance & Privacy) — PHI access and disclosure audit trail; purpose: HIPAA compliance monitoring; certified uses: breach investigation, compliance audit

#### Data Assets (5)
- `Patient Master Dataset` (Dataset) — Source: Electronic Health Record
- `Clinical Encounters Dataset` (Dataset) — Source: Electronic Health Record
- `Claims Register Dataset` (Dataset) — Source: Claims Management System
- `Lab Results Dataset` (Dataset) — Source: Clinical Data Warehouse
- `Compliance Audit Log Dataset` (Dataset) — Source: Regulatory Reporting System

#### Data Elements (16)
**Patient Master Dataset:** Patient ID (Key, STRING), Medical Record Number (Key, STRING), Date of Birth (Attribute, DATE), Consent Status (Attribute, STRING)
**Clinical Encounters Dataset:** Diagnosis Code ICD-10 (Attribute, STRING), Procedure Code CPT (Attribute, STRING), Encounter Date (Attribute, DATE), Attending Physician (Attribute, STRING)
**Claims Register Dataset:** Claim ID (Key, STRING), Claim Amount (Measure, DECIMAL), National Provider Identifier (Attribute, STRING), Denial Reason Code (Attribute, STRING)
**Lab Results Dataset:** Lab Test Code (Key, STRING), Lab Result Value (Measure, DECIMAL), Lab Result Value (Attribute, STRING)
**Compliance Audit Log Dataset:** PHI Indicator (Attribute, BOOLEAN), Audit Event Type (Attribute, STRING), Breach Indicator (Attribute, BOOLEAN)

#### Delivery Targets (5)
Each collection gets `Secure Clinical Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one: each Dataset links to its corresponding Collection.

#### Terms of Use → Collection links (5)
- Patient Master → HIPAA Compliant Use
- Clinical Encounters → Internal Clinical Use
- Claims Register → Payer Data Sharing Agreement
- Lab Results → Research Data Agreement
- Compliance Audit Log → HIPAA Compliant Use

#### Consumer Access (3) sample records
- Patient Master / care.coordinator@health.org / Clinical Analytics
- Claims Register / billing.analyst@health.org / Revenue Cycle Optimization
- Compliance Audit Log / privacy.officer@health.org / Compliance Reporting

---

### Retail & CPG

Use for retailers, consumer goods, e-commerce, and grocery customers.

#### Categories (4)
- `Customer` — customer identity, loyalty, and segmentation data products
- `Product` — product catalog and pricing data products
- `Supply Chain` — inventory, supplier, and logistics data products
- `Transactions` — POS, e-commerce, and returns data products

#### Cost Centers (4)
- Customer Marketing, Merchandising, Supply Chain Operations, Store Operations

#### Terms of Use (4)
- `Internal Use Only` (Controlled) — Approved internal business use; PII must not be shared externally
- `Partner Analytics Agreement` (Accessible) — Non-PII product and transaction data sharing with approved retail partners
- `Open Product Data` (Accessible) — Non-sensitive product catalog data; freely usable for category intelligence
- `Restricted PII Data` (Restricted) — Customer PII restricted to approved marketing and privacy-compliant workflows

#### Usage Types (4) with colors
- `Customer Analytics` (sky) — Customer behavior, segmentation, and lifetime value analysis
- `Inventory Planning` (mint) — Demand forecasting and stock replenishment analytics
- `Merchandising Analysis` (peach) — Assortment planning and pricing optimization
- `Marketing Personalization` (lemon) — Campaign targeting and loyalty program analytics

#### Delivery Formats (4)
- CSV, JSON, Excel, Parquet

#### Delivery Methods (4)
- HTTPS Download, API Access, S3 Bucket, SFTP

#### Delivery Templates (4)
- `Self-Service Download` (Manual) — System: Customer Data Platform, Location: downloads.retail.internal
- `API Data Feed` (Automatic) — System: API Gateway, Location: api.retail.internal/v1/data
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://retail-data-products/
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.retail.internal/outbound

#### Data Collections (5)
- `Customer Master` (Customer) — Certified customer registry; purpose: single source of truth for customer identity; certified uses: segmentation, personalization, loyalty
- `Product Catalog` (Product) — Authoritative product master; purpose: product information management; certified uses: merchandising, pricing, e-commerce
- `Transaction History` (Transactions) — POS and e-commerce transaction records; purpose: sales analytics; certified uses: revenue reporting, basket analysis, returns
- `Inventory Ledger` (Supply Chain) — Real-time and historical inventory positions; purpose: inventory management; certified uses: replenishment, shrinkage analysis
- `Supplier Register` (Supply Chain) — Approved supplier master; purpose: supplier management; certified uses: procurement, lead time analysis

#### Data Assets (5)
- `Customer Master Dataset` (Dataset) — Source: Customer Data Platform
- `Product Catalog Dataset` (Dataset) — Source: ERP / Inventory System
- `Transaction History Dataset` (Dataset) — Source: Point of Sale System
- `Inventory Ledger Dataset` (Dataset) — Source: ERP / Inventory System
- `Supplier Register Dataset` (Dataset) — Source: ERP / Inventory System

#### Data Elements (16)
**Customer Master Dataset:** Customer ID (Key, STRING), Email Address (Attribute, STRING), Loyalty Tier (Attribute, STRING), Customer Lifetime Value (Measure, DECIMAL)
**Product Catalog Dataset:** SKU (Key, STRING), Product Name (Attribute, STRING), Unit Price (Measure, DECIMAL), UPC Barcode (Attribute, STRING)
**Transaction History Dataset:** Transaction ID (Key, STRING), Transaction Amount (Measure, DECIMAL), Transaction Date (Attribute, DATE), Payment Method (Attribute, STRING)
**Inventory Ledger Dataset:** Stock on Hand (Measure, INTEGER), Reorder Point (Measure, INTEGER), Warehouse Location (Attribute, STRING)
**Supplier Register Dataset:** Supplier ID (Key, STRING), Lead Time (Measure, INTEGER), Approved Vendor Indicator (Attribute, BOOLEAN)

#### Delivery Targets (5)
Each collection gets `Self-Service Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one.

#### Terms of Use → Collection links (5)
- Customer Master → Restricted PII Data
- Product Catalog → Open Product Data
- Transaction History → Internal Use Only
- Inventory Ledger → Internal Use Only
- Supplier Register → Partner Analytics Agreement

#### Consumer Access (3) sample records
- Customer Master / marketing.analyst@retail.com / Customer Analytics
- Product Catalog / buyer@retail.com / Merchandising Analysis
- Inventory Ledger / supply.planner@retail.com / Inventory Planning

---

### Insurance

Use for property & casualty, life, health carriers, reinsurance, and brokerage customers.

#### Categories (4)
- `Policy & Underwriting` — policy and underwriting data products
- `Claims` — claims and fraud data products
- `Customer` — policyholder and agent data products
- `Risk & Compliance` — actuarial and regulatory data products

#### Cost Centers (4)
- Underwriting, Claims Operations, Customer Operations, Actuarial & Risk

#### Terms of Use (4)
- `Internal Actuarial Use` (Controlled) — Restricted to actuarial and risk modeling teams; no external distribution
- `Regulatory Reporting` (Restricted) — For regulatory submission workflows only; must comply with Solvency II and NAIC
- `Reinsurance Data Sharing` (Accessible) — Governs sharing of aggregated claims and reserve data with reinsurance partners
- `Internal Operations` (Controlled) — General internal use for claims and policy operations teams

#### Usage Types (4) with colors
- `Actuarial Modeling` (orchid) — Reserve calculation, pricing, and loss development
- `Claims Analytics` (posy) — Claims frequency, severity, and fraud detection
- `Underwriting Optimization` (sky) — Risk selection and pricing refinement
- `Regulatory Compliance` (mint) — Solvency and statutory filing support

#### Delivery Formats (4)
- CSV, JSON, Excel, Parquet

#### Delivery Methods (4)
- HTTPS Download, S3 Bucket, SFTP, API Access

#### Delivery Templates (4)
- `Self-Service Download` (Manual) — System: Data Warehouse, Location: downloads.insurance.internal
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://insurance-data-products/
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.insurance.internal/outbound
- `API Data Feed` (Automatic) — System: API Gateway, Location: api.insurance.internal/v1/data

#### Data Collections (5)
- `Policyholder Master` (Customer) — Certified policyholder registry; purpose: single source of truth for policyholders; certified uses: KYC, renewal, agent management
- `Policy Register` (Policy & Underwriting) — All active and historical policies; purpose: policy lifecycle management; certified uses: underwriting, premium calculation, renewals
- `Claims Register` (Claims) — All claims intake through settlement; purpose: claims management; certified uses: reserving, fraud detection, subrogation
- `Actuarial Reserve Data` (Risk & Compliance) — Reserve estimates by line of business; purpose: financial reserving; certified uses: IFRS 17, Solvency II, loss development
- `Regulatory Submissions` (Risk & Compliance) — Statutory and regulatory filings data; purpose: regulatory reporting; certified uses: NAIC, state DOI, Solvency II reporting

#### Data Assets (5)
- `Policyholder Master Dataset` (Dataset) — Source: Policy Administration System
- `Policy Register Dataset` (Dataset) — Source: Policy Administration System
- `Claims Register Dataset` (Dataset) — Source: Claims Management System
- `Actuarial Reserve Dataset` (Dataset) — Source: Actuarial Modeling Platform
- `Regulatory Submissions Dataset` (Dataset) — Source: Regulatory Reporting System

#### Data Elements (16)
**Policyholder Master Dataset:** Policyholder ID (Key, STRING), Date of Birth (Attribute, DATE), Risk Profile (Attribute, STRING), KYC Status (Attribute, STRING)
**Policy Register Dataset:** Policy Number (Key, STRING), Premium Amount (Measure, DECIMAL), Coverage Type (Attribute, STRING), Policy Effective Date (Attribute, DATE)
**Claims Register Dataset:** Claim ID (Key, STRING), Claim Amount (Measure, DECIMAL), Loss Type (Attribute, STRING), Fraud Indicator (Attribute, BOOLEAN)
**Actuarial Reserve Dataset:** Loss Ratio (Measure, DECIMAL), Actuarial Reserve Amount (Measure, DECIMAL), Solvency Capital Requirement (Measure, DECIMAL)
**Regulatory Submissions Dataset:** Regulatory Filing Date (Attribute, DATE), Risk Classification (Attribute, STRING), Combined Ratio (Measure, DECIMAL)

#### Delivery Targets (5)
Each collection gets `Self-Service Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one.

#### Terms of Use → Collection links (5)
- Policyholder Master → Internal Operations
- Policy Register → Internal Actuarial Use
- Claims Register → Internal Operations
- Actuarial Reserve Data → Regulatory Reporting
- Regulatory Submissions → Regulatory Reporting

#### Consumer Access (3) sample records
- Actuarial Reserve Data / actuary@insurance.com / Actuarial Modeling
- Claims Register / claims.analyst@insurance.com / Claims Analytics
- Regulatory Submissions / compliance@insurance.com / Regulatory Compliance

---

### Public Sector & Government

Use for federal, state, and local agencies, defense, and public utilities customers.

#### Categories (4)
- `Citizen Services` — citizen identity and benefits data products
- `Program & Operations` — grants, contracts, and program data products
- `Financial Management` — appropriations and expenditure data products
- `Compliance & Reporting` — regulatory filing and audit data products

#### Cost Centers (4)
- Citizen Services Division, Program Operations, Financial Management Office, Compliance & Oversight

#### Terms of Use (4)
- `Government Internal Use` (Controlled) — Authorized government staff only; subject to Privacy Act and agency data policies
- `FOIA Public Data` (Accessible) — Non-sensitive public data released per FOIA obligations; freely accessible
- `Restricted PII Data` (Restricted) — Contains PII; access restricted to need-to-know basis per Privacy Act
- `Inter-Agency Sharing Agreement` (Controlled) — Governs data sharing between federal agencies under MOU; must comply with FISMA

#### Usage Types (4) with colors
- `Policy Analysis` (sky) — Legislative and program policy impact analysis
- `Program Evaluation` (mint) — Grant and contract performance monitoring
- `Financial Audit` (posy) — Appropriation and expenditure audit support
- `Citizen Services Delivery` (lemon) — Benefits eligibility and case management support

#### Delivery Formats (4)
- CSV, JSON, Excel, XML

#### Delivery Methods (4)
- HTTPS Download, SFTP, API Access, S3 Bucket

#### Delivery Templates (4)
- `Secure Government Download` (Manual) — System: Data Analytics Platform, Location: downloads.agency.gov
- `Inter-Agency File Transfer` (Automatic) — System: SFTP Server, Location: sftp.agency.gov/interagency
- `API Data Feed` (Automatic) — System: API Gateway, Location: api.agency.gov/v1/data
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://agency-data-products/

#### Data Collections (5)
- `Citizen Registry` (Citizen Services) — Certified citizen identity and demographics; purpose: benefits eligibility and case management; certified uses: benefits administration, identity verification, program enrollment
- `Benefits Register` (Citizen Services) — Active and historical benefits records; purpose: program administration; certified uses: eligibility determination, payment processing, audit
- `General Ledger` (Financial Management) — Appropriations, obligations, and expenditures; purpose: financial management; certified uses: audit, budget reporting, OMB reporting
- `Grants & Contracts Register` (Program & Operations) — Awards and contract performance data; purpose: program management; certified uses: SAM.gov reporting, OMB reporting, program evaluation
- `Compliance Submissions` (Compliance & Reporting) — Regulatory and oversight filings; purpose: compliance reporting; certified uses: FISMA, OMB A-123, Inspector General reporting

#### Data Assets (5)
- `Citizen Registry Dataset` (Dataset) — Source: Case Management System
- `Benefits Register Dataset` (Dataset) — Source: Case Management System
- `General Ledger Dataset` (Dataset) — Source: Financial Management System
- `Grants Register Dataset` (Dataset) — Source: Grants Management System
- `Compliance Submissions Dataset` (Dataset) — Source: Data Analytics Platform

#### Data Elements (16)
**Citizen Registry Dataset:** Citizen ID (Key, STRING), Social Security Number (Attribute, STRING), Benefits Eligibility Status (Attribute, STRING), Program Enrollment Date (Attribute, DATE)
**Benefits Register Dataset:** Case ID (Key, STRING), Benefit Amount (Measure, DECIMAL), Case Worker ID (Attribute, STRING)
**General Ledger Dataset:** Appropriation Code (Key, STRING), Obligation Amount (Measure, DECIMAL), Expenditure Amount (Measure, DECIMAL), Fiscal Year (Attribute, STRING)
**Grants Register Dataset:** Grant ID (Key, STRING), Award Amount (Measure, DECIMAL), Vendor ID (Attribute, STRING)
**Compliance Submissions Dataset:** Compliance Status (Attribute, STRING), PII Indicator (Attribute, BOOLEAN), Report Submission Date (Attribute, DATE)

#### Delivery Targets (5)
Each collection gets `Secure Government Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one.

#### Terms of Use → Collection links (5)
- Citizen Registry → Restricted PII Data
- Benefits Register → Government Internal Use
- General Ledger → Government Internal Use
- Grants & Contracts Register → FOIA Public Data
- Compliance Submissions → Inter-Agency Sharing Agreement

#### Consumer Access (3) sample records
- Citizen Registry / case.worker@agency.gov / Citizen Services Delivery
- General Ledger / budget.analyst@agency.gov / Financial Audit
- Grants & Contracts Register / program.manager@agency.gov / Program Evaluation

---

### Oil & Gas

Use for upstream E&P, midstream pipeline, downstream refining, oilfield services, and integrated energy companies.

#### Categories (4)
- `Assets & Operations` — well, facility, and production data products
- `HSE & Compliance` — health, safety, environment, and permit data products
- `Supply Chain & Procurement` — vendor, materials, and contract data products
- `Finance & Commercial` — production accounting and joint venture data products

#### Cost Centers (4)
- Operations Engineering, HSE Department, Supply Chain & Procurement, Finance & JV Accounting

#### Terms of Use (4)
- `Internal Operations Use` (Controlled) — Authorized operations and engineering staff only; no external distribution
- `Regulatory Reporting` (Restricted) — Restricted to BSEE, EPA, and PHMSA regulatory reporting workflows
- `JV Partner Sharing Agreement` (Accessible) — Governs sharing of production and financial data with joint venture partners
- `Environmental Disclosure` (Accessible) — Publicly disclosed environmental release and permit data per regulatory requirements

#### Usage Types (4) with colors
- `Production Analytics` (sky) — Well performance, decline curves, and production optimization
- `HSE Reporting` (posy) — Incident tracking, permit compliance, and environmental monitoring
- `Asset Optimization` (mint) — Equipment reliability, maintenance planning, and OPEX analysis
- `JV Reporting` (orchid) — Joint venture accounting, working interest, and partner reporting

#### Delivery Formats (4)
- CSV, JSON, Parquet, Excel

#### Delivery Methods (4)
- HTTPS Download, S3 Bucket, SFTP, API Access

#### Delivery Templates (4)
- `Self-Service Download` (Manual) — System: Production Accounting System, Location: downloads.energy.internal
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://energy-data-products/
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.energy.internal/outbound
- `API Data Feed` (Automatic) — System: SCADA API Gateway, Location: api.energy.internal/v1/data

#### Data Collections (5)
- `Well Master` (Assets & Operations) — Certified well registry with location and status; purpose: well lifecycle management; certified uses: production reporting, regulatory filing, asset optimization
- `Production Volume Register` (Assets & Operations) — Daily and monthly production volumes by well; purpose: production accounting; certified uses: royalty calculation, revenue reporting, BSEE reporting
- `HSE Incident Log` (HSE & Compliance) — All safety incidents, near misses, and environmental events; purpose: HSE management; certified uses: OSHA reporting, BSEE reporting, incident investigation
- `Vendor & Contract Register` (Supply Chain & Procurement) — Approved vendor master and active contracts; purpose: procurement management; certified uses: vendor qualification, contract compliance, spend analysis
- `Joint Venture Ledger` (Finance & Commercial) — JV partner interests and financial settlements; purpose: JV accounting; certified uses: partner reporting, working interest billing, SEC disclosures

#### Data Assets (5)
- `Well Master Dataset` (Dataset) — Source: Enterprise Asset Management System
- `Production Volume Dataset` (Dataset) — Source: SCADA / Historian
- `HSE Incident Dataset` (Dataset) — Source: HSE Management System
- `Vendor Register Dataset` (Dataset) — Source: Enterprise Asset Management System
- `JV Ledger Dataset` (Dataset) — Source: Production Accounting System

#### Data Elements (16)
**Well Master Dataset:** Well ID (Key, STRING), API Well Number (Key, STRING), Field Name (Attribute, STRING), Production Zone (Attribute, STRING)
**Production Volume Dataset:** Daily Oil Production BOE (Measure, DECIMAL), Water Cut Percentage (Measure, DECIMAL), Run Ticket Number (Key, STRING)
**HSE Incident Dataset:** Incident ID (Key, STRING), Incident Severity (Attribute, STRING), Lost Time Injury (Attribute, BOOLEAN), Spill Indicator (Attribute, BOOLEAN)
**Vendor Register Dataset:** Vendor ID (Key, STRING), Contract Value (Measure, DECIMAL), Approved Vendor Indicator (Attribute, BOOLEAN)
**JV Ledger Dataset:** AFE Number (Key, STRING), Working Interest Percentage (Measure, DECIMAL), Royalty Rate (Measure, DECIMAL), Net Revenue Interest (Measure, DECIMAL)

#### Delivery Targets (5)
Each collection gets `Self-Service Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one.

#### Terms of Use → Collection links (5)
- Well Master → Internal Operations Use
- Production Volume Register → JV Partner Sharing Agreement
- HSE Incident Log → Regulatory Reporting
- Vendor & Contract Register → Internal Operations Use
- Joint Venture Ledger → JV Partner Sharing Agreement

#### Consumer Access (3) sample records
- Production Volume Register / production.engineer@energy.com / Production Analytics
- HSE Incident Log / hse.manager@energy.com / HSE Reporting
- Joint Venture Ledger / jv.accountant@energy.com / JV Reporting

---

### Manufacturing

Use for discrete and process manufacturing, automotive, aerospace & defense, and consumer goods production customers.

#### Categories (4)
- `Product & Engineering` — product master, BOM, and engineering data products
- `Production & Operations` — work order, shop floor, and OEE data products
- `Quality` — quality control, non-conformance, and certification data products
- `Supply Chain` — supplier, material, and inventory data products

#### Cost Centers (4)
- Engineering, Manufacturing Operations, Quality Assurance, Supply Chain Management

#### Terms of Use (4)
- `Internal Manufacturing Use` (Controlled) — Authorized manufacturing and engineering staff only; no external distribution
- `Supplier Quality Sharing` (Accessible) — Non-confidential quality and specification data shared with approved suppliers
- `Regulatory Compliance` (Restricted) — Restricted to ITAR, RoHS, and ISO compliance reporting workflows
- `Internal Operations` (Controlled) — General internal use for production and supply chain operations teams

#### Usage Types (4) with colors
- `Production Planning` (sky) — Capacity planning, scheduling, and throughput optimization
- `Quality Analytics` (posy) — Defect analysis, yield tracking, and SPC monitoring
- `Supply Chain Optimization` (mint) — Supplier performance, lead time, and inventory analytics
- `Engineering Analysis` (orchid) — BOM accuracy, ECO impact, and design analytics

#### Delivery Formats (4)
- CSV, JSON, Excel, Parquet

#### Delivery Methods (4)
- HTTPS Download, S3 Bucket, API Access, SFTP

#### Delivery Templates (4)
- `Self-Service Download` (Manual) — System: ERP / MES, Location: downloads.manufacturing.internal
- `API Data Feed` (Automatic) — System: API Gateway, Location: api.manufacturing.internal/v1/data
- `Cloud Storage Export` (Automatic) — System: S3, Location: s3://manufacturing-data-products/
- `Secure File Transfer` (Automatic) — System: SFTP Server, Location: sftp.manufacturing.internal/outbound

#### Data Collections (5)
- `Product Master` (Product & Engineering) — Authoritative product and part definitions; purpose: product information management; certified uses: BOM management, costing, ITAR compliance
- `Bill of Materials` (Product & Engineering) — Structured BOM for all active products; purpose: manufacturing planning; certified uses: MRP, costing, ECO analysis
- `Work Order Register` (Production & Operations) — All work orders and production run history; purpose: production tracking; certified uses: OEE analysis, capacity planning, cost reporting
- `Non-Conformance Register` (Quality) — All NCRs, defects, and corrective actions; purpose: quality management; certified uses: SPC, supplier quality, ISO 9001 reporting
- `Supplier & Material Master` (Supply Chain) — Approved suppliers and raw material specifications; purpose: procurement and supply chain management; certified uses: vendor qualification, MRP, spend analysis

#### Data Assets (5)
- `Product Master Dataset` (Dataset) — Source: Product Lifecycle Management System
- `Bill of Materials Dataset` (Dataset) — Source: ERP / Manufacturing Execution System
- `Work Order Dataset` (Dataset) — Source: ERP / Manufacturing Execution System
- `NCR Dataset` (Dataset) — Source: Quality Management System
- `Supplier Master Dataset` (Dataset) — Source: ERP / Manufacturing Execution System

#### Data Elements (16)
**Product Master Dataset:** Part Number (Key, STRING), Part Description (Attribute, STRING), Revision Level (Attribute, STRING), Product Classification Code (Attribute, STRING)
**Bill of Materials Dataset:** Bill of Materials BOM (Attribute, STRING), Engineering Change Order Number (Attribute, STRING), Unit of Measure (Attribute, STRING)
**Work Order Dataset:** Work Order Number (Key, STRING), Overall Equipment Effectiveness OEE (Measure, DECIMAL), Actual Cycle Time (Measure, DECIMAL), Shift Code (Attribute, STRING)
**NCR Dataset:** NCR Number (Key, STRING), Defect Code (Attribute, STRING), First Pass Yield (Measure, DECIMAL), Corrective Action Status (Attribute, STRING)
**Supplier Master Dataset:** Supplier ID (Key, STRING), Lead Time Days (Measure, INTEGER), Safety Stock Level (Measure, INTEGER), Approved Vendor Indicator (Attribute, BOOLEAN)

#### Delivery Targets (5)
Each collection gets `Self-Service Download` template, CSV format, HTTPS Download method.

#### Data Asset → Collection links (5)
One-to-one.

#### Terms of Use → Collection links (5)
- Product Master → Regulatory Compliance
- Bill of Materials → Internal Manufacturing Use
- Work Order Register → Internal Operations
- Non-Conformance Register → Supplier Quality Sharing
- Supplier & Material Master → Internal Manufacturing Use

#### Consumer Access (3) sample records
- Work Order Register / production.planner@manufacturing.com / Production Planning
- Non-Conformance Register / quality.engineer@manufacturing.com / Quality Analytics
- Supplier & Material Master / supply.chain.analyst@manufacturing.com / Supply Chain Optimization

---

## Step 4 — Import order and dependencies

```
01_Category.xlsx                    ← no dependencies
02_Cost_Center.xlsx                 ← no dependencies
03_Terms_of_Use.xlsx                ← no dependencies
04_Usage_Type.xlsx                  ← no dependencies
05_Delivery_Format.xlsx             ← no dependencies
06_Delivery_Method.xlsx             ← no dependencies
07_Delivery_Template.xlsx           ← depends on 05, 06
08_Data_Asset.xlsx                  ← no dependencies
09_Data_Collection.xlsx             ← depends on 01
10_Data_Element.xlsx                ← depends on 08
11_Delivery_Target.xlsx             ← depends on 07, 09
12_Data_Asset_Collection.xlsx       ← depends on 08, 09
13_Terms_Collection.xlsx            ← depends on 03, 09
14_Consumer_Access.xlsx             ← depends on 09, 11
```

**Import method:** IDMC UI → Data Marketplace → Admin → Import → Upload file → Import one file at a time.

**Import 01–06 first** — these are configuration/reference objects with no dependencies and must exist before any other object references them.

---

## Step 5 — Confirmation checklist

After all imports, verify in the Data Marketplace UI:

- [ ] Categories visible under Browse (4 total)
- [ ] Data Collections visible under Browse — grouped by Category (5 total)
- [ ] Data Assets visible under each Data Collection (5 total)
- [ ] Data Elements visible on each Data Asset (16 total)
- [ ] Delivery Templates visible in Admin (4 total)
- [ ] Delivery Targets configured on each Data Collection (5 total)
- [ ] Terms of Use linked to each Data Collection (5 total)
- [ ] Consumer Access records visible in Admin (3 total)
- [ ] Usage Types visible in Admin with correct colors (4 total)

---

## Common errors and fixes

| Error | Fix |
|-------|-----|
| Category not found on Data Collection import | Import Category (01) before Data Collection (09) |
| Delivery Template not found on Delivery Target | Import Delivery Template (07) before Delivery Target (11) |
| Delivery Format/Method not resolved | Names in Delivery Template must exactly match Format Name / Method Name from files 05 and 06 |
| Data Asset not found on Data Element import | Import Data Asset (08) before Data Element (10) |
| Consumer Access fails | Delivery Target must exist before Consumer Access; import 11 before 14 |
| Terms of Use link fails | Terms of Use Name must exactly match the Name field from file 03 |
| Blank sheet rejection | Do not import the Predefined_Values sheet — only import the primary named sheet |
| "Reference ID configured by administrator" warning | Leave Reference ID column values blank — keep the header but do not populate values; Marketplace assigns them |

---

## Sharing this skill

This skill is a Markdown file at `~/.claude/commands/marketplace-setup.md`.

**To share with a colleague:**
1. Send them the file — they save it to `~/.claude/commands/marketplace-setup.md`
2. They type `/marketplace-setup` in any Claude Code session to invoke it

**To publish to a team:**
- Add to a shared repo under `.claude/commands/marketplace-setup.md`
- Anyone who clones the repo and opens Claude Code in that directory gets the skill automatically
