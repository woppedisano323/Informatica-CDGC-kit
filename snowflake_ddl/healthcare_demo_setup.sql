-- ============================================================
-- Healthcare AI Governance Demo — Snowflake Setup
-- ============================================================
-- Purpose: Create all tables, views, and AI model schemas
--   needed for the CDGC Healthcare demo environment.
--   Run this in Snowflake or DBeaver before MCC scanning.
--
-- Database : CDGC_DEMO (or existing — update USE DATABASE below)
-- Schemas  :
--   CLINICAL_CORE    — 6 core clinical tables + 3 reporting views
--   TRAINING_DATA    — 2 ML feature tables (Sepsis, NLP)
--   MODEL_REGISTRY   — 2 AI model I/O tables + 2 lineage views
--
-- Aligns with:
--   09_AI_System.xlsx  — Clinical Decision Support Platform, NLP Engine
--   10_AI_Model.xlsx   — Sepsis Risk Prediction Model, Clinical Note NLP Model
--   11_Business_Term.xlsx — 38 terms: USCDI clinical data, PHI/HIPAA, SDOH
--   12_Data_Set.xlsx   — Patient Summary, PHI Disclosure Log, Claims, Labs,
--                        Demographics, Immunization Registry, SDOH Screening
--   13_DQ_Rule_Template.xlsx — 10 rules: DOB, ICD-10, LOINC, CVX, PHI, etc.
--
-- After running:
--   In MCC → catalog source:
--   - Filter: CDGC_DEMO.CLINICAL_CORE, CDGC_DEMO.TRAINING_DATA,
--             CDGC_DEMO.MODEL_REGISTRY
--   - Enable: Metadata Extraction, Data Profiling, Data Quality,
--             Data Classification, Glossary Association, Lineage Discovery
--   - Run scan
-- ============================================================


-- ── 1. SETUP ──────────────────────────────────────────────────

USE WAREHOUSE COMPUTE_WH;
USE DATABASE CDGC_DEMO;  -- change to your target database

CREATE SCHEMA IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE
  COMMENT = 'Core clinical data tables for healthcare CDGC demo. Scanned by MCC.';

CREATE SCHEMA IF NOT EXISTS CDGC_DEMO.TRAINING_DATA
  COMMENT = 'Feature datasets used to train clinical AI models. Scanned by MCC for DQ monitoring.';

CREATE SCHEMA IF NOT EXISTS CDGC_DEMO.MODEL_REGISTRY
  COMMENT = 'AI model input/output contracts. Simulates clinical ML platform schema for MCC lineage.';


-- ============================================================
-- CLINICAL_CORE — Core Clinical Tables
-- ============================================================

-- ── PATIENT_DEMOGRAPHICS ──────────────────────────────────────
-- Maps to: AHSDS-05 Patient Demographics File
-- DQ Rules: AHSDQR-01 (DATE_OF_BIRTH), AHSDQR-08 (CONSENT_ON_FILE),
--           AHSDQR-10 (PATIENT_ID)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.PATIENT_DEMOGRAPHICS (
    PATIENT_ID              VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique patient identifier — MRN or enterprise patient ID',
    FIRST_NAME              VARCHAR(50)                        COMMENT 'Patient first name — PHI',
    LAST_NAME               VARCHAR(50)                        COMMENT 'Patient last name — PHI',
    DATE_OF_BIRTH           DATE                               COMMENT 'Patient date of birth — PHI, USCDI required',
    SEX                     VARCHAR(10)                        COMMENT 'Administrative sex: MALE / FEMALE / UNKNOWN / OTHER',
    RACE                    VARCHAR(50)                        COMMENT 'Race per OMB standards — USCDI required',
    ETHNICITY               VARCHAR(50)                        COMMENT 'Ethnicity per OMB standards — USCDI required',
    PREFERRED_LANGUAGE      VARCHAR(50)                        COMMENT 'Patient preferred language for communication',
    ADDRESS_LINE1           VARCHAR(100)                       COMMENT 'Street address — PHI',
    CITY                    VARCHAR(50)                        COMMENT 'City of residence',
    STATE                   VARCHAR(2)                         COMMENT 'State abbreviation',
    ZIP_CODE                VARCHAR(10)                        COMMENT 'Postal zip code',
    PHONE_NUMBER            VARCHAR(20)                        COMMENT 'Primary phone number — PHI',
    EMAIL                   VARCHAR(100)                       COMMENT 'Primary email address — PHI',
    EMERGENCY_CONTACT       VARCHAR(100)                       COMMENT 'Emergency contact name and phone',
    CONSENT_ON_FILE         BOOLEAN                            COMMENT 'HIPAA consent authorization on file',
    CONSENT_DATE            DATE                               COMMENT 'Date consent was signed',
    PATIENT_SINCE           DATE                               COMMENT 'Date of first encounter with this organization',
    INSURANCE_PLAN_ID       VARCHAR(20)                        COMMENT 'Primary insurance plan identifier',
    PCP_PROVIDER_ID         VARCHAR(20)                        COMMENT 'Primary care provider identifier'
);

-- ── CLINICAL_ENCOUNTERS ───────────────────────────────────────
-- Maps to: AHSDS-01 USCDI Patient Summary, AHSDS-03 Claims Data Feed
-- DQ Rules: AHSDQR-02 (ICD10_CODE)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.CLINICAL_ENCOUNTERS (
    ENCOUNTER_ID            VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique encounter identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient identifier — foreign key to PATIENT_DEMOGRAPHICS',
    ENCOUNTER_DATE          TIMESTAMP                          COMMENT 'Date and time encounter was initiated',
    ENCOUNTER_TYPE          VARCHAR(30)                        COMMENT 'INPATIENT / OUTPATIENT / ED / TELEHEALTH / OBSERVATION',
    FACILITY_CODE           VARCHAR(20)                        COMMENT 'Facility or clinic identifier',
    PROVIDER_ID             VARCHAR(20)                        COMMENT 'Attending or primary provider identifier',
    ICD10_CODE              VARCHAR(10)                        COMMENT 'Primary diagnosis ICD-10-CM code — DQ: must be valid ICD-10',
    PROCEDURE_CODE          VARCHAR(10)                        COMMENT 'Primary procedure CPT/HCPCS code',
    DRG_CODE                VARCHAR(10)                        COMMENT 'Diagnosis Related Group code for inpatient billing',
    ADMISSION_DATE          DATE                               COMMENT 'Date of admission (inpatient only)',
    DISCHARGE_DATE          DATE                               COMMENT 'Date of discharge (inpatient only)',
    DISCHARGE_DISPOSITION   VARCHAR(30)                        COMMENT 'HOME / SNF / REHAB / EXPIRED / AMA / TRANSFER',
    ADMISSION_TYPE          VARCHAR(20)                        COMMENT 'ELECTIVE / URGENT / EMERGENCY / NEWBORN',
    LENGTH_OF_STAY          INTEGER                            COMMENT 'Length of stay in days (inpatient only)',
    STATUS                  VARCHAR(20)                        COMMENT 'ACTIVE / DISCHARGED / CANCELLED',
    PAYER_TYPE              VARCHAR(30)                        COMMENT 'MEDICARE / MEDICAID / COMMERCIAL / SELF_PAY'
);

-- ── LAB_RESULTS ───────────────────────────────────────────────
-- Maps to: AHSDS-04 Lab Results Feed
-- DQ Rules: AHSDQR-03 (LOINC_CODE), AHSDQR-07 (LAB_RESULT_UNITS)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.LAB_RESULTS (
    RESULT_ID               VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique lab result identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient identifier — foreign key to PATIENT_DEMOGRAPHICS',
    ENCOUNTER_ID            VARCHAR(20)                        COMMENT 'Encounter where lab was ordered',
    LAB_TEST_NAME           VARCHAR(100)                       COMMENT 'Human-readable lab test name — USCDI required',
    LOINC_CODE              VARCHAR(10)                        COMMENT 'LOINC code for the test — DQ: must be valid LOINC',
    LAB_RESULT_VALUE        VARCHAR(50)                        COMMENT 'Result value (numeric or text)',
    NUMERIC_VALUE           FLOAT                              COMMENT 'Numeric result value where applicable',
    LAB_RESULT_UNITS        VARCHAR(20)                        COMMENT 'Units of measure — DQ: must be present for numeric results',
    LAB_REFERENCE_RANGE     VARCHAR(50)                        COMMENT 'Normal reference range e.g. 3.5-5.0',
    ABNORMAL_FLAG           VARCHAR(10)                        COMMENT 'H=High, L=Low, C=Critical, N=Normal',
    RESULT_DATE             TIMESTAMP                          COMMENT 'Date and time result was finalized',
    ORDERING_PROVIDER       VARCHAR(20)                        COMMENT 'Provider who ordered the test',
    SPECIMEN_TYPE           VARCHAR(30)                        COMMENT 'BLOOD / URINE / TISSUE / SWAB / CSF',
    STATUS                  VARCHAR(20)                        COMMENT 'FINAL / PRELIMINARY / CORRECTED / CANCELLED'
);

-- ── MEDICATION_ORDERS ─────────────────────────────────────────
-- Maps to: AHSDS-01 USCDI Patient Summary
-- DQ Rules: AHSDQR-06 (MEDICATION_DOSE)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.MEDICATION_ORDERS (
    ORDER_ID                VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique medication order identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient identifier — foreign key to PATIENT_DEMOGRAPHICS',
    ENCOUNTER_ID            VARCHAR(20)                        COMMENT 'Encounter where medication was ordered',
    MEDICATION_NAME         VARCHAR(100)                       COMMENT 'Generic or brand medication name — USCDI required',
    NDC_CODE                VARCHAR(15)                        COMMENT 'National Drug Code identifier',
    RXNORM_CODE             VARCHAR(10)                        COMMENT 'RxNorm medication concept code',
    MEDICATION_DOSE         FLOAT                              COMMENT 'Prescribed dose amount — DQ: must be within clinical range',
    DOSE_UNIT               VARCHAR(20)                        COMMENT 'Dose unit: mg / mcg / mL / units',
    ROUTE_OF_ADMINISTRATION VARCHAR(30)                        COMMENT 'ORAL / IV / IM / SC / TOPICAL / INHALED',
    FREQUENCY               VARCHAR(30)                        COMMENT 'QD / BID / TID / QID / PRN / Q4H',
    START_DATE              DATE                               COMMENT 'Medication start date',
    END_DATE                DATE                               COMMENT 'Medication end date (null if ongoing)',
    PRESCRIBER_ID           VARCHAR(20)                        COMMENT 'Ordering provider identifier',
    MEDICATION_STATUS       VARCHAR(20)                        COMMENT 'ACTIVE / DISCONTINUED / ON_HOLD / COMPLETED',
    DISPENSE_QUANTITY       FLOAT                              COMMENT 'Quantity dispensed',
    REFILLS_AUTHORIZED      INTEGER                            COMMENT 'Number of refills authorized'
);

-- ── IMMUNIZATION_RECORDS ──────────────────────────────────────
-- Maps to: AHSDS-06 Immunization Registry
-- DQ Rules: AHSDQR-04 (CVX_CODE)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.IMMUNIZATION_RECORDS (
    IMMUNIZATION_ID         VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique immunization record identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient identifier — foreign key to PATIENT_DEMOGRAPHICS',
    IMMUNIZATION_NAME       VARCHAR(100)                       COMMENT 'Vaccine name — USCDI required',
    CVX_CODE                VARCHAR(5)                         COMMENT 'CDC CVX vaccine code — DQ: must be valid CVX',
    IMMUNIZATION_DATE       DATE                               COMMENT 'Date vaccine was administered — USCDI required',
    LOT_NUMBER              VARCHAR(20)                        COMMENT 'Vaccine lot number',
    MANUFACTURER            VARCHAR(50)                        COMMENT 'Vaccine manufacturer name',
    ROUTE                   VARCHAR(20)                        COMMENT 'IM / SC / ORAL / INTRANASAL',
    SITE                    VARCHAR(20)                        COMMENT 'Anatomical administration site',
    ADMINISTERED_BY         VARCHAR(20)                        COMMENT 'Provider who administered the vaccine',
    DOSE_NUMBER             INTEGER                            COMMENT 'Dose number in series (1, 2, 3...)',
    SERIES_COMPLETE         BOOLEAN                            COMMENT 'True if vaccination series is complete',
    REGISTRY_REPORTED       BOOLEAN                            COMMENT 'True if reported to state immunization registry'
);

-- ── SDOH_ASSESSMENTS ──────────────────────────────────────────
-- Maps to: AHSDS-07 SDOH Screening Data
-- DQ Rules: AHSDQR-09 (ASSESSMENT_DATE)
-- Business Terms: AHSBT-30 (Housing Instability), AHSBT-31 (Food Insecurity),
--                 AHSBT-32 (Transportation Barrier)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.SDOH_ASSESSMENTS (
    ASSESSMENT_ID           VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique SDOH assessment identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient identifier — foreign key to PATIENT_DEMOGRAPHICS',
    ENCOUNTER_ID            VARCHAR(20)                        COMMENT 'Encounter where screening was conducted',
    ASSESSMENT_DATE         DATE                               COMMENT 'Date SDOH screening was completed — DQ: must be within 12 months',
    SCREENING_TOOL          VARCHAR(50)                        COMMENT 'AHC-HRSN / PRAPARE / WellRx / FIND',
    HOUSING_INSTABILITY     BOOLEAN                            COMMENT 'Patient reported housing instability or homelessness risk',
    FOOD_INSECURITY         BOOLEAN                            COMMENT 'Patient reported food insecurity or hunger',
    TRANSPORTATION_BARRIER  BOOLEAN                            COMMENT 'Patient reported transportation barrier to care',
    INTERPERSONAL_VIOLENCE  BOOLEAN                            COMMENT 'Patient reported intimate partner or domestic violence risk',
    FINANCIAL_STRAIN        BOOLEAN                            COMMENT 'Patient reported financial difficulty meeting basic needs',
    SOCIAL_ISOLATION        BOOLEAN                            COMMENT 'Patient reported social isolation or lack of support',
    SDOH_RISK_SCORE         INTEGER                            COMMENT 'Composite SDOH risk score 0-10',
    REFERRAL_MADE           BOOLEAN                            COMMENT 'True if community referral was initiated',
    REFERRAL_TYPE           VARCHAR(100)                       COMMENT 'Type of community resource referral made',
    ADMINISTERED_BY         VARCHAR(20)                        COMMENT 'Provider or staff who conducted screening'
);

-- ── PHI_DISCLOSURE_LOG ────────────────────────────────────────
-- Maps to: AHSDS-02 PHI Disclosure Log
-- Business Terms: AHSBT-33 (PHI Minimum Necessary), AHSBT-34 (Business Associate)
-- DQ Rules: AHSDQR-05 (PHI_CATEGORY)
CREATE TABLE IF NOT EXISTS CDGC_DEMO.CLINICAL_CORE.PHI_DISCLOSURE_LOG (
    DISCLOSURE_ID           VARCHAR(20)   NOT NULL PRIMARY KEY COMMENT 'Unique PHI disclosure event identifier',
    PATIENT_ID              VARCHAR(20)                        COMMENT 'Patient whose PHI was disclosed',
    DISCLOSURE_DATE         TIMESTAMP                          COMMENT 'Date and time of PHI disclosure',
    DISCLOSURE_TYPE         VARCHAR(30)                        COMMENT 'TREATMENT / PAYMENT / OPERATIONS / RESEARCH / LEGAL / MARKETING',
    RECIPIENT_NAME          VARCHAR(100)                       COMMENT 'Name of entity receiving PHI',
    RECIPIENT_TYPE          VARCHAR(30)                        COMMENT 'COVERED_ENTITY / BUSINESS_ASSOCIATE / PATIENT / GOVERNMENT',
    PHI_CATEGORY            VARCHAR(50)                        COMMENT 'Category of PHI disclosed — DQ: must align with minimum necessary standard',
    MINIMUM_NECESSARY       BOOLEAN                            COMMENT 'True if disclosure was limited to minimum necessary PHI',
    AUTHORIZATION_TYPE      VARCHAR(30)                        COMMENT 'CONSENT / AUTHORIZATION / LEGAL_REQUIREMENT / TPO',
    AUTHORIZATION_ID        VARCHAR(20)                        COMMENT 'Reference to signed authorization document',
    PURPOSE_OF_DISCLOSURE   VARCHAR(200)                       COMMENT 'Clinical or administrative reason for disclosure',
    DATA_ELEMENTS_SHARED    VARCHAR(500)                       COMMENT 'List of specific data elements disclosed',
    DISCLOSED_BY            VARCHAR(20)                        COMMENT 'Staff member who processed the disclosure',
    HIPAA_EXCEPTION_APPLIED BOOLEAN                            COMMENT 'True if a HIPAA exception permitted disclosure without authorization'
);


-- ============================================================
-- TRAINING_DATA — ML Feature Tables
-- ============================================================

-- ── SEPSIS_RISK_FEATURES ──────────────────────────────────────
-- Feeds: Sepsis Risk Prediction Model (AHSAIM-01)
-- Source: CLINICAL_ENCOUNTERS + LAB_RESULTS + VITAL_SIGNS
CREATE OR REPLACE TABLE CDGC_DEMO.TRAINING_DATA.SEPSIS_RISK_FEATURES (
    PATIENT_ID              VARCHAR(20)     NOT NULL    COMMENT 'Patient identifier',
    ENCOUNTER_ID            VARCHAR(20)     NOT NULL    COMMENT 'ICU or ED encounter identifier',
    HEART_RATE              FLOAT                       COMMENT 'Heart rate in bpm — NULL indicates missing vitals (DQ issue)',
    RESPIRATORY_RATE        FLOAT                       COMMENT 'Respiratory rate per minute',
    TEMPERATURE_C           FLOAT                       COMMENT 'Body temperature in Celsius',
    SYSTOLIC_BP             FLOAT                       COMMENT 'Systolic blood pressure mmHg',
    DIASTOLIC_BP            FLOAT                       COMMENT 'Diastolic blood pressure mmHg',
    SPO2                    FLOAT                       COMMENT 'Oxygen saturation percentage',
    WBC_COUNT               FLOAT                       COMMENT 'White blood cell count x10^9/L — LOINC 6690-2',
    LACTATE_LEVEL           FLOAT                       COMMENT 'Serum lactate mmol/L — DQ: values > 20 flagged as anomalous',
    CREATININE              FLOAT                       COMMENT 'Serum creatinine mg/dL — LOINC 2160-0',
    GLASGOW_COMA_SCORE      INTEGER                     COMMENT 'GCS total score 3-15',
    VASOPRESSOR_USE         BOOLEAN                     COMMENT 'True if vasopressors currently active',
    MECHANICAL_VENTILATION  BOOLEAN                     COMMENT 'True if patient on mechanical ventilation',
    SOFA_SCORE              INTEGER                     COMMENT 'Sequential Organ Failure Assessment score 0-24',
    PRIOR_SEPSIS            BOOLEAN                     COMMENT 'True if patient has prior sepsis diagnosis',
    ICU_HOURS               INTEGER                     COMMENT 'Hours in ICU at time of assessment',
    AGE_AT_ENCOUNTER        INTEGER                     COMMENT 'Patient age in years at time of encounter',
    SEPSIS_LABEL            INTEGER                     COMMENT 'Ground truth: 1=sepsis onset within 6h, 0=no onset',
    DATA_PARTITION          VARCHAR(10)                 COMMENT 'TRAIN / VALIDATE / TEST',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training set'
);

-- ── NLP_DOCUMENT_CORPUS ───────────────────────────────────────
-- Feeds: Clinical Note NLP Model (AHSAIM-02)
CREATE OR REPLACE TABLE CDGC_DEMO.TRAINING_DATA.NLP_DOCUMENT_CORPUS (
    DOCUMENT_ID             VARCHAR(36)     NOT NULL    COMMENT 'Unique document identifier',
    PATIENT_ID              VARCHAR(20)     NOT NULL    COMMENT 'Patient identifier (de-identified for training)',
    ENCOUNTER_ID            VARCHAR(20)                 COMMENT 'Associated encounter',
    DOCUMENT_TYPE           VARCHAR(30)                 COMMENT 'PROGRESS_NOTE / DISCHARGE_SUMMARY / RADIOLOGY / PATHOLOGY / CONSULT',
    DOCUMENT_DATE           DATE                        COMMENT 'Date note was authored',
    AUTHOR_SPECIALTY        VARCHAR(50)                 COMMENT 'Clinical specialty of authoring provider',
    NOTE_TEXT               VARCHAR(5000)               COMMENT 'Clinical note text (de-identified) — primary NLP input',
    WORD_COUNT              INTEGER                     COMMENT 'Word count of note text',
    ICD10_MENTIONS          VARCHAR(500)                COMMENT 'ICD-10 codes mentioned or extracted from note',
    LOINC_MENTIONS          VARCHAR(500)                COMMENT 'LOINC codes for tests referenced in note',
    MEDICATION_MENTIONS     VARCHAR(500)                COMMENT 'Medications mentioned in note text',
    SENTIMENT_LABEL         VARCHAR(20)                 COMMENT 'POSITIVE / NEGATIVE / NEUTRAL — clinical outcome sentiment',
    NLP_EXTRACT_LABEL       INTEGER                     COMMENT 'Ground truth: 1=clinically actionable content, 0=routine',
    PHI_SCRUBBED            BOOLEAN                     COMMENT 'True if PHI has been de-identified from note text',
    DATA_PARTITION          VARCHAR(10)                 COMMENT 'TRAIN / VALIDATE / TEST',
    RECORD_CREATED_DATE     DATE                        COMMENT 'Date record added to training corpus'
);


-- ============================================================
-- MODEL_REGISTRY — AI Model I/O Tables
-- ============================================================

-- ── SEPSIS_RISK_IO ────────────────────────────────────────────
-- Maps to: AHSAIM-01 Sepsis Risk Prediction Model
CREATE OR REPLACE TABLE CDGC_DEMO.MODEL_REGISTRY.SEPSIS_RISK_IO (
    PATIENT_ID              VARCHAR(20)     COMMENT '[INPUT] Patient being assessed',
    ENCOUNTER_ID            VARCHAR(20)     COMMENT '[INPUT] Current ICU/ED encounter',
    HEART_RATE              FLOAT           COMMENT '[INPUT] Current heart rate bpm',
    RESPIRATORY_RATE        FLOAT           COMMENT '[INPUT] Current respiratory rate',
    TEMPERATURE_C           FLOAT           COMMENT '[INPUT] Current body temperature',
    SYSTOLIC_BP             FLOAT           COMMENT '[INPUT] Current systolic blood pressure',
    WBC_COUNT               FLOAT           COMMENT '[INPUT] Latest WBC count',
    LACTATE_LEVEL           FLOAT           COMMENT '[INPUT] Latest lactate measurement',
    SOFA_SCORE              INTEGER         COMMENT '[INPUT] Current SOFA score',
    SEPSIS_RISK_SCORE       FLOAT           COMMENT '[OUTPUT] Predicted sepsis risk 0.0-1.0',
    RISK_TIER               VARCHAR(10)     COMMENT '[OUTPUT] LOW / MEDIUM / HIGH / CRITICAL',
    ALERT_TRIGGERED         BOOLEAN         COMMENT '[OUTPUT] True if sepsis alert should be raised',
    RECOMMENDED_ACTION      VARCHAR(100)    COMMENT '[OUTPUT] MONITOR / BLOOD_CULTURES / ANTIBIOTICS / ICU_ESCALATE',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] When inference was executed'
);

-- ── CLINICAL_NLP_IO ───────────────────────────────────────────
-- Maps to: AHSAIM-02 Clinical Note NLP Model
CREATE OR REPLACE TABLE CDGC_DEMO.MODEL_REGISTRY.CLINICAL_NLP_IO (
    DOCUMENT_ID             VARCHAR(36)     COMMENT '[INPUT] Document being processed',
    PATIENT_ID              VARCHAR(20)     COMMENT '[INPUT] Patient identifier',
    DOCUMENT_TYPE           VARCHAR(30)     COMMENT '[INPUT] Note type for context',
    NOTE_TEXT               VARCHAR(5000)   COMMENT '[INPUT] Clinical note text',
    EXTRACTED_ICD10         VARCHAR(500)    COMMENT '[OUTPUT] ICD-10 codes extracted from note',
    EXTRACTED_MEDICATIONS   VARCHAR(500)    COMMENT '[OUTPUT] Medication entities identified',
    EXTRACTED_LOINC         VARCHAR(500)    COMMENT '[OUTPUT] Lab/procedure codes identified',
    CLINICAL_FINDINGS       VARCHAR(1000)   COMMENT '[OUTPUT] Key clinical findings as structured JSON',
    PHI_DETECTED            BOOLEAN         COMMENT '[OUTPUT] True if residual PHI detected in note',
    ACTIONABILITY_SCORE     FLOAT           COMMENT '[OUTPUT] Clinical actionability score 0.0-1.0',
    CONFIDENCE_SCORE        FLOAT           COMMENT '[OUTPUT] Extraction confidence 0.0-1.0',
    MODEL_VERSION           VARCHAR(10)     COMMENT '[META] Model version identifier',
    INFERENCE_TIMESTAMP     TIMESTAMP_NTZ   COMMENT '[META] Inference timestamp'
);


-- ============================================================
-- LINEAGE VIEWS — CLINICAL_CORE
-- MCC parses these SQL views to generate lineage between
-- base tables and reporting views in CDGC.
-- ============================================================

CREATE OR REPLACE VIEW CDGC_DEMO.CLINICAL_CORE.PATIENT_CLINICAL_SUMMARY
  COMMENT = 'USCDI patient summary — joins demographics, encounters, and labs for care coordination'
AS
SELECT
    p.PATIENT_ID,
    p.FIRST_NAME,
    p.LAST_NAME,
    p.DATE_OF_BIRTH,
    p.SEX,
    p.RACE,
    p.ETHNICITY,
    p.PREFERRED_LANGUAGE,
    p.CONSENT_ON_FILE,
    e.ENCOUNTER_ID,
    e.ENCOUNTER_DATE,
    e.ENCOUNTER_TYPE,
    e.ICD10_CODE,
    e.DISCHARGE_DISPOSITION,
    l.LAB_TEST_NAME,
    l.LOINC_CODE,
    l.LAB_RESULT_VALUE,
    l.LAB_RESULT_UNITS,
    l.ABNORMAL_FLAG,
    l.RESULT_DATE
FROM CDGC_DEMO.CLINICAL_CORE.PATIENT_DEMOGRAPHICS p
JOIN CDGC_DEMO.CLINICAL_CORE.CLINICAL_ENCOUNTERS e ON p.PATIENT_ID = e.PATIENT_ID
LEFT JOIN CDGC_DEMO.CLINICAL_CORE.LAB_RESULTS l    ON e.ENCOUNTER_ID = l.ENCOUNTER_ID;

CREATE OR REPLACE VIEW CDGC_DEMO.CLINICAL_CORE.HIGH_RISK_PATIENT_REPORT
  COMMENT = 'High-risk patients with SDOH needs and recent ED/inpatient encounters — care management prioritization'
AS
SELECT
    p.PATIENT_ID,
    p.DATE_OF_BIRTH,
    p.PREFERRED_LANGUAGE,
    e.ENCOUNTER_DATE,
    e.ENCOUNTER_TYPE,
    e.ICD10_CODE,
    e.LENGTH_OF_STAY,
    s.ASSESSMENT_DATE,
    s.HOUSING_INSTABILITY,
    s.FOOD_INSECURITY,
    s.TRANSPORTATION_BARRIER,
    s.SDOH_RISK_SCORE,
    s.REFERRAL_MADE
FROM CDGC_DEMO.CLINICAL_CORE.PATIENT_DEMOGRAPHICS p
JOIN CDGC_DEMO.CLINICAL_CORE.CLINICAL_ENCOUNTERS e  ON p.PATIENT_ID = e.PATIENT_ID
LEFT JOIN CDGC_DEMO.CLINICAL_CORE.SDOH_ASSESSMENTS s ON p.PATIENT_ID = s.PATIENT_ID
WHERE e.ENCOUNTER_TYPE IN ('ED', 'INPATIENT')
  AND s.SDOH_RISK_SCORE >= 3;

CREATE OR REPLACE VIEW CDGC_DEMO.CLINICAL_CORE.PHI_DISCLOSURE_SUMMARY
  COMMENT = 'HIPAA compliance summary — PHI disclosures by type, recipient, and minimum necessary adherence'
AS
SELECT
    d.DISCLOSURE_DATE,
    d.DISCLOSURE_TYPE,
    d.RECIPIENT_TYPE,
    d.PHI_CATEGORY,
    d.MINIMUM_NECESSARY,
    d.AUTHORIZATION_TYPE,
    d.HIPAA_EXCEPTION_APPLIED,
    p.CONSENT_ON_FILE,
    p.CONSENT_DATE
FROM CDGC_DEMO.CLINICAL_CORE.PHI_DISCLOSURE_LOG d
JOIN CDGC_DEMO.CLINICAL_CORE.PATIENT_DEMOGRAPHICS p ON d.PATIENT_ID = p.PATIENT_ID;


-- ============================================================
-- LINEAGE VIEWS — MODEL_REGISTRY
-- MCC parses the SQL to auto-generate lineage:
--   TRAINING_DATA tables → MODEL_REGISTRY pipeline views
-- ============================================================

CREATE OR REPLACE VIEW CDGC_DEMO.MODEL_REGISTRY.V_SEPSIS_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: SEPSIS_RISK_FEATURES → SEPSIS_RISK_IO'
AS
SELECT
    sf.PATIENT_ID,
    sf.ENCOUNTER_ID,
    sf.HEART_RATE,
    sf.RESPIRATORY_RATE,
    sf.TEMPERATURE_C,
    sf.SYSTOLIC_BP,
    sf.WBC_COUNT,
    sf.LACTATE_LEVEL,
    sf.SOFA_SCORE,
    sf.VASOPRESSOR_USE,
    sf.MECHANICAL_VENTILATION,
    sf.AGE_AT_ENCOUNTER
FROM CDGC_DEMO.TRAINING_DATA.SEPSIS_RISK_FEATURES sf
WHERE sf.DATA_PARTITION = 'TRAIN'
  AND sf.HEART_RATE IS NOT NULL
  AND sf.LACTATE_LEVEL IS NOT NULL;

CREATE OR REPLACE VIEW CDGC_DEMO.MODEL_REGISTRY.V_NLP_TRAINING_PIPELINE
  COMMENT = 'MCC lineage view: NLP_DOCUMENT_CORPUS → CLINICAL_NLP_IO'
AS
SELECT
    nc.DOCUMENT_ID,
    nc.PATIENT_ID,
    nc.DOCUMENT_TYPE,
    nc.NOTE_TEXT,
    nc.ICD10_MENTIONS,
    nc.LOINC_MENTIONS,
    nc.MEDICATION_MENTIONS,
    nc.WORD_COUNT
FROM CDGC_DEMO.TRAINING_DATA.NLP_DOCUMENT_CORPUS nc
WHERE nc.DATA_PARTITION = 'TRAIN'
  AND nc.PHI_SCRUBBED = TRUE
  AND nc.WORD_COUNT >= 10;


-- ============================================================
-- VERIFICATION
-- Run these after execution to confirm everything exists
-- ============================================================

SHOW TABLES IN SCHEMA CDGC_DEMO.CLINICAL_CORE;
SHOW TABLES IN SCHEMA CDGC_DEMO.TRAINING_DATA;
SHOW TABLES IN SCHEMA CDGC_DEMO.MODEL_REGISTRY;

SHOW VIEWS IN SCHEMA CDGC_DEMO.CLINICAL_CORE;
SHOW VIEWS IN SCHEMA CDGC_DEMO.MODEL_REGISTRY;

-- Expected:
--   CLINICAL_CORE:   6 tables (PATIENT_DEMOGRAPHICS, CLINICAL_ENCOUNTERS,
--                              LAB_RESULTS, MEDICATION_ORDERS,
--                              IMMUNIZATION_RECORDS, SDOH_ASSESSMENTS,
--                              PHI_DISCLOSURE_LOG)
--                    3 views  (PATIENT_CLINICAL_SUMMARY,
--                              HIGH_RISK_PATIENT_REPORT,
--                              PHI_DISCLOSURE_SUMMARY)
--   TRAINING_DATA:   2 tables (SEPSIS_RISK_FEATURES, NLP_DOCUMENT_CORPUS)
--   MODEL_REGISTRY:  2 tables (SEPSIS_RISK_IO, CLINICAL_NLP_IO)
--                    2 views  (V_SEPSIS_TRAINING_PIPELINE, V_NLP_TRAINING_PIPELINE)
