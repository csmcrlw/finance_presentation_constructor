"""Расчеты для различных управленческих отчетов."""
import re
import pandas as pd

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
REPORT_TYPES = {"plan_fact", "dynamics", "expenses"}

def report_data(frame: pd.DataFrame, report_type: str, start: str, end: str = "", indicator: str = "") -> pd.DataFrame:
    if report_type not in REPORT_TYPES:
        raise ValueError("Неизвестный тип отчета")
    if not PERIOD_RE.fullmatch(start) or (end and not PERIOD_RE.fullmatch(end)):
        raise ValueError("Период должен иметь формат ГГГГ-ММ")
    if report_type == "dynamics":
        if not end or end < start:
            raise ValueError("Для анализа динамики укажите корректный диапазон месяцев")
        if not indicator.strip():
            raise ValueError("Для анализа динамики укажите показатель (категорию)")
        data = frame.loc[frame.period.between(start, end) & (frame.category == indicator.strip())]
        if data.empty:
            raise ValueError("За выбранный диапазон записи не найдены")
        result = data.groupby("period", as_index=False, sort=True)[["plan", "fact"]].sum()
        result["change_pct"] = result["fact"].pct_change(fill_method=None) * 100
        return result
    data = frame.loc[frame.period == start]
    if data.empty:
        raise ValueError(f"За период {start} записи не найдены")
    if report_type == "expenses":
        data = data.loc[data.kind == "expense"]
        if data.empty:
            raise ValueError("Для отчета о расходах нужны строки с kind=expense")
        if (data.fact < 0).any():
            raise ValueError("Для структуры расходов укажите положительные значения fact")
        result = data.groupby("category", as_index=False, sort=True)[["fact"]].sum()
        total = result.fact.sum()
        if total <= 0:
            raise ValueError("Общая сумма расходов должна быть больше нуля")
        result["share_pct"] = result.fact / total * 100
        return result.sort_values("fact", ascending=False).reset_index(drop=True)
    from .calculations import calculate
    return calculate(frame, start)
