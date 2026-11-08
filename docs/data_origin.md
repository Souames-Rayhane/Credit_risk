# Data Origin and Provenance

## 1. Data Source
- **Provider:** Home Credit Group via Kaggle
- **Competition:** Home Credit Default Risk
- **Source URL:** https://www.kaggle.com/competitions/home-credit-default-risk/data
- **Download Date:** March 2026

## 2. Downloaded Files in `data/raw/`
1. **`application_train.csv`**: Static records of loan applications, including borrower socio-demographic features, financial profile, and loan characteristics (central table).
2. **`previous_application.csv`**: Historical records of all prior loan applications submitted by the client to Home Credit (approved, refused, canceled, or unused).
3. **`installments_payments.csv`**: Detailed repayment schedule and actual payment records for each installment across past loans (used to track repayment delays / Days Past Due and unpaid amounts).
4. **`HomeCredit_columns_description.csv`**: Data dictionary containing definitions for each feature, including instructions on how to interpret relative dates.

## 3. Licensing and Terms of Use
- **License Type:** Kaggle Competition Official Rules.
- **Usage Rights & Restrictions:** The dataset is provided strictly for academic research, educational evaluation, and non-commercial purposes.
- **Confidentiality & Anonymization:** Data is fully anonymized by the data provider; clients and contracts are represented using synthetic hashed identifiers (`SK_ID_CURR`, `SK_ID_PREV`).

## 4. Technical Notes & Data Handling Rules
- **Volume & Scale:** The raw dataset is large, with `installments_payments.csv` containing over 13.6 million rows (~850 MB uncompressed).
- **Handling Constraint:** Raw files must not be opened using spreadsheet software (such as Microsoft Excel or LibreOffice Calc) to prevent row truncation and memory crashes.
- **Relative Dates:** Date features (prefixed with `DAYS_`, e.g., `DAYS_BIRTH`, `DAYS_DECISION`, `DAYS_INSTALMENT`, `DAYS_ENTRY_PAYMENT`) are recorded as negative integer offsets representing the number of days relative to the current application date (`0` = application date, `-30` = 30 days prior).
- **Processing Pipeline:** Filtering, sampling (to meet the workshop target of 40,000–50,000 rows for the main table), and database ingestion will be executed programmatically via Python scripts and loaded into PostgreSQL.