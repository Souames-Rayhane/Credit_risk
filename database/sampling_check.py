import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
SEED = 42
N_MAX = 4000

app = pd.read_csv(
    RAW / "application_train.csv",
    usecols=["SK_ID_CURR", "TARGET", "NAME_INCOME_TYPE", "DAYS_EMPLOYED"],
)

# --- 1) DAYS_EMPLOYED = 365243 : qui sont ces clients ? (population entière)
sent = app[app["DAYS_EMPLOYED"] == 365243]
print("Clients avec DAYS_EMPLOYED = 365243 :", len(sent))
print(sent["NAME_INCOME_TYPE"].value_counts().head(5))
print("TARGET moyen (code 365243) :", round(sent["TARGET"].mean() * 100, 2), "%")
print("TARGET moyen (autres)      :",
      round(app.loc[app["DAYS_EMPLOYED"] != 365243, "TARGET"].mean() * 100, 2), "%")

# --- 2) Échantillon stratifié sur TARGET
frac = N_MAX / len(app)
clients = app.groupby("TARGET", group_keys=False).sample(frac=frac, random_state=SEED)
print("\nÉchantillon :", len(clients), "clients, TARGET=1 :",
      round(clients["TARGET"].mean() * 100, 2), "%")
ids = set(clients["SK_ID_CURR"])

# --- 3) Leurs échéances
parts = []
for chunk in pd.read_csv(RAW / "installments_payments.csv", chunksize=1_000_000):
    parts.append(chunk[chunk["SK_ID_CURR"].isin(ids)])
inst = pd.concat(parts, ignore_index=True)
inst["jours_retard"] = inst["DAYS_ENTRY_PAYMENT"] - inst["DAYS_INSTALMENT"]
inst["manque"] = inst["AMT_INSTALMENT"] - inst["AMT_PAYMENT"]

# --- 4) Combien de lignes selon le nombre de clients et la fenêtre ?
print("\nLignes selon nombre de clients et fenêtre (jours avant la demande) :")
rows = []
for n in [1500, 2000, 3000, 4000]:
    sous = clients.sample(n=n, random_state=SEED)
    sous_ids = set(sous["SK_ID_CURR"])
    for fen in [None, 730, 365]:
        d = inst[inst["SK_ID_CURR"].isin(sous_ids)]
        if fen is not None:
            d = d[d["DAYS_INSTALMENT"] >= -fen]
        rows.append({
            "clients": n,
            "fenetre_jours": fen if fen else "tout",
            "lignes": len(d),
            "clients_target1": int(sous["TARGET"].sum()),
            "lignes_retard_gt7": int((d["jours_retard"] > 7).sum()),
            "lignes_retard_gt30": int((d["jours_retard"] > 30).sum()),
        })
print(pd.DataFrame(rows).to_string(index=False))

# --- 5) Doublons d'échéances (sur tout l'échantillon)
cle = ["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"]
grp = inst.groupby(cle).agg(
    n_lignes=("AMT_PAYMENT", "size"),
    n_versions=("NUM_INSTALMENT_VERSION", "nunique"),
    n_dates_paiement=("DAYS_ENTRY_PAYMENT", "nunique"),
).reset_index()
dup = grp[grp["n_lignes"] > 1]
print("\nÉchéances avec plusieurs lignes :", len(dup), "sur", len(grp))
print("  dont plusieurs versions de calendrier :", int((dup["n_versions"] > 1).sum()))
print("  dont plusieurs dates de paiement      :", int((dup["n_dates_paiement"] > 1).sum()))

# --- 6) Tranches de retard
bins = [-10**6, 0, 7, 30, 10**6]
labels = ["A temps / en avance", "1-7 j", "8-30 j", "> 30 j"]
inst["tranche"] = pd.cut(inst["jours_retard"], bins=bins, labels=labels)
print("\nTranches de retard (toutes lignes) :")
print(inst["tranche"].value_counts(dropna=False).sort_index())

# --- 7) Paiements insuffisants : arrondis ou vrais manques ?
print("\nDistribution du manque (lignes avec manque > 0) :")
print(inst.loc[inst["manque"] > 0, "manque"].describe(percentiles=[.25, .5, .75, .9]))
print("Manque entre 0 et 1 :", int(((inst["manque"] > 0) & (inst["manque"] <= 1)).sum()))