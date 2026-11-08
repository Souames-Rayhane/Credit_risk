import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
FILES = ["application_train", "previous_application", "installments_payments"]

def count_rows(path, chunksize=500_000):
    total = 0
    for chunk in pd.read_csv(path, usecols=[0], chunksize=chunksize):
        total += len(chunk)
    return total

for name in FILES:
    path = RAW / f"{name}.csv"
    head = pd.read_csv(path, nrows=5)
    print(f"\n=== {name} ===")
    print("Colonnes :", len(head.columns))
    print(list(head.columns))
    print("Nombre de lignes :", count_rows(path))