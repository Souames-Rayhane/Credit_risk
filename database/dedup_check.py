import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
SEED, N_CLIENTS = 42, 1300

app = pd.read_csv(RAW / "application_train.csv", usecols=["SK_ID_CURR", "TARGET"])
clients = app.groupby("TARGET", group_keys=False).sample(
    frac=N_CLIENTS / len(app), random_state=SEED)
ids = set(clients["SK_ID_CURR"])

parts = []
for ch in pd.read_csv(RAW / "installments_payments.csv", chunksize=1_000_000):
    parts.append(ch[ch["SK_ID_CURR"].isin(ids)])
inst = pd.concat(parts, ignore_index=True)

print("Clients :", len(clients), "| TARGET=1 :", int(clients["TARGET"].sum()))
print("Lignes d'échéances :", len(inst))

cle = ["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"]
agg = inst.groupby(cle).agg(
    n_lignes=("AMT_PAYMENT", "size"),
    n_dates_prevues=("DAYS_INSTALMENT", "nunique"),
    n_montants_dus=("AMT_INSTALMENT", "nunique"),
    nb_dates_paiement=("DAYS_ENTRY_PAYMENT", "nunique"),
    du_max=("AMT_INSTALMENT", "max"),
    paye_total=("AMT_PAYMENT", "sum"),
).reset_index()

multi = agg[agg["n_lignes"] > 1]
print("\nÉchéances distinctes :", len(agg), "| avec plusieurs lignes :", len(multi))
print("  plusieurs dates prévues :", int((multi["n_dates_prevues"] > 1).sum()))
print("  plusieurs montants dus  :", int((multi["n_montants_dus"] > 1).sum()))
print("  plusieurs dates de paiement :", int((multi["nb_dates_paiement"] > 1).sum()))

frac = multi[multi["nb_dates_paiement"] > 1]
ratio = frac["paye_total"] / frac["du_max"]
print("\nPaiements fractionnés : total payé / montant dû")
print(ratio.describe())
print("  total payé >= 99 % du dû :", int((ratio >= 0.99).sum()), "sur", len(frac))

# Insuffisance : ligne par ligne vs niveau échéance
inst["manque_ligne"] = inst["AMT_INSTALMENT"] - inst["AMT_PAYMENT"]
srt = inst.sort_values(cle + ["NUM_INSTALMENT_VERSION"])
dern = srt.groupby(cle).agg(
    SK_ID_CURR=("SK_ID_CURR", "first"),
    du_ref=("AMT_INSTALMENT", "last"),
    due=("DAYS_INSTALMENT", "last"),
    derniere_paie=("DAYS_ENTRY_PAYMENT", "max"),
).reset_index()
dern = dern.merge(agg[cle + ["paye_total"]], on=cle)

print("\nInsuffisantes (manque > 1) :")
print("  ligne par ligne :", int((inst["manque_ligne"] > 1).sum()), "sur", len(inst))
print("  niveau échéance :", int(((dern["du_ref"] - dern["paye_total"]) > 1).sum()),
      "sur", len(dern))

# Retard au niveau échéance (dernier paiement - date prévue)
dern["retard"] = dern["derniere_paie"] - dern["due"]
bins = [-10**6, 0, 7, 30, 10**6]
labels = ["A temps / en avance", "1-7 j", "8-30 j", "> 30 j"]
dern["tranche"] = pd.cut(dern["retard"], bins=bins, labels=labels)
print("\nTranches (niveau échéance) :")
print(dern["tranche"].value_counts(dropna=False).sort_index())

# Signal client : retard > 7 jours dans l'historique -> TARGET
pc = dern.groupby("SK_ID_CURR")["retard"].max().reset_index(name="max_retard")
chk = clients.merge(pc, on="SK_ID_CURR", how="left")
chk["historique"] = chk["max_retard"].notna()
chk["retard_gt7"] = chk["max_retard"].gt(7)
print("\nClients sans historique :", int((~chk["historique"]).sum()))
print("\nTARGET selon retard > 7 j dans l'historique :")
print(chk[chk["historique"]].groupby("retard_gt7")["TARGET"].agg(["count", "sum", "mean"]))
