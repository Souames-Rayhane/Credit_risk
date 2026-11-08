--- materialized views, indexes and optimization
SET search_path TO credit, public;

-- 1_ Index on Foreign Key client_id (Validated by test T1: 5.4 speedup)
CREATE INDEX IF NOT EXISTS idx_paiements_client 
ON paiements (client_id);

---- 2) Covering index for client delay queries (Validated by Test T2: 38x speedup via index Only scan)
CREATE INDEX IF NOT EXISTS idx_echeances_client_cov 
ON echeances (client_id) INCLUDE (jours_retard);

---3 index on severe delay filtering (Validated by Test T3a: 52x speedup on selective filters)
CREATE INDEX IF NOT EXISTS idx_echeances_retard 
ON echeances (jours_retard);

------- Update statistics for the cost-based optimizer
ANALYZE paiements;
ANALYZE echeances;