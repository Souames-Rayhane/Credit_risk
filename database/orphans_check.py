import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
SEED, N_CLIENTS = 42, 1300

# 1) Même échantillon de clients que le chargement
app = pd.read_csv(RAW / "application_train.csv", usecols=["SK_ID_CURR", "TARGET"])
clients = app.groupby("TARGET", group_keys=False).sample(
    frac=N_CLIENTS / len(app), random_state=SEED)
ids = set(clients["SK_ID_CURR"])

# 2) previous_application complet (tous clients) et partie de l'échantillon
prev_all = pd.read_csv(
    RAW / "previous_application.csv",
    usecols=["SK_ID_PREV", "SK_ID_CURR", "NAME_CONTRACT_TYPE",
             "NAME_CONTRACT_STATUS", "NAME_PORTFOLIO"],
)
print("SK_ID_PREV unique dans previous_application :", prev_all["SK_ID_PREV"].is_unique)
prev_sample = prev_all[prev_all["SK_ID_CURR"].isin(ids)]
print("Crédits de l'échantillon :", len(prev_sample))

# 3) Paiements de l'échantillon
parts = []
for ch in pd.read_csv(RAW / "installments_payments.csv", chunksize=1_000_000):
    parts.append(ch[ch["SK_ID_CURR"].isin(ids)])
pay = pd.concat(parts, ignore_index=True)
pay["jours_retard"] = pay["DAYS_ENTRY_PAYMENT"] - pay["DAYS_INSTALMENT"]

pay["dans_echantillon"] = pay["SK_ID_PREV"].isin(set(prev_sample["SK_ID_PREV"]))
pay["dans_global"] = pay["SK_ID_PREV"].isin(set(prev_all["SK_ID_PREV"]))
orph = pay[~pay["dans_echantillon"]]

print("\n=== Orphelins ===")
print("Lignes orphelines :", len(orph), "sur", len(pay))
print("Crédits distincts orphelins :", orph["SK_ID_PREV"].nunique())
print("Clients concernés :", orph["SK_ID_CURR"].nunique())

print("\n--- Hypothèse 1 : existent ailleurs dans previous_application ? ---")
print("Lignes orphelines dont le SK_ID_PREV existe dans previous_application :",
      int(orph["dans_global"].sum()))
print("Lignes orphelines dont le SK_ID_PREV n'existe nulle part :",
      int((~orph["dans_global"]).sum()))

autre = (orph[orph["dans_global"]]
         .merge(prev_all[["SK_ID_PREV", "SK_ID_CURR"]].rename(
             columns={"SK_ID_CURR": "CURR_dans_prev"}), on="SK_ID_PREV"))
print("Clients propriétaires dans previous_application différents du client du paiement :",
      int((autre["CURR_dans_prev"] != autre["SK_ID_CURR"]).sum()), "lignes sur", len(autre))

print("\n--- Nature des orphelins (version du calendrier, 0 = carte de crédit d'après la description) ---")
print("Part des lignes avec version 0 :")
print("  orphelins     :", round((orph["NUM_INSTALMENT_VERSION"] == 0).mean() * 100, 2), "%")
print("  non orphelins :", round((pay.loc[pay["dans_echantillon"], "NUM_INSTALMENT_VERSION"] == 0).mean() * 100, 2), "%")

print("\n--- Les orphelins ressemblent-ils aux autres ? ---")
for nom, d in [("orphelins", orph), ("non orphelins", pay[pay["dans_echantillon"]])]:
    d = d.dropna(subset=["jours_retard"])
    print(f"{nom:14s} lignes={len(d):6d}  retard>0 : {(d['jours_retard']>0).mean()*100:5.2f} %"
          f"  retard>7 : {(d['jours_retard']>7).mean()*100:5.2f} %"
          f"  retard moyen : {d['jours_retard'].mean():6.2f} j")

print("\n--- Crédits orphelins présents dans previous_application (si oui) : statut et portefeuille ---")
if autre["SK_ID_PREV"].nunique() > 0:
    detail = autre.drop_duplicates("SK_ID_PREV").merge(
        prev_all[["SK_ID_PREV", "NAME_CONTRACT_STATUS", "NAME_PORTFOLIO"]], on="SK_ID_PREV")
    print(detail["NAME_PORTFOLIO"].value_counts().head())
    print(detail["NAME_CONTRACT_STATUS"].value_counts().head())