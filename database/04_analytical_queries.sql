-- 04_analytical_queries.sql : requêtes analytiques 
-- on a utiliser: retard en jours = dernier paiement - date prévue (positif veut dire = en retard)
-- les taux de retard sont calculees sur les echeances ayant une date de paiement.
-- les dates sont relatives a la demande actuelle de chaque client (pas de calendrier en commun)
SET search_path TO credit, public;
--------remarrrqq: Q1,Q2,Q4,Q5:reponde a la question A,,,
----------Q6b: repond a B
-----------Q7: repond C
------Q8: repond D
------------------------------------------------------------------------------
-- Q0. Vue de base : une ligne par échéance, enrichie (crédit + client + tranche)
------------------------------------------------------------------------------
--une ligne par echeance avec credit, client et tranche de retard
CREATE OR REPLACE VIEW v_echeances_detail AS
SELECT e.credit_id, e.client_id, e.instalment_number,
       e.jours_prevu, e.jours_dernier_paiement, e.jours_retard,
       e.montant_du, e.total_paye, e.paiement_fractionne,
       c.credit_source, c.portfolio, c.contract_status,
       cl.target, cl.region_rating,
       CASE WHEN e.jours_retard IS NULL THEN '0 - sans date de paiement'
            WHEN e.jours_retard <= 0    THEN '1 - a temps / en avance'
            WHEN e.jours_retard <= 7    THEN '2 - 1 a 7 jours'
            WHEN e.jours_retard <= 30   THEN '3 - 8 a 30 jours'
            ELSE                             '4 - plus de 30 jours'
       END AS tranche_retard
FROM echeances e
JOIN credits c  ON c.credit_id = e.credit_id
JOIN clients cl ON cl.client_id = e.client_id;

------------------------------------------------------------------------------
-- Q1_ KPI globaux (question A, descriptif)(les taux de rtards avc date de paiment)
------------------------------------------------------------------------------
SELECT COUNT(*)                                   AS nb_echeances,
       COUNT(jours_retard)                        AS nb_avec_date_paiement,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 0)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 7)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_7j_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 30)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_30j_pct
FROM v_echeances_detail;
-- we should hve : 45296 , 45288 , 8.90 , 2.87 , 0.36 selon une petite analyse qu'on a faite lors de la creation de l bdd

------------------------------------------------------------------------------
-- Q2. Retards par source de credit et portefeuille, avec classement (question A)
------------------------------------------------------------------------------
WITH aggregated_produits AS (
  SELECT credit_source,
         COALESCE(portfolio, '(non documente)')            AS portefeuille,
         COUNT(jours_retard)                               AS nb_echeances,
         COUNT(*) FILTER (WHERE jours_retard > 0)          AS nb_retards,
         COUNT(*) FILTER (WHERE jours_retard > 7)          AS nb_retards_7j
  FROM v_echeances_detail
  GROUP BY credit_source, COALESCE(portfolio, '(non documente)')
)
SELECT credit_source, portefeuille, nb_echeances,
       ROUND(100.0 * nb_retards / nb_echeances, 2)         AS taux_retard_pct,
       ROUND(100.0 * nb_retards_7j / nb_echeances, 2)      AS taux_retard_7j_pct,
       RANK() OVER (ORDER BY nb_retards_7j::numeric / nb_echeances DESC) AS rang
FROM aggregated_produits
WHERE nb_echeances >= 100          -- rgle d'affichage pas de taux sur de petit effectiff
ORDER BY rang;

------------------------------------------------------------------------------
-- Q3. Retards par zone regionale (question A)
------------------------------------------------------------------------------
SELECT region_rating                                       AS zone,
       COUNT(DISTINCT client_id)                           AS nb_clients,
       COUNT(jours_retard)                                 AS nb_echeances,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 0)
             / NULLIF(COUNT(jours_retard), 0), 2)          AS taux_retard_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 7)
             / NULLIF(COUNT(jours_retard), 0), 2)          AS taux_retard_7j_pct
FROM v_echeances_detail
GROUP BY region_rating
ORDER BY region_rating;

------------------------------------------------------------------------------
-- Q4. Repartition par tranche de retard, avec part en %
------------------------------------------------------------------------------
SELECT tranche_retard,
       COUNT(*)                                            AS nb_echeances,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS part_pct
FROM v_echeances_detail
GROUP BY tranche_retard
ORDER BY tranche_retard;
-- normalement: 8 | 41259 | 2727 | 1139 | 163

------------------------------------------------------------------------------
-- Q10 :( Pivot source × portefeuille × tranche, avec sous-totaux (ROLLUP + GROUPINng)
------------------------------------------------------------------------------
SELECT CASE WHEN GROUPING(credit_source) = 1 THEN 'TOTAL' ELSE credit_source END AS source_credit,
       CASE WHEN GROUPING(portfolio) = 1 THEN 'Tous portefeuilles'
            ELSE COALESCE(portfolio, '(non documente)') END                      AS portefeuille,
       COUNT(*)                                            AS nb_echeances,
       COUNT(*) FILTER (WHERE jours_retard <= 0)           AS a_temps,
       COUNT(*) FILTER (WHERE jours_retard BETWEEN 1 AND 7)  AS retard_1_7j,
       COUNT(*) FILTER (WHERE jours_retard BETWEEN 8 AND 30) AS retard_8_30j,
       COUNT(*) FILTER (WHERE jours_retard > 30)           AS retard_plus_30j
FROM v_echeances_detail
GROUP BY ROLLUP (credit_source, portfolio)
ORDER BY GROUPING(credit_source), credit_source, GROUPING(portfolio), portfolio;

---avec ça on a repondu sur A

------------------------------------------------------------------------------
-- Q5a. Distribution du ratio annuiteee / revenu (pour verifier les bandes de Q5b )
---celle ci c juste pour nous pour comprendre Q5b
------------------------------------------------------------------------------
SELECT ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p10,
       ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p25,
       ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS mediane,
       ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p75,
       ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p90
FROM clients;

------------------------------------------------------------------------------
-- Q5b. Taux de difficultee (TARGET) par profil, comparee au taux global (question B)
------------------------------------------------------------------------------
WITH base_clients AS (
  SELECT client_id, target, region_rating, income_type, education_type,
         annuity_amount / NULLIF(income_total, 0)  AS ratio_annuite_revenu,
         NTILE(4) OVER (ORDER BY income_total)     AS quartile_revenu,
         CASE WHEN ext_source_2 IS NULL THEN 'Score inconnu'
              WHEN ext_source_2 < 0.3   THEN '< 0.3'
              WHEN ext_source_2 < 0.5   THEN '0.3 - 0.5'
              WHEN ext_source_2 < 0.7   THEN '0.5 - 0.7'
              ELSE '>= 0.7' END                    AS bande_score
  FROM clients
),
enriched_clients AS (
  SELECT *,
         CASE WHEN ratio_annuite_revenu IS NULL THEN 'Inconnu'
              WHEN ratio_annuite_revenu < 0.10  THEN '< 10 %'
              WHEN ratio_annuite_revenu < 0.20  THEN '10 - 20 %'
              ELSE '>= 20 %' END                   AS bande_ratio
  FROM base_clients
),
segments AS (
  SELECT 'Zone regionale' AS dimension, region_rating::text AS segment, target FROM enriched_clients
  UNION ALL SELECT 'Type de revenu',          income_type,    target FROM enriched_clients
  UNION ALL SELECT 'Education',               education_type, target FROM enriched_clients
  UNION ALL SELECT 'Quartile de revenu',      'Q' || quartile_revenu, target FROM enriched_clients
  UNION ALL SELECT 'Ratio annuite / revenu',  bande_ratio,    target FROM enriched_clients
  UNION ALL SELECT 'Score externe',           bande_score,    target FROM enriched_clients
)
SELECT dimension, segment,
       COUNT(*)                                  AS n_clients,
       SUM(target)                               AS nb_difficulte,
       ROUND(100.0 * AVG(target), 2)             AS taux_difficulte_pct,
       ROUND(100.0 * (AVG(target) - (SELECT AVG(target) FROM clients)), 2) AS ecart_vs_global_pts
FROM segments
GROUP BY dimension, segment
HAVING COUNT(*) >= 30                            -- règle d'affichage du scope
ORDER BY dimension, taux_difficulte_pct DESC;


------------------------------------------------------------------------------
-- Q7: qui repond a "C" Un retard passee esq il annonce une difficulte actuelle ? (question C)
------------------------------------------------------------------------------
WITH client_hist AS (
  SELECT client_id, MAX(jours_retard) AS max_retard
  FROM echeances
  GROUP BY client_id
),
enriched_clients AS (
  SELECT cl.client_id, cl.target,
         CASE WHEN h.max_retard IS NULL THEN 'Sans historique'
              WHEN h.max_retard > 7     THEN 'Retard > 7 j'
              ELSE 'Pas de retard > 7 j' END AS groupe
  FROM clients cl
  LEFT JOIN client_hist h ON h.client_id = cl.client_id
)
SELECT groupe,
       COUNT(*)                         AS n_clients,
       SUM(target)                      AS nb_difficulte,
       ROUND(100.0 * AVG(target), 2)    AS taux_difficulte_pct,
       ROUND(AVG(target) FILTER (WHERE TRUE)
             / NULLIF((SELECT AVG(target) FROM enriched_clients
                       WHERE groupe = 'Pas de retard > 7 j'), 0), 2) AS rapport_vs_reference
FROM enriched_clients
GROUP BY groupe
ORDER BY groupe;
--  Pas de retard 901 | 64 | 7.10 ; setard > 7 j 332 | 38 | 11.45 (rapport ≈ 1.61) ; sans historique 67 | 3




------------------------------------------------------------------------------
-- Q11 repon a D ;; Score d'alerte simple (question D) : donne de 0 a three3
--      +1 retard > 7 j dans l'historique ; +1 ratio annuitee/revenu dans le quart sup ;
--      +1 score externe dans le quart inf.
---------------------------------------------------------------------------
WITH client_hist AS (
  SELECT client_id, MAX(jours_retard) AS max_retard
  FROM echeances
  GROUP BY client_id
),
base AS (
  SELECT cl.client_id, cl.target, cl.ext_source_2,
         cl.annuity_amount / NULLIF(cl.income_total, 0) AS ratio,
         h.max_retard
  FROM clients cl
  LEFT JOIN client_hist h ON h.client_id = cl.client_id
),
seuils AS (
  SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ratio)        AS q3_ratio,
         PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ext_source_2) AS q1_score
  FROM base
),
scored_clients AS (
  SELECT b.client_id, b.target,
         COALESCE((b.max_retard > 7)::int, 0)
       + COALESCE((b.ratio > s.q3_ratio)::int, 0)
       + COALESCE((b.ext_source_2 < s.q1_score)::int, 0) AS score_alerte
  FROM base b
  CROSS JOIN seuils s
)
SELECT score_alerte,
       COUNT(*)                         AS n_clients,
       SUM(target)                      AS nb_difficulte,
       ROUND(100.0 * AVG(target), 2)    AS taux_difficulte_pct
FROM scored_clients
GROUP BY score_alerte
ORDER BY score_alerte;

