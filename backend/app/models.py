from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ReportOptions:
    period: str
    title: str
    template: str = "standard"
    chart_type: str = "column"
    style: str = "corporate"
    include_cover: bool = True
    subtitle: str = ""
    author: str = ""
    report_type: str = "plan_fact"
    period_end: str = ""
    indicator: str = ""
    one_chart_per_slide: bool = False
    slides_config: list | None = None

@dataclass(frozen=True)
class ReportResult:
    path: Path
    slides: int
