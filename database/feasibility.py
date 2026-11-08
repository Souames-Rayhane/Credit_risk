import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
SEED = 42
N_CLIENTS = 1200

# 1) Échantillon reproductible de clients
app = pd.read_csv(
    RAW / "application_train.csv",
    usecols=["SK_ID_CURR", "TARGET", "AMT_INCOME_TOTAL",
             "AMT_CREDIT", "AMT_ANNUITY", "DAYS_EMPLOYED"],
)
clients = app.sample(n=N_CLIENTS, random_state=SEED)
ids = set(clients["SK_ID_CURR"])

# 2) Leurs paiements d'échéances (lecture par blocs)
parts = []
for chunk in pd.read_csv(RAW / "installments_payments.csv", chunksize=1_000_000):
    parts.append(chunk[chunk["SK_ID_CURR"].isin(ids)])
inst = pd.concat(parts, ignore_index=True)

# 3) Indicateurs de base
inst["jours_retard"] = inst["DAYS_ENTRY_PAYMENT"] - inst["DAYS_INSTALMENT"]
inst["manque"] = inst["AMT_INSTALMENT"] - inst["AMT_PAYMENT"]

print("Clients échantillonnés :", len(clients))
print("Taux TARGET=1 (échantillon) :", round(clients["TARGET"].mean() * 100, 2), "%")
print("Taux TARGET=1 (population)  :", round(app["TARGET"].mean() * 100, 2), "%")
print("Lignes d'échéances :", len(inst))
print("Clients avec au moins une échéance :", inst["SK_ID_CURR"].nunique())
print("Crédits distincts (SK_ID_PREV) :", inst["SK_ID_PREV"].nunique())
print("Échéances distinctes (PREV, numéro) :",
      inst[["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"]].drop_duplicates().shape[0])

print("\nValeurs manquantes :")
print(inst.isna().sum())
print("\nRetard (jours) :")
print(inst["jours_retard"].describe())
print("\nPart en retard (> 0 j) :", round((inst["jours_retard"] > 0).mean() * 100, 2), "%")
print("Part en retard (> 30 j) :", round((inst["jours_retard"] > 30).mean() * 100, 2), "%")
print("Part de paiements insuffisants :", round((inst["manque"] > 0).mean() * 100, 2), "%")

# 4) Les retards passés sont-ils liés à la difficulté actuelle ?
par_client = inst.groupby("SK_ID_CURR").agg(
    max_retard=("jours_retard", "max")
).reset_index()
par_client["retard_30"] = par_client["max_retard"] > 30
check = clients.merge(par_client, on="SK_ID_CURR", how="left")
check["retard_30"] = check["retard_30"].fillna(False).astype(bool)
print("\nTARGET moyen selon un retard > 30 j dans l'historique :")
print(check.groupby("retard_30")["TARGET"].agg(["count", "mean"]))

print("\nDAYS_EMPLOYED == 365243 :",
      int((clients["DAYS_EMPLOYED"] == 365243).sum()), "clients")