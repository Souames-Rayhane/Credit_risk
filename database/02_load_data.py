"""Charge un échantillon  de Home Credit dans PostgreSQL (schéma 'credit')."""
import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def get_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "credit_risk"),
    )
    return create_engine(url)


def to_db(df):
    """NaN / NA -> None pour que PostgreSQL reçoive des NULL."""
    return df.astype(object).where(df.notna(), None)


def build_clients(raw, n_clients, seed):
    cols = ["SK_ID_CURR", "TARGET", "NAME_CONTRACT_TYPE", "AMT_INCOME_TOTAL",
            "AMT_CREDIT", "AMT_ANNUITY", "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE",
            "OCCUPATION_TYPE", "DAYS_EMPLOYED", "EXT_SOURCE_2", "REGION_RATING_CLIENT"]
    app = pd.read_csv(raw / "application_train.csv", usecols=cols)
    sample = app.groupby("TARGET", group_keys=False).sample(
        frac=n_clients / len(app), random_state=seed)

    flag = sample["DAYS_EMPLOYED"] == 365243
    sample["no_employment_flag"] = flag
    sample["DAYS_EMPLOYED"] = sample["DAYS_EMPLOYED"].where(~flag).astype("Int64")

    clients = sample.rename(columns={
        "SK_ID_CURR": "client_id", "TARGET": "target",
        "NAME_CONTRACT_TYPE": "contract_type", "AMT_INCOME_TOTAL": "income_total",
        "AMT_CREDIT": "credit_amount", "AMT_ANNUITY": "annuity_amount",
        "NAME_INCOME_TYPE": "income_type", "NAME_EDUCATION_TYPE": "education_type",
        "OCCUPATION_TYPE": "occupation_type", "DAYS_EMPLOYED": "days_employed",
        "EXT_SOURCE_2": "ext_source_2", "REGION_RATING_CLIENT": "region_rating",
    }).sort_values("client_id").reset_index(drop=True)
    return clients


def build_credits(raw, ids):
    cols = ["SK_ID_PREV", "SK_ID_CURR", "NAME_CONTRACT_TYPE", "NAME_PORTFOLIO",
            "NAME_CONTRACT_STATUS", "AMT_APPLICATION", "AMT_CREDIT", "AMT_ANNUITY",
            "CNT_PAYMENT", "DAYS_DECISION"]
    prev = pd.read_csv(raw / "previous_application.csv", usecols=cols)
    prev = prev[prev["SK_ID_CURR"].isin(ids)].copy()
    prev["CNT_PAYMENT"] = prev["CNT_PAYMENT"].round().astype("Int64")
    prev["DAYS_DECISION"] = prev["DAYS_DECISION"].astype("Int64")
    return prev.rename(columns={
        "SK_ID_PREV": "credit_id", "SK_ID_CURR": "client_id",
        "NAME_CONTRACT_TYPE": "contract_type", "NAME_PORTFOLIO": "portfolio",
        "NAME_CONTRACT_STATUS": "contract_status", "AMT_APPLICATION": "amt_application",
        "AMT_CREDIT": "amt_credit", "AMT_ANNUITY": "amt_annuity",
        "CNT_PAYMENT": "term_months", "DAYS_DECISION": "days_decision",
    }).sort_values("credit_id").reset_index(drop=True)


def build_paiements(raw, ids):
    parts = []
    for chunk in pd.read_csv(raw / "installments_payments.csv", chunksize=1_000_000):
        parts.append(chunk[chunk["SK_ID_CURR"].isin(ids)])
    pay = pd.concat(parts, ignore_index=True)
    pay = pay.rename(columns={
        "SK_ID_PREV": "credit_id", "SK_ID_CURR": "client_id",
        "NUM_INSTALMENT_VERSION": "instalment_version",
        "NUM_INSTALMENT_NUMBER": "instalment_number",
        "DAYS_INSTALMENT": "days_instalment", "DAYS_ENTRY_PAYMENT": "days_entry_payment",
        "AMT_INSTALMENT": "amt_instalment", "AMT_PAYMENT": "amt_payment",
    })
    pay["days_entry_payment"] = pay["days_entry_payment"].round().astype("Int64")
    pay["days_instalment"] = pay["days_instalment"].round().astype("Int64")
    pay["instalment_version"] = pay["instalment_version"].round().astype("Int64")
    return pay.sort_values(["credit_id", "instalment_number", "instalment_version"]
                           ).reset_index(drop=True)



def add_missing_credits(credits, paiements):
    """Ajoute une fiche minimale pour les crédits connus seulement par leurs paiements."""
    credits = credits.copy()
    credits["credit_source"] = "previous_application"
    manquants = (paiements.loc[~paiements["credit_id"].isin(credits["credit_id"]),
                               ["credit_id", "client_id"]]
                 .drop_duplicates())
    if manquants["credit_id"].duplicated().any():
        raise SystemExit("Un crédit orphelin est rattaché à plusieurs clients : à analyser.")
    manquants["credit_source"] = "installments_only"
    credits = pd.concat([credits, manquants], ignore_index=True)
    return credits.sort_values("credit_id").reset_index(drop=True)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--n-clients", type=int, default=1300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    raw = Path(args.raw_dir)

    clients = build_clients(raw, args.n_clients, args.seed)
    ids = set(clients["client_id"])
    credits = build_credits(raw, ids)
    paiements = build_paiements(raw, ids)

    credits = add_missing_credits(credits, paiements)
    n_seuls = int((credits["credit_source"] == "installments_only").sum())
    print(f"Clients : {len(clients)} | TARGET=1 : {int(clients['target'].sum())}")
    print(f"Crédits : {len(credits)} (dont {n_seuls} connus seulement par leurs paiements)")
    print(f"Lignes de paiements : {len(paiements)}")

    orphelins = ~paiements["credit_id"].isin(credits["credit_id"])
    print("Paiements sans crédit correspondant :", int(orphelins.sum()))
    if orphelins.any():
        raise SystemExit("Orphelins détectés : envoyez ce résultat avant de continuer.")

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE credit.paiements, credit.credits, credit.clients "
                          "RESTART IDENTITY"))
        for name, df in [("clients", clients), ("credits", credits),
                         ("paiements", paiements)]:
            to_db(df).to_sql(name, conn, schema="credit", if_exists="append",
                             index=False, chunksize=2000, method="multi")
            print(f"Table {name} chargée.")
        conn.execute(text("REFRESH MATERIALIZED VIEW credit.echeances"))
        conn.execute(text("ANALYZE"))
    print("Chargement terminé.")


if __name__ == "__main__":
    main()