import pandas as pd

REQUIRED = ("period", "category", "plan", "fact")

def validate_and_prepare(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError("Отсутствуют обязательные столбцы: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("В таблице нет строк")
    for col in ("period", "category"):
        if frame[col].isna().any() or frame[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Столбец {col} содержит пустые значения")
        frame[col] = frame[col].astype(str).str.strip()
    for col in ("plan", "fact"):
        try:
            frame[col] = pd.to_numeric(frame[col], errors="raise")
        except (TypeError, ValueError):
            raise ValueError(f"Столбец {col} должен содержать числа") from None
        if frame[col].isna().any() or not frame[col].map(lambda v: bool(pd.notna(v) and abs(v) != float('inf'))).all():
            raise ValueError(f"Столбец {col} содержит пустые или бесконечные значения")
    if "kind" in frame.columns:
        frame["kind"] = frame["kind"].fillna("").astype(str).str.strip().str.lower()
    else:
        frame["kind"] = ""
    return frame.loc[:, [*REQUIRED, "kind"]]
