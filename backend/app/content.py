from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class SlideContent:
    title: str
    data: pd.DataFrame
    report_type: str = ""
    chart_type: str = ""
    one_chart_per_slide: bool = False

def prepare_slides(summary: pd.DataFrame, period: str, rows_per_slide: int = 9,
                   report_type: str = "plan_fact", period_end: str = "", one_chart_per_slide: bool = False) -> list[SlideContent]:
    labels = {"plan_fact": f"План и факт: {period}",
              "dynamics": f"Динамика показателей: {period} — {period_end}",
              "expenses": f"Структура расходов: {period}"}
    if one_chart_per_slide and report_type in {"plan_fact", "expenses"}:
        return [SlideContent(f"{row.category}: {period}", summary.iloc[i:i+1])
                for i, row in enumerate(summary.itertuples())]
    return [SlideContent(f"{labels[report_type]} (часть {i // rows_per_slide + 1})",
                         summary.iloc[i:i+rows_per_slide])
            for i in range(0, len(summary), rows_per_slide)]
