-- ============================================================
-- FCB Financial Services Demo — Snowflake Setup
-- ============================================================
-- Purpose : Create all tables, views, and lineage structures
--           needed for the First Capital Bank CDGC demo.
--           Run this in Snowflake (or DBeaver) before MCC scanning.
--
-- Vertical : Financial Services (FSI)
--
-- !! BEFORE RUNNING — update the two variables below !!
--
--   YOUR_DATABASE   The Snowflake database where schemas will be created.
--                   The database must already exist.
--                   Example: PROD_DB, DEMO_DB, SANDBOX
--
--   YOUR_WAREHOUSE  The Snowflake warehouse to use for this session.
--                   Example: COMPUTE_WH, DEMO_WH, DEV_WH
--
-- Find/replace both values in this file before executing.
-- All other names (FCB_CORE, TRAINING_DATA, MODEL_REGISTRY) can
-- be left as-is or changed to match your naming convention.
--
-- Schemas created:
--   FCB_CORE         4 core financial tables + 3 reporting views
--   TRAINING_DATA    4 ML feature tables
--   MODEL_REGISTRY   7 AI model I/O tables + 7 lineage views
--
-- Run order:
--   1. Setup (USE + CREATE SCHEMA)
--   2. FCB_CORE tables
--   3. TRAINING_DATA tables
--   4. MODEL_REGISTRY tables
--   5. Lineage views (FCB_CORE + MODEL_REGISTRY)
--   6. Verification queries
--
-- After running:
--   In MCC → create a Snowflake catalog source, then:
--   - Filter: YOUR_DATABASE.FCB_CORE
--             YOUR_DATABASE.TRAINING_DATA
--             YOUR_DATABASE.MODEL_REGISTRY
--   - Enable: Metadata Extraction, Data Profiling, Data Quality,
--             Data Classification, Glossary Association, Lineage Discovery
--   - Run scan
-- ============================================================


-- ── 1. SETUP ──────────────────────────────────────────────────
-- !! Replace YOUR_WAREHOUSE and YOUR_DATABASE before running !!

USE WAREHOUSE YOUR_WAREHOUSE;
USE DATABASE YOUR_DATABASE;

CREATE SCHEMA IF NOT EXISTS YOUR_DATABASE.FCB_CORE
  COMMENT = 'Core financial services tables for FCB CDGC demo. Scanned by MCC.';

CREATE SCHEMA IF NOT EXISTS YOUR_DATABASE.TRAINING_DATA
  COMMENT = 'Feature datasets used to train FCB AI models. Scanned by MCC for DQ monitoring.';

CREATE SCHEMA IF NOT EXISTS YOUR_DATABASE.MODEL_REGISTRY
  COMMENT = 'AI model input/output contracts. Simulates MLflow/Databricks model schema for MCC lineage.';


-- ============================================================
-- FCB_CORE — Core Financial Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS YOUR_DATABASE.FCB_CORE.CUSTOMER_MASTER (
    CUSTOMER_ID     VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique customer identifier',
    FIRST_NAME      VARCHAR(50)                        COMMENT 'Customer first name',
    LAST_NAME       VARCHAR(50)                        COMMENT 'Customer last name',
    DATE_OF_BIRTH   DATE                               COMMENT 'Customer date of birth',
    SSN             VARCHAR(11)                        COMMENT 'Social Security Number — PII sensitive',
    EMAIL           VARCHAR(100)                       COMMENT 'Primary email address',
    PHONE_NUMBER    VARCHAR(20)                        COMMENT 'Primary phone number',
    ADDRESS_LINE1   VARCHAR(100)                       COMMENT 'Street address line 1',
    CITY            VARCHAR(50)                        COMMENT 'City of residence',
    STATE           VARCHAR(2)                         COMMENT 'State abbreviation',
    ZIP_CODE        VARCHAR(10)                        COMMENT 'Postal zip code',
    ACCOUNT_STATUS  VARCHAR(20)                        COMMENT 'Current account status: ACTIVE, INACTIVE, SUSPENDED, CLOSED',
    CUSTOMER_SINCE  DATE                               COMMENT 'Date customer relationship was established',
    CREDIT_SCORE    NUMBER(4,0)                        COMMENT 'FICO credit score 300-850',
    ANNUAL_INCOME   NUMBER(12,2)                       COMMENT 'Declared annual income in USD',
    RISK_TIER       VARCHAR(20)                        COMMENT 'Internal risk classification: LOW, MEDIUM, HIGH, VERY_HIGH',
    ACCOUNT_TYPE    VARCHAR(30)                        COMMENT 'CHECKING / SAVINGS / MONEY_MARKET / CD',
    BRANCH_CODE     VARCHAR(10)                        COMMENT 'Home branch identifier'
);

CREATE TABLE IF NOT EXISTS YOUR_DATABASE.FCB_CORE.TRANSACTION_LEDGER (
    TRANSACTION_ID    VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique transaction identifier',
    ACCOUNT_ID        VARCHAR(20)                        COMMENT 'Associated account identifier',
    CUSTOMER_ID       VARCHAR(20)                        COMMENT 'Customer identifier — foreign key to CUSTOMER_MASTER',
    TRANSACTION_DATE  TIMESTAMP                          COMMENT 'Date and time transaction was initiated',
    TRANSACTION_TYPE  VARCHAR(20)                        COMMENT 'Transaction type: DEBIT, CREDIT, TRANSFER, FEE',
    AMOUNT            NUMBER(12,2)                       COMMENT 'Transaction amount in native currency',
    CURRENCY          VARCHAR(3)                         COMMENT 'ISO 4217 currency code',
    MERCHANT_NAME     VARCHAR(100)                       COMMENT 'Name of merchant or payee',
    MERCHANT_CATEGORY VARCHAR(50)                        COMMENT 'Merchant category classification',
    BALANCE_AFTER     NUMBER(12,2)                       COMMENT 'Account balance after transaction',
    CHANNEL           VARCHAR(20)                        COMMENT 'Transaction channel: ONLINE, BRANCH, ATM, MOBILE',
    STATUS            VARCHAR(20)                        COMMENT 'Transaction status: COMPLETED, PENDING, FAILED, REVERSED',
    REFERENCE_NUMBER  VARCHAR(25)                        COMMENT 'External reference or confirmation number'
);

CREATE TABLE IF NOT EXISTS YOUR_DATABASE.FCB_CORE.GL_ENTRY_REGISTER (
    ENTRY_ID       VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique general ledger entry identifier',
    JOURNAL_ID     VARCHAR(20)                        COMMENT 'Journal batch identifier',
    ENTRY_DATE     DATE                               COMMENT 'Date of the accounting entry',
    POSTING_DATE   DATE                               COMMENT 'Date entry was posted to the ledger',
    ACCOUNT_CODE   VARCHAR(10)                        COMMENT 'Chart of accounts code',
    ACCOUNT_NAME   VARCHAR(100)                       COMMENT 'Account name from chart of accounts',
    DEBIT_AMOUNT   NUMBER(15,2)                       COMMENT 'Debit amount in USD',
    CREDIT_AMOUNT  NUMBER(15,2)                       COMMENT 'Credit amount in USD',
    NET_AMOUNT     NUMBER(15,2)                       COMMENT 'Net amount: debit minus credit',
    COST_CENTER    VARCHAR(50)                        COMMENT 'Business unit cost center code',
    LEGAL_ENTITY   VARCHAR(100)                       COMMENT 'Legal entity associated with the entry',
    CURRENCY       VARCHAR(3)                         COMMENT 'ISO 4217 currency code',
    FISCAL_PERIOD  VARCHAR(5)                         COMMENT 'Fiscal period code e.g. P01-P12',
    FISCAL_YEAR    NUMBER(4,0)                        COMMENT 'Fiscal year of the entry',
    CREATED_BY     VARCHAR(100)                       COMMENT 'User who created the entry',
    APPROVED_BY    VARCHAR(100)                       COMMENT 'User who approved the entry'
);

CREATE TABLE IF NOT EXISTS YOUR_DATABASE.FCB_CORE.RISK_EXPOSURE_DAILY (
    RISK_ID                  VARCHAR(20)  NOT NULL PRIMARY KEY COMMENT 'Unique risk assessment identifier',
    CUSTOMER_ID              VARCHAR(20)                       COMMENT 'Customer identifier — foreign key to CUSTOMER_MASTER',
    ASSESSMENT_DATE          DATE                              COMMENT 'Date of risk assessment',
    RISK_CATEGORY            VARCHAR(20)                       COMMENT 'Risk type: CREDIT, MARKET, OPERATIONAL, LIQUIDITY, REGULATORY',
    EXPOSURE_AMOUNT          NUMBER(15,2)                      COMMENT 'Total exposure amount in USD',
    PROBABILITY_OF_DEFAULT   FLOAT                             COMMENT 'Estimated probability of default (0.0 to 1.0)',
    LOSS_GIVEN_DEFAULT       FLOAT                             COMMENT 'Estimated loss given default as a ratio (0.0 to 1.0)',
    EXPECTED_LOSS            NUMBER(15,2)                      COMMENT 'Expected loss = exposure x PD x LGD',
    RISK_RATING              VARCHAR(5)                        COMMENT 'Internal risk rating: AAA to CCC',
    COLLATERAL_VALUE         NUMBER(15,2)                      COMMENT 'Value of collateral securing the exposure',
    REGULATORY_CAPITAL       NUMBER(15,2)                      COMMENT 'Required regulatory capital allocation',
    BASEL_CLASS              VARCHAR(30)                       COMMENT 'Basel III asset class classification'
);


-- ============================================================
-- TRAINING_DATA — ML Feature Tables
-- ============================================================

CREATE OR REPLACE TABLE YOUR_DATABASE.TRAINING_DATA.TRANSACTION_FEATURES (
    TRANSACTION_ID          VARCHAR(36)     NOT NULL    COMMENT 'Unique transaction identifier (UUID)',
    ACCOUNT_ID              VARCHAR(20)     NOT NULL    COMMENT 'Customer account identifier',
    TRANSACTION_AMOUNT      FLOAT                       COMMENT 'Transaction value in USD — NULL indicates missing amount (DQ issue)',
    MERCHANT_CATEGORY_CODE  VARCHAR(4)                  COMMENT 'ISO 18245 merchant category code',
    MERCHANT_NAME           VARCHAR(100)                COMMENT 'Merchant display name',
    TRANSACTION_TIMESTAMP   TIMESTAMP_NTZ               COMMENT 'UTC timestamp of transaction',
    DEVICE_FINGERPRINT      VARCHAR(64)                 COMMENT 'Hashed device identifier',
    CHANNEL                 VARCHAR(20)                 COMMENT 'ATM / ONLINE / POS / MOBILE',
    GEOLOCATION_COUNTRY     VARCHAR(3)                  COMMENT 'ISO 3166-1 alpha-3 country code',
    VELOCITY_1H             INTEGER                     COMMENT 'Transaction count last 1 hour',
    VELOCITY_24H            INTEGER                     COMMENT 'Transaction count last 24 hours',
    AVG_TRANSACTION_30D     FLOAT                       COMMENT 'Rolling 30-day average transaction amount',
    IS_INTERNATIONAL        BOOLEAN                     COMMENT 'True if cross-border transaction',
    FRAUD_LABEL             INTEGER                     COMMENT 'Ground truth: 1=fraud, 0=legitimate',
    DATA_PARTITION          VARCHAR(10)                 COMMENT 'TRAIN / VALIDATE / TEST',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training set'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.TRAINING_DATA.CUSTOMER_360_FEATURES (
    CUSTOMER_ID             VARCHAR(20)     NOT NULL    COMMENT 'Unique customer identifier',
    AGE                     INTEGER                     COMMENT 'Customer age in years',
    ANNUAL_INCOME           FLOAT                       COMMENT 'Declared annual income in USD',
    EMPLOYMENT_STATUS       VARCHAR(30)                 COMMENT 'EMPLOYED / SELF_EMPLOYED / UNEMPLOYED / RETIRED',
    CREDIT_SCORE            INTEGER                     COMMENT 'Bureau credit score 300-850 — values outside range are DQ issues',
    DEBT_TO_INCOME_RATIO    FLOAT                       COMMENT 'Total monthly debt / gross monthly income',
    EXISTING_LOAN_COUNT     INTEGER                     COMMENT 'Number of active loans',
    MONTHS_CUSTOMER         INTEGER                     COMMENT 'Tenure as customer in months',
    KYC_DOCUMENT_TYPE       VARCHAR(30)                 COMMENT 'PASSPORT / DRIVERS_LICENSE / NATIONAL_ID',
    KYC_DOCUMENT_COUNTRY    VARCHAR(3)                  COMMENT 'ISO 3166-1 alpha-3 issuing country',
    KYC_VERIFIED_DATE       DATE                        COMMENT 'Date KYC verification completed',
    KYC_EXPIRY_DATE         DATE                        COMMENT 'Document expiry date',
    PEP_FLAG                BOOLEAN                     COMMENT 'Politically Exposed Person indicator',
    SANCTIONS_FLAG          BOOLEAN                     COMMENT 'OFAC/EU sanctions list match',
    DEFAULT_LABEL           INTEGER                     COMMENT 'Ground truth: 1=defaulted within 12mo, 0=no default',
    DATA_PARTITION          VARCHAR(10)                 COMMENT 'TRAIN / VALIDATE / TEST',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training set'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.TRAINING_DATA.RISK_EXPOSURE_FEATURES (
    EXPOSURE_ID             VARCHAR(36)     NOT NULL    COMMENT 'Unique risk exposure record identifier',
    COUNTERPARTY_ID         VARCHAR(20)     NOT NULL    COMMENT 'Counterparty or customer identifier',
    ASSET_CLASS             VARCHAR(30)                 COMMENT 'MORTGAGE / AUTO / COMMERCIAL / CONSUMER / SECURITIES',
    OUTSTANDING_BALANCE     FLOAT                       COMMENT 'Current outstanding exposure in USD',
    ORIGINAL_BALANCE        FLOAT                       COMMENT 'Original principal amount in USD',
    MATURITY_DATE           DATE                        COMMENT 'Loan or instrument maturity date',
    INTEREST_RATE           FLOAT                       COMMENT 'Annual interest rate as decimal — values > 1.0 are DQ issues',
    COLLATERAL_VALUE        FLOAT                       COMMENT 'Fair market value of collateral in USD',
    LTV_RATIO               FLOAT                       COMMENT 'Loan-to-value ratio — values > 2.0 flagged as anomalous',
    DAYS_PAST_DUE           INTEGER                     COMMENT 'Days since last payment was due',
    INTERNAL_RATING         VARCHAR(5)                  COMMENT 'Internal risk rating AAA to CCC',
    STRESS_SCENARIO         VARCHAR(20)                 COMMENT 'BASELINE / ADVERSE / SEVERELY_ADVERSE',
    PROJECTED_LOSS          FLOAT                       COMMENT 'Model projected loss under scenario in USD',
    REGULATORY_CAPITAL      FLOAT                       COMMENT 'Required regulatory capital allocation in USD',
    RECORD_QUARTER          VARCHAR(7)                  COMMENT 'Reporting quarter e.g. 2025-Q4',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training set'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.TRAINING_DATA.REGULATORY_SUBMISSIONS_FEATURES (
    SUBMISSION_ID           VARCHAR(36)     NOT NULL    COMMENT 'Unique submission identifier',
    FILING_TYPE             VARCHAR(20)                 COMMENT 'CCAR / FR-Y9C / CALL_REPORT / SAR / CTR',
    REGULATORY_BODY         VARCHAR(20)                 COMMENT 'FED / OCC / FDIC / FINRA / CFPB',
    REPORTING_PERIOD        VARCHAR(7)                  COMMENT 'Reporting period e.g. 2025-Q4',
    SUBMISSION_DATE         DATE                        COMMENT 'Date filed with regulator',
    DEADLINE_DATE           DATE                        COMMENT 'Regulatory deadline',
    FILED_ON_TIME           BOOLEAN                     COMMENT 'True if submitted before deadline',
    RESTATEMENT_COUNT       INTEGER                     COMMENT 'Number of restatements filed',
    ERROR_COUNT             INTEGER                     COMMENT 'Validation errors at submission time',
    COMPLETENESS_SCORE      FLOAT                       COMMENT 'Field completeness 0.0-1.0 — values outside range are DQ issues',
    ACCEPTANCE_STATUS       VARCHAR(20)                 COMMENT 'ACCEPTED / REJECTED / PENDING_REVIEW',
    REJECTION_REASON        VARCHAR(500)                COMMENT 'Regulatory rejection reason if applicable',
    VALIDATION_LABEL        INTEGER                     COMMENT 'Ground truth: 1=clean filing, 0=required correction',
    DATA_PARTITION          VARCHAR(10)                 COMMENT 'TRAIN / VALIDATE / TEST',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training set'
);


-- ============================================================
-- MODEL_REGISTRY — AI Model I/O Tables
-- ============================================================

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.FRAUD_DETECTOR_IO (
    TRANSACTION_AMOUNT      FLOAT           COMMENT '[INPUT] Transaction value in USD',
    MERCHANT_CATEGORY_CODE  VARCHAR(4)      COMMENT '[INPUT] Merchant category for pattern matching',
    DEVICE_FINGERPRINT      VARCHAR(64)     COMMENT '[INPUT] Device identifier for account takeover detection',
    VELOCITY_1H             INTEGER         COMMENT '[INPUT] Recent transaction velocity',
    VELOCITY_24H            INTEGER         COMMENT '[INPUT] Daily transaction velocity',
    AVG_TRANSACTION_30D     FLOAT           COMMENT '[INPUT] Baseline spending behavior',
    IS_INTERNATIONAL        BOOLEAN         COMMENT '[INPUT] Cross-border transaction flag',
    GEOLOCATION_COUNTRY     VARCHAR(3)      COMMENT '[INPUT] Transaction origin country',
    FRAUD_PROBABILITY       FLOAT           COMMENT '[OUTPUT] Fraud probability score 0.0-1.0',
    DECISION                VARCHAR(20)     COMMENT '[OUTPUT] APPROVE / STEP_UP / DECLINE',
    CONFIDENCE_SCORE        FLOAT           COMMENT '[OUTPUT] Model confidence 0.0-1.0',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] When inference was executed'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.BEHAVIORAL_ANOMALY_IO (
    ACCOUNT_ID              VARCHAR(20)     COMMENT '[INPUT] Account being assessed',
    VELOCITY_24H            INTEGER         COMMENT '[INPUT] Transaction count last 24 hours',
    AVG_TRANSACTION_30D     FLOAT           COMMENT '[INPUT] Baseline spending pattern',
    CHANNEL                 VARCHAR(20)     COMMENT '[INPUT] Transaction channel context',
    DEVICE_FINGERPRINT      VARCHAR(64)     COMMENT '[INPUT] Device consistency indicator',
    TRANSACTION_AMOUNT      FLOAT           COMMENT '[INPUT] Current transaction size',
    GEOLOCATION_COUNTRY     VARCHAR(3)      COMMENT '[INPUT] Geographic anomaly detection',
    ANOMALY_SCORE           FLOAT           COMMENT '[OUTPUT] Behavioral deviation score 0.0-1.0',
    ANOMALY_TYPE            VARCHAR(50)     COMMENT '[OUTPUT] ACCOUNT_TAKEOVER / VELOCITY / GEO_ANOMALY / NONE',
    RISK_TIER               VARCHAR(10)     COMMENT '[OUTPUT] LOW / MEDIUM / HIGH / CRITICAL',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.AML_ANOMALY_IO (
    ACCOUNT_ID              VARCHAR(20)     COMMENT '[INPUT] Account under review',
    TRANSACTION_AMOUNT      FLOAT           COMMENT '[INPUT] Transaction value',
    MERCHANT_CATEGORY_CODE  VARCHAR(4)      COMMENT '[INPUT] Transaction type context',
    VELOCITY_24H            INTEGER         COMMENT '[INPUT] Transaction frequency',
    IS_INTERNATIONAL        BOOLEAN         COMMENT '[INPUT] Cross-border flag',
    GEOLOCATION_COUNTRY     VARCHAR(3)      COMMENT '[INPUT] Transaction country',
    SANCTIONS_FLAG          BOOLEAN         COMMENT '[INPUT] OFAC/EU sanctions pre-screen',
    PEP_FLAG                BOOLEAN         COMMENT '[INPUT] Politically Exposed Person flag',
    SAR_PROBABILITY         FLOAT           COMMENT '[OUTPUT] Suspicious Activity Report probability 0.0-1.0',
    AML_RISK_SCORE          FLOAT           COMMENT '[OUTPUT] Composite AML risk score',
    ALERT_LEVEL             VARCHAR(10)     COMMENT '[OUTPUT] NONE / LOW / MEDIUM / HIGH / CRITICAL',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.CREDIT_RISK_IO (
    CUSTOMER_ID             VARCHAR(20)     COMMENT '[INPUT] Applicant identifier',
    ANNUAL_INCOME           FLOAT           COMMENT '[INPUT] Declared income in USD',
    CREDIT_SCORE            INTEGER         COMMENT '[INPUT] Bureau credit score',
    DEBT_TO_INCOME_RATIO    FLOAT           COMMENT '[INPUT] DTI ratio',
    EMPLOYMENT_STATUS       VARCHAR(30)     COMMENT '[INPUT] Employment classification',
    EXISTING_LOAN_COUNT     INTEGER         COMMENT '[INPUT] Current debt obligations count',
    MONTHS_CUSTOMER         INTEGER         COMMENT '[INPUT] Customer relationship tenure',
    OUTSTANDING_BALANCE     FLOAT           COMMENT '[INPUT] Total current exposure in USD',
    PD_SCORE                FLOAT           COMMENT '[OUTPUT] Probability of Default 0.0-1.0',
    RISK_GRADE              VARCHAR(5)      COMMENT '[OUTPUT] Internal risk grade AAA-CCC',
    APPROVED_LIMIT          FLOAT           COMMENT '[OUTPUT] Recommended credit limit in USD',
    DECISION                VARCHAR(20)     COMMENT '[OUTPUT] APPROVE / REVIEW / DECLINE',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.KYC_CLASSIFIER_IO (
    CUSTOMER_ID             VARCHAR(20)     COMMENT '[INPUT] Customer being verified',
    KYC_DOCUMENT_TYPE       VARCHAR(30)     COMMENT '[INPUT] Document type presented',
    KYC_DOCUMENT_COUNTRY    VARCHAR(3)      COMMENT '[INPUT] Document issuing country',
    PEP_FLAG                BOOLEAN         COMMENT '[INPUT] PEP pre-screen result',
    SANCTIONS_FLAG          BOOLEAN         COMMENT '[INPUT] Sanctions pre-screen result',
    KYC_EXPIRY_DATE         DATE            COMMENT '[INPUT] Document validity check',
    VERIFICATION_STATUS     VARCHAR(20)     COMMENT '[OUTPUT] VERIFIED / PENDING / REJECTED / ESCALATED',
    RISK_CLASSIFICATION     VARCHAR(20)     COMMENT '[OUTPUT] LOW_RISK / MEDIUM_RISK / HIGH_RISK',
    CONFIDENCE_SCORE        FLOAT           COMMENT '[OUTPUT] Document authenticity confidence 0.0-1.0',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.REGULATORY_VALIDATOR_IO (
    SUBMISSION_ID           VARCHAR(36)     COMMENT '[INPUT] Filing being validated',
    FILING_TYPE             VARCHAR(20)     COMMENT '[INPUT] Regulatory report type',
    COMPLETENESS_SCORE      FLOAT           COMMENT '[INPUT] Field completeness ratio',
    ERROR_COUNT             INTEGER         COMMENT '[INPUT] Pre-submission error count',
    RESTATEMENT_COUNT       INTEGER         COMMENT '[INPUT] Historical restatement count',
    DAYS_BEFORE_DEADLINE    INTEGER         COMMENT '[INPUT] Submission lead time in days',
    PASS_PROBABILITY        FLOAT           COMMENT '[OUTPUT] Probability of regulator acceptance 0.0-1.0',
    PREDICTED_STATUS        VARCHAR(20)     COMMENT '[OUTPUT] ACCEPTED / REJECTED / PENDING_REVIEW',
    REJECTION_RISK_FACTORS  VARCHAR(500)    COMMENT '[OUTPUT] Top risk factors as JSON array string',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);

CREATE OR REPLACE TABLE YOUR_DATABASE.MODEL_REGISTRY.CCAR_STRESS_IO (
    EXPOSURE_ID             VARCHAR(36)     COMMENT '[INPUT] Exposure record being stressed',
    ASSET_CLASS             VARCHAR(30)     COMMENT '[INPUT] Asset classification',
    OUTSTANDING_BALANCE     FLOAT           COMMENT '[INPUT] Current exposure amount in USD',
    LTV_RATIO               FLOAT           COMMENT '[INPUT] Collateral coverage ratio',
    INTEREST_RATE           FLOAT           COMMENT '[INPUT] Current annual interest rate as decimal',
    DAYS_PAST_DUE           INTEGER         COMMENT '[INPUT] Delinquency status in days',
    INTERNAL_RATING         VARCHAR(5)      COMMENT '[INPUT] Internal risk rating',
    STRESS_SCENARIO         VARCHAR(20)     COMMENT '[INPUT] Fed stress scenario applied',
    PROJECTED_LOSS          FLOAT           COMMENT '[OUTPUT] Projected loss under scenario in USD',
    LOSS_RATE               FLOAT           COMMENT '[OUTPUT] Loss as % of outstanding balance',
    REGULATORY_CAPITAL      FLOAT           COMMENT '[OUTPUT] Required capital allocation in USD',
    CET1_IMPACT             FLOAT           COMMENT '[OUTPUT] CET1 capital ratio impact in basis points',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);


-- ============================================================
-- LINEAGE VIEWS — FCB_CORE
-- MCC parses these SQL views to generate lineage between
-- base tables and reporting views in CDGC.
-- ============================================================

CREATE OR REPLACE VIEW YOUR_DATABASE.FCB_CORE.CUSTOMER_RISK_SUMMARY
  COMMENT = 'Customer profile joined with daily risk exposure — source for risk-based reporting'
AS
SELECT
    c.CUSTOMER_ID,
    c.FIRST_NAME,
    c.LAST_NAME,
    c.SSN,
    c.DATE_OF_BIRTH,
    c.EMAIL,
    c.CREDIT_SCORE,
    c.RISK_TIER,
    c.ANNUAL_INCOME,
    r.ASSESSMENT_DATE,
    r.RISK_CATEGORY,
    r.EXPOSURE_AMOUNT,
    r.PROBABILITY_OF_DEFAULT,
    r.LOSS_GIVEN_DEFAULT,
    r.EXPECTED_LOSS,
    r.RISK_RATING,
    r.REGULATORY_CAPITAL
FROM YOUR_DATABASE.FCB_CORE.CUSTOMER_MASTER c
JOIN YOUR_DATABASE.FCB_CORE.RISK_EXPOSURE_DAILY r ON c.CUSTOMER_ID = r.CUSTOMER_ID;

CREATE OR REPLACE VIEW YOUR_DATABASE.FCB_CORE.TRANSACTION_SUMMARY_DAILY
  COMMENT = 'Daily transaction aggregation per customer — feeds CTR reporting and AML monitoring'
AS
SELECT
    CUSTOMER_ID,
    CAST(TRANSACTION_DATE AS DATE)  AS TRANSACTION_DATE,
    CURRENCY,
    COUNT(*)                        AS TRANSACTION_COUNT,
    SUM(AMOUNT)                     AS TOTAL_AMOUNT,
    MAX(AMOUNT)                     AS MAX_AMOUNT,
    SUM(CASE WHEN STATUS = 'COMPLETED' THEN 1 ELSE 0 END)              AS COMPLETED_COUNT,
    SUM(CASE WHEN AMOUNT >= 10000 AND CURRENCY = 'USD' THEN 1 ELSE 0 END) AS CTR_ELIGIBLE_COUNT
FROM YOUR_DATABASE.FCB_CORE.TRANSACTION_LEDGER
GROUP BY CUSTOMER_ID, CAST(TRANSACTION_DATE AS DATE), CURRENCY;

CREATE OR REPLACE VIEW YOUR_DATABASE.FCB_CORE.REGULATORY_EXPOSURE_REPORT
  COMMENT = 'Basel/CCAR regulatory exposure report — joins customer, risk, and GL data for regulatory submission'
AS
SELECT
    c.CUSTOMER_ID,
    c.SSN,
    c.DATE_OF_BIRTH,
    c.CREDIT_SCORE,
    c.RISK_TIER,
    r.ASSESSMENT_DATE,
    r.RISK_CATEGORY,
    r.EXPOSURE_AMOUNT,
    r.PROBABILITY_OF_DEFAULT,
    r.LOSS_GIVEN_DEFAULT,
    r.EXPECTED_LOSS,
    r.REGULATORY_CAPITAL,
    r.BASEL_CLASS,
    r.RISK_RATING,
    g.ACCOUNT_CODE,
    g.DEBIT_AMOUNT,
    g.CREDIT_AMOUNT,
    g.FISCAL_PERIOD,
    g.FISCAL_YEAR,
    g.LEGAL_ENTITY
FROM YOUR_DATABASE.FCB_CORE.CUSTOMER_MASTER c
JOIN YOUR_DATABASE.FCB_CORE.RISK_EXPOSURE_DAILY r ON c.CUSTOMER_ID = r.CUSTOMER_ID
JOIN YOUR_DATABASE.FCB_CORE.GL_ENTRY_REGISTER g   ON g.ACCOUNT_CODE IN ('1200','5100','6001');


-- ============================================================
-- LINEAGE VIEWS — MODEL_REGISTRY
-- MCC parses the SQL in these views to auto-generate
-- column-level lineage: TRAINING_DATA → MODEL_REGISTRY
-- ============================================================

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_FRAUD_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: TRANSACTION_FEATURES → FRAUD_DETECTOR_IO'
AS
SELECT
    tf.TRANSACTION_AMOUNT,
    tf.MERCHANT_CATEGORY_CODE,
    tf.DEVICE_FINGERPRINT,
    tf.VELOCITY_1H,
    tf.VELOCITY_24H,
    tf.AVG_TRANSACTION_30D,
    tf.IS_INTERNATIONAL,
    tf.GEOLOCATION_COUNTRY
FROM YOUR_DATABASE.TRAINING_DATA.TRANSACTION_FEATURES tf
WHERE tf.DATA_PARTITION = 'TRAIN'
  AND tf.TRANSACTION_AMOUNT IS NOT NULL;

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_BEHAVIORAL_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: TRANSACTION_FEATURES → BEHAVIORAL_ANOMALY_IO'
AS
SELECT
    tf.ACCOUNT_ID,
    tf.VELOCITY_24H,
    tf.AVG_TRANSACTION_30D,
    tf.CHANNEL,
    tf.DEVICE_FINGERPRINT,
    tf.TRANSACTION_AMOUNT,
    tf.GEOLOCATION_COUNTRY
FROM YOUR_DATABASE.TRAINING_DATA.TRANSACTION_FEATURES tf
WHERE tf.DATA_PARTITION = 'TRAIN';

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_AML_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: TRANSACTION_FEATURES + CUSTOMER_360_FEATURES → AML_ANOMALY_IO'
AS
SELECT
    tf.ACCOUNT_ID,
    tf.TRANSACTION_AMOUNT,
    tf.MERCHANT_CATEGORY_CODE,
    tf.VELOCITY_24H,
    tf.IS_INTERNATIONAL,
    tf.GEOLOCATION_COUNTRY,
    cf.SANCTIONS_FLAG,
    cf.PEP_FLAG
FROM YOUR_DATABASE.TRAINING_DATA.TRANSACTION_FEATURES tf
JOIN YOUR_DATABASE.TRAINING_DATA.CUSTOMER_360_FEATURES cf ON tf.ACCOUNT_ID = cf.CUSTOMER_ID
WHERE tf.DATA_PARTITION = 'TRAIN';

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_CREDIT_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: CUSTOMER_360_FEATURES + RISK_EXPOSURE_FEATURES → CREDIT_RISK_IO'
AS
SELECT
    cf.CUSTOMER_ID,
    cf.ANNUAL_INCOME,
    cf.CREDIT_SCORE,
    cf.DEBT_TO_INCOME_RATIO,
    cf.EMPLOYMENT_STATUS,
    cf.EXISTING_LOAN_COUNT,
    cf.MONTHS_CUSTOMER,
    re.OUTSTANDING_BALANCE
FROM YOUR_DATABASE.TRAINING_DATA.CUSTOMER_360_FEATURES cf
LEFT JOIN YOUR_DATABASE.TRAINING_DATA.RISK_EXPOSURE_FEATURES re ON cf.CUSTOMER_ID = re.COUNTERPARTY_ID
WHERE cf.DATA_PARTITION = 'TRAIN';

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_KYC_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: CUSTOMER_360_FEATURES → KYC_CLASSIFIER_IO'
AS
SELECT
    cf.CUSTOMER_ID,
    cf.KYC_DOCUMENT_TYPE,
    cf.KYC_DOCUMENT_COUNTRY,
    cf.PEP_FLAG,
    cf.SANCTIONS_FLAG,
    cf.KYC_EXPIRY_DATE
FROM YOUR_DATABASE.TRAINING_DATA.CUSTOMER_360_FEATURES cf
WHERE cf.DATA_PARTITION = 'TRAIN';

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_REGULATORY_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: REGULATORY_SUBMISSIONS_FEATURES → REGULATORY_VALIDATOR_IO'
AS
SELECT
    rs.SUBMISSION_ID,
    rs.FILING_TYPE,
    rs.COMPLETENESS_SCORE,
    rs.ERROR_COUNT,
    rs.RESTATEMENT_COUNT,
    DATEDIFF('day', rs.SUBMISSION_DATE, rs.DEADLINE_DATE) AS DAYS_BEFORE_DEADLINE
FROM YOUR_DATABASE.TRAINING_DATA.REGULATORY_SUBMISSIONS_FEATURES rs
WHERE rs.DATA_PARTITION = 'TRAIN';

CREATE OR REPLACE VIEW YOUR_DATABASE.MODEL_REGISTRY.V_CCAR_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: RISK_EXPOSURE_FEATURES + REGULATORY_SUBMISSIONS_FEATURES → CCAR_STRESS_IO'
AS
SELECT
    re.EXPOSURE_ID,
    re.ASSET_CLASS,
    re.OUTSTANDING_BALANCE,
    re.LTV_RATIO,
    re.INTEREST_RATE,
    re.DAYS_PAST_DUE,
    re.INTERNAL_RATING,
    re.STRESS_SCENARIO
FROM YOUR_DATABASE.TRAINING_DATA.RISK_EXPOSURE_FEATURES re
WHERE re.STRESS_SCENARIO IN ('BASELINE', 'ADVERSE', 'SEVERELY_ADVERSE');


-- ============================================================
-- VERIFICATION — Run after execution to confirm setup
-- ============================================================

SHOW TABLES IN SCHEMA YOUR_DATABASE.FCB_CORE;
SHOW TABLES IN SCHEMA YOUR_DATABASE.TRAINING_DATA;
SHOW TABLES IN SCHEMA YOUR_DATABASE.MODEL_REGISTRY;
SHOW VIEWS  IN SCHEMA YOUR_DATABASE.FCB_CORE;
SHOW VIEWS  IN SCHEMA YOUR_DATABASE.MODEL_REGISTRY;

-- Row counts (populated separately by seed script)
-- SELECT COUNT(*) FROM YOUR_DATABASE.FCB_CORE.CUSTOMER_MASTER;       -- expect 500
-- SELECT COUNT(*) FROM YOUR_DATABASE.FCB_CORE.TRANSACTION_LEDGER;    -- expect 2000
-- SELECT COUNT(*) FROM YOUR_DATABASE.FCB_CORE.GL_ENTRY_REGISTER;     -- expect 800
-- SELECT COUNT(*) FROM YOUR_DATABASE.FCB_CORE.RISK_EXPOSURE_DAILY;   -- expect 600
