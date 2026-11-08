
DROP SCHEMA IF EXISTS credit CASCADE;
CREATE SCHEMA credit;
SET search_path TO credit, public;
--juste pour faciliter l'accée aux tables sans refaire a chaque fois credit.table 

CREATE TABLE clients (
  client_id           INTEGER PRIMARY KEY,                
  target              SMALLINT NOT NULL CHECK (target IN (0,1)),
  contract_type       TEXT,
  income_total        NUMERIC(14,2) CHECK (income_total >= 0),
  credit_amount       NUMERIC(14,2) CHECK (credit_amount >= 0),
  annuity_amount      NUMERIC(14,2) CHECK (annuity_amount >= 0),
  income_type         TEXT,
  education_type      TEXT,
  occupation_type     TEXT,
  days_employed       INTEGER,                           
  no_employment_flag  BOOLEAN NOT NULL DEFAULT FALSE,     -- vrai si 365243
  ext_source_2        NUMERIC(8,6) CHECK (ext_source_2 BETWEEN 0 AND 1),
  region_rating       SMALLINT CHECK (region_rating IN (1,2,3))
);

CREATE TABLE credits (
  credit_id        INTEGER PRIMARY KEY,                   -- SK_ID_PREV
  client_id        INTEGER NOT NULL REFERENCES clients(client_id),
  credit_source    TEXT NOT NULL DEFAULT 'previous_application'
                   CHECK (credit_source IN ('previous_application','installments_only')),
  contract_type    TEXT,
  portfolio        TEXT,
  contract_status  TEXT,
  amt_application  NUMERIC(14,2),
  amt_credit       NUMERIC(14,2),
  amt_annuity      NUMERIC(14,2),
  term_months      SMALLINT,
  days_decision    INTEGER                                -- relatif à la demande actuelle
);

CREATE TABLE paiements (                                  
  paiement_id         BIGSERIAL PRIMARY KEY,
  credit_id           INTEGER NOT NULL REFERENCES credits(credit_id),
  client_id           INTEGER NOT NULL REFERENCES clients(client_id),
  instalment_version  SMALLINT,
  instalment_number   SMALLINT NOT NULL,
  days_instalment     INTEGER NOT NULL,
  days_entry_payment  INTEGER,                            -- NULL quand paiement non renseignee
  amt_instalment      NUMERIC(14,2) NOT NULL,
  amt_payment         NUMERIC(14,2)
);


CREATE MATERIALIZED VIEW echeances AS
WITH raw_paiements AS (
  SELECT * FROM paiements
),
latest_version AS (
  SELECT DISTINCT ON (credit_id, instalment_number)
         credit_id, instalment_number, amt_instalment AS montant_du
  FROM raw_paiements
  ORDER BY credit_id, instalment_number, instalment_version DESC
),
aggregated_paiements AS (
  SELECT credit_id, client_id, instalment_number,
         MAX(days_instalment)               AS jours_prevu,
         MAX(days_entry_payment)            AS jours_dernier_paiement,
         COUNT(*)                           AS nb_lignes,
         COUNT(DISTINCT days_entry_payment) AS nb_dates_paiement,
         SUM(amt_payment)                   AS total_paye
  FROM raw_paiements
  GROUP BY credit_id, client_id, instalment_number
)
SELECT a.credit_id, a.client_id, a.instalment_number,
       a.jours_prevu, a.jours_dernier_paiement,
       l.montant_du, a.total_paye, a.nb_lignes,
       (a.nb_dates_paiement > 1)                AS paiement_fractionne,
       a.jours_dernier_paiement - a.jours_prevu AS jours_retard
FROM aggregated_paiements a
JOIN latest_version l USING (credit_id, instalment_number);