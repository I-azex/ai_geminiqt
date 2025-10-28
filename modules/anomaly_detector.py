import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(df: pd.DataFrame):
    """Находит нетипичные транзакции по суммам."""
    model = IsolationForest(contamination=0.02, random_state=42)
    df["anomaly_flag"] = model.fit_predict(df[["amount"]])
    return df[df["anomaly_flag"] == -1]
