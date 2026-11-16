import pandas as pd

def calculate(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    selected = frame.loc[frame["period"].astype(str) == period]
    if selected.empty:
        raise ValueError(f"За период {period} записи не найдены")
    result = selected.groupby("category", as_index=False, sort=True)[["plan", "fact"]].sum()
    result["deviation"] = result["fact"] - result["plan"]
    result["deviation_pct"] = result.apply(
        lambda row: (row["deviation"] / abs(row["plan"]) * 100) if row["plan"] != 0 else None,
        axis=1,
    )
    return result
