
-- 05_dashboard_views.sql : vues lues par le tableau de bord Streamlit
-- A executer APRES 04_analytical_queries.sql (qui cree v_echeances_detail).
-- Chaque vue reprend une requete de 04 a l'identique ; le dashboard fait seulement
-- SELECT * FROM <vue>, donc toute la logique reste dans PostgreSQL.
SET search_path TO credit, public;
 
------------------------------------------------------------------------------
-- Question A
------------------------------------------------------------------------------
-- Q1. KPI globaux
CREATE OR REPLACE VIEW v_dash_q1_kpi AS
SELECT COUNT(*)                                   AS nb_echeances,
       COUNT(jours_retard)                        AS nb_avec_date_paiement,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 0)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 7)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_7j_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE jours_retard > 30)
             / NULLIF(COUNT(jours_retard), 0), 2) AS taux_retard_30j_pct
FROM v_echeances_detail;
 
-- Taux de difficulte global (reference pour toutes les pages)
CREATE OR REPLACE VIEW v_dash_global AS
SELECT COUNT(*)                       AS n_clients,
       SUM(target)                    AS nb_difficulte,
       ROUND(100.0 * AVG(target), 2)  AS taux_difficulte_pct
FROM clients;
 
-- Q2. Retards par source et portefeuille, avec classement
CREATE OR REPLACE VIEW v_dash_q2_produits AS
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
WHERE nb_echeances >= 100;
 
-- Q4. Repartition par tranche de retard
CREATE OR REPLACE VIEW v_dash_q4_tranches AS
SELECT tranche_retard,
       COUNT(*)                                            AS nb_echeances,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS part_pct
FROM v_echeances_detail
GROUP BY tranche_retard;
 
-- Q5. Pivot source x portefeuille x tranche (ROLLUP)
-- Ajout par rapport a 04 : la colonne sans_date_paiement, pour que les tranches
-- additionnees retombent exactement sur nb_echeances.
CREATE OR REPLACE VIEW v_dash_q5_pivot AS
SELECT CASE WHEN GROUPING(credit_source) = 1 THEN 'TOTAL' ELSE credit_source END AS source_credit,
       CASE WHEN GROUPING(portfolio) = 1 THEN 'Tous portefeuilles'
            ELSE COALESCE(portfolio, '(non documente)') END                      AS portefeuille,
       COUNT(*)                                              AS nb_echeances,
       COUNT(*) FILTER (WHERE jours_retard <= 0)             AS a_temps,
       COUNT(*) FILTER (WHERE jours_retard BETWEEN 1 AND 7)  AS retard_1_7j,
       COUNT(*) FILTER (WHERE jours_retard BETWEEN 8 AND 30) AS retard_8_30j,
       COUNT(*) FILTER (WHERE jours_retard > 30)             AS retard_plus_30j,
       COUNT(*) FILTER (WHERE jours_retard IS NULL)          AS sans_date_paiement,
       GROUPING(credit_source)                               AS g_source,
       GROUPING(portfolio)                                   AS g_portefeuille
FROM v_echeances_detail
GROUP BY ROLLUP (credit_source, portfolio);
 
------------------------------------------------------------------------------
-- Question B
------------------------------------------------------------------------------
-- Q6a. Distribution du ratio annuite / revenu
CREATE OR REPLACE VIEW v_dash_q6a_ratio AS
SELECT ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p10,
       ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p25,
       ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS mediane,
       ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p75,
       ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY annuity_amount / NULLIF(income_total, 0))::numeric, 3) AS p90
FROM clients;
 
-- Q6b. Taux de difficulte par profil, compare au taux global
CREATE OR REPLACE VIEW v_dash_q6b_profils AS
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
       ROUND(100.0 * (AVG(target) - (SELECT AVG(target) FROM clients)), 2) AS ecart_vs_global_pts,
       CASE WHEN SUM(target) < 10 THEN 'indicatif (< 10 evenements)' ELSE 'ok' END AS fiabilite
FROM segments
GROUP BY dimension, segment
HAVING COUNT(*) >= 30;
 
------------------------------------------------------------------------------
-- Question C
------------------------------------------------------------------------------
-- Q7. Un retard passe annonce-t-il une difficulte actuelle ?
CREATE OR REPLACE VIEW v_dash_q7_historique AS
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
       ROUND(AVG(target)
             / NULLIF((SELECT AVG(target) FROM enriched_clients
                       WHERE groupe = 'Pas de retard > 7 j'), 0), 2) AS rapport_vs_reference
FROM enriched_clients
GROUP BY groupe;
 
------------------------------------------------------------------------------
-- Question D
------------------------------------------------------------------------------
-- Q8. Score d'alerte : +1 retard > 7 j dans l'historique ; +1 score externe dans le quart inferieur
CREATE OR REPLACE VIEW v_dash_q8_alerte AS
WITH client_hist AS (
  SELECT client_id, MAX(jours_retard) AS max_retard
  FROM echeances
  GROUP BY client_id
),
base AS (
  SELECT cl.client_id, cl.target, cl.ext_source_2, h.max_retard
  FROM clients cl
  LEFT JOIN client_hist h ON h.client_id = cl.client_id
),
seuils AS (
  SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ext_source_2) AS q1_score
  FROM base
),
scored_clients AS (
  SELECT b.client_id, b.target,
         COALESCE((b.max_retard > 7)::int, 0)
       + COALESCE((b.ext_source_2 < s.q1_score)::int, 0) AS score_alerte
  FROM base b
  CROSS JOIN seuils s
)
SELECT score_alerte,
       COUNT(*)                         AS n_clients,
       SUM(target)                      AS nb_difficulte,
       ROUND(100.0 * AVG(target), 2)    AS taux_difficulte_pct
FROM scored_clients
GROUP BY score_alerte;
 