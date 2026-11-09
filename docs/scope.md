# Project Scope: Bank Credit Risk & Repayment Delay Analysis

Workshop #01 – Applied Data Analytics & Decision Support (From SQL to Insight)
Team: Dalia Mezerna, Rayhane Souames – ESI, SID G1

## 1. Business problem

A lender's risk team needs to detect early which customer profiles, products
and regions show repayment delays that precede payment difficulties, in order to
adjust lending criteria and prioritise follow-up.

## 2. Audience

- General Executive: business value, key findings, recommendations.
- Head of IT: data model, architecture, implementation choices.

## 3. Decisions supported

1. Which customer segments and regions should be monitored more closely?(with analytical qst A and B)
2. Which customers should be contacted first (collection priorities)?(with analytical qst C and D)
3.  Which lending criteria (income, annuity-to-income ratio, external score)
   should be reviewed?(with analytical qst  B)
   

## 4. Analytical questions



 A  :Where are repayment delays concentrated (product type, region)? | Descriptive |
 B : Which customer profiles show the most payment difficulties? | Diagnostic |
 C  :Does a past repayment delay signal a current payment difficulty? | Diagnostic |
 D  :Which customers should be prioritised for follow-up (simple alert score)? | Prescriptive |
## partie analyse de données (which took a lot of time because the dataset is complicated)
## 5. Data

- Source: Kaggle "Home Credit Default Risk" (real, anonymised data).
- Tables used: application_train, previous_application, installments_payments.
- Sample: 1,300 customers, stratified on TARGET (seed 42), full payment history
  (about 48,000 payment rows). Sample size is a parameter of the loading script.
- Dates in the source are relative to each customer's current application
  (no common calendar), so time analysis is done in relative time.

## 6. Definitions

- Installment = (credit_id, installment_number). One installment can have
  several payment rows (split payments).
- Due amount = amount of the latest version of the installment calendar.
- Delay (days) = last payment day - scheduled day (positive = late).
- Delay bands: on time or early (<= 0), 1-7 days, 8-30 days, > 30 days.
- Customer alert signal: at least one installment late by more than 7 days.
- Payment difficulty = TARGET = 1 (defined by the source for the current loan;
  the exact thresholds X and Y are not specified).
- Underpayment: only defined at installment level (total paid vs. due amount).

## 7. KPIs (values from the sample check; to be recomputed in SQL)

| KPI | Answers | Definition | Sample value |
|-----|---------|------------|--------------|
| Late rate | A | late installments (> 0 d) / installments with a payment date | 8.9 % |
| Late > 7 days | A | same, threshold 7 days | 2.9 % |
| Late > 30 days | A | same, threshold 30 days | 0.36 % |
| Difficulty rate | B | mean of TARGET, always shown with the global rate | 8.08 % |
| Customers with a delay > 7 d | C | customers with such a delay / customers with history | 26.9 % |
| Risk ratio | C | difficulty rate with a delay > 7 d / without | about 1.6 |
| Priority customers | D | customers flagged by the alert score / all customers | to define |

## 8. Reporting rules

- Always show the sample size (n) next to a rate.
- Do not comment on segments with fewer than 30 customers or 10 events.
- Findings describe this sample and do not prove causality.

## 9. Out of scope (and why)

- Branches: not in the source data; the regional rating (REGION_RATING_CLIENT)
  is used as the geographic dimension.
- Loan vintages by calendar date: dates are relative, so no common calendar.
- Provisioning: no loss or default per credit in the data.
- Gender and age are not used for segmentation or alerting (fairness).

## 10. Known data issues

- DAYS_EMPLOYED = 365243 is a placeholder for "not employed" (mostly
  pensioners): set to NULL with a flag.
- Split payments and several calendar versions per installment.
- Very few delays above 30 days; few customers in difficulty (about 105),
  so fine segments are unstable.
- 120 credits (7.6 % of payment rows) appear in installments_payments with no
  record in previous_application. 86 % of their rows use calendar version 0,
  which the source documents as credit cards. They are kept and flagged
  credit_source = 'installments_only'. They behave differently (mean delay
  -0.5 days vs -9.4 days), so results are also shown by credit source.

## end of data analysis