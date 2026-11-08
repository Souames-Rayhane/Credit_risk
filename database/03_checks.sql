SET search_path TO credit, public;

SELECT 'clients'  AS controle, COUNT(*) AS valeur, 1300  AS attendu FROM clients
UNION ALL SELECT 'clients_target1', COUNT(*) FILTER (WHERE target = 1), 105 FROM clients
UNION ALL SELECT 'paiements', COUNT(*), 48000 FROM paiements
UNION ALL SELECT 'echeances', COUNT(*), 45296 FROM echeances
UNION ALL SELECT 'echeances_fractionnees', COUNT(*) FILTER (WHERE paiement_fractionne), 2371 FROM echeances
UNION ALL SELECT 'clients_avec_historique', COUNT(DISTINCT client_id), 1233 FROM echeances
UNION ALL SELECT 'a_temps_ou_en_avance', COUNT(*) FILTER (WHERE jours_retard <= 0), 41259 FROM echeances
UNION ALL SELECT 'retard_1_7', COUNT(*) FILTER (WHERE jours_retard BETWEEN 1 AND 7), 2727 FROM echeances
UNION ALL SELECT 'retard_8_30', COUNT(*) FILTER (WHERE jours_retard BETWEEN 8 AND 30), 1139 FROM echeances
UNION ALL SELECT 'retard_gt_30', COUNT(*) FILTER (WHERE jours_retard > 30), 163 FROM echeances
UNION ALL SELECT 'sans_date_paiement', COUNT(*) FILTER (WHERE jours_retard IS NULL), 8 FROM echeances
UNION ALL SELECT 'insuffisantes', COUNT(*) FILTER (WHERE montant_du - COALESCE(total_paye, 0) > 1), 23 FROM echeances
UNION ALL SELECT 'credits', COUNT(*), 6227 FROM credits
UNION ALL SELECT 'credits_installments_only', COUNT(*) FILTER (WHERE credit_source = 'installments_only'), 120 FROM credits
UNION ALL SELECT 'sans_emploi_flag', COUNT(*) FILTER (WHERE no_employment_flag), NULL FROM clients;

-- Orphelins (doit renvoyer 0)
SELECT COUNT(*) AS paiements_sans_credit
FROM paiements p LEFT JOIN credits c USING (credit_id)
WHERE c.credit_id IS NULL;