# Database Performance & Indexing Benchmark

## 1. Objective and Methodology
We evaluate query execution performance on PostgreSQL using `EXPLAIN (ANALYZE, BUFFERS)` before and after creating indexes and materialised views, following the optimization guidelines from Course 3.

---

## 2. Benchmark Summary Table

| Test | Target Query / Use Case | Before Optimization | After Optimization | Speedup | Plan Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T1** | Client payment history lookup (`paiements`) | **11.66 ms** | **2.16 ms** | **~5.4x** | `Seq Scan` -> `Bitmap Index Scan` |
| **T2** | Client delay lookup on Materialised View (`echeances`) | **16.71 ms** | **0.43 ms** | **~38.8x** | `Seq Scan` -> `Index Only Scan` (Heap Fetches: 0) |
| **T3a** | Severe delay count (`jours_retard > 30`, ~0.36% rows) | **13.56 ms** | **0.26 ms** | **~52.1x** | `Seq Scan` -> `Index Only Scan` |
| **T3b** | Frequent delay count (`jours_retard > -20`, >90% rows) | **19.89 ms** | **13.84 ms** | **~1.4x** | Optimizer relies on `Seq Scan` (Selectivity rule confirmed) |
| **T4** | Expression rewrite (`jours_retard` vs calculated diff) | **13.56 ms** | **0.26 ms** | **~52.1x** | Enables index usage by querying precalculated column |

---

## 3. In-Depth Technical Analysis

### T1: Foreign Key Indexing (`idx_paiements_client`)
- **Before:** Scanning all 45,000+ rows required 448 shared memory hits (`Seq Scan`).
- **After:** The index directly points to the 20 payments belonging to the client (`Bitmap Index Scan`), reducing execution time from **11.66 ms to 2.16 ms**.

### T2: Covering Index & Index Only Scan (`idx_echeances_client_cov`)
- By adding `INCLUDE (jours_retard)` to `(client_id)`, PostgreSQL reads the required metric straight from the index tree.
- **Result:** `Heap Fetches = 0`. The database engine does not even touch the table on disk, resulting in a **38x performance boost** (**0.43 ms**).

### T3 & T4: Selectivity Principle & Query Rewriting
- **High selectivity (< 1%):** For `jours_retard > 30` (only 163 rows out of 45,296), `idx_echeances_retard` delivers instant results in **0.26 ms**.
- **Low selectivity (> 90%):** For `jours_retard > -20`, reading through an index would cause random I/O thrashing. The cost-based optimizer correctly chooses a sequential scan.
- **Rewriting rule:** Using an expression like `(jours_dernier_paiement - jours_prevu) > 30` blocks index usage. Using the materialized column `jours_retard` resolves this.

---

## 4. Index Storage Overhead
Storage footprint retrieved via `pg_relation_size`:
- `echeances` (Materialised View): 3,704 kB
- `paiements` (Base Table): 3,552 kB
- `idx_echeances_client_cov`: 1,008 kB
- `idx_paiements_client`: 360 kB
- `idx_echeances_retard`: 336 kB

**Trade-off conclusion:** Adding ~1.7 MB of secondary indexes is negligible in disk cost, while yielding between **5x to 50x speedups** for dashboard analytical queries.