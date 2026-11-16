from pathlib import Path
import logging
from .models import ReportOptions, ReportResult
from .loader import load_file, load_sql
from .validation import validate_and_prepare
from .report_types import report_data
from .content import prepare_slides
from .generator import generate

logger = logging.getLogger(__name__)

def run_report(options: ReportOptions, destination: Path, source_file: Path | None = None,
               database_url: str | None = None, query: str | None = None) -> ReportResult:
    if source_file:
        raw = load_file(source_file)
    elif database_url and query:
        raw = load_sql(database_url, query)
    else:
        raise ValueError("Не указан источник данных")
    prepared = validate_and_prepare(raw)
    if options.slides_config is not None:
        from .content import SlideContent
        if not isinstance(options.slides_config, list) or not 1 <= len(options.slides_config) <= 30:
            raise ValueError("Укажите от 1 до 30 слайдов")
        content = []
        for i, cfg in enumerate(options.slides_config, 1):
            if not isinstance(cfg, dict):
                raise ValueError("Некорректные настройки слайда")
            report_type = cfg.get("report_type", "plan_fact")
            period = cfg.get("period", "")
            period_end = cfg.get("period_end", "")
            indicator = str(cfg.get("indicator", "")).strip()
            chart_type = cfg.get("chart_type", "column")
            if chart_type not in {"column", "bar", "line"}:
                raise ValueError(f"Слайд {i}: неизвестный тип диаграммы")
            summary = report_data(prepared, report_type, period, period_end, indicator)
            if report_type == "plan_fact" and indicator:
                summary = summary.loc[summary.category == indicator]
                if summary.empty:
                    raise ValueError(f"Слайд {i}: показатель «{indicator}» не найден за {period}")
            if report_type == "expenses" and indicator:
                summary = summary.loc[summary.category == indicator]
                if summary.empty:
                    raise ValueError(f"Слайд {i}: статья «{indicator}» не найдена за {period}")
            if len(summary) > 9:
                raise ValueError(f"Слайд {i}: больше 9 строк. Выберите конкретный показатель")
            default_title = f"{indicator or {'plan_fact': 'План и факт', 'dynamics': 'Динамика', 'expenses': 'Структура расходов'}[report_type]}: {period}"
            content.append(SlideContent(str(cfg.get("title") or default_title)[:120], summary,
                                        report_type, chart_type, report_type == "expenses" and bool(indicator)))
    elif options.one_chart_per_slide and options.report_type == "dynamics":
        from .content import SlideContent
        names = [name.strip() for name in options.indicator.split(",") if name.strip()]
        if not names:
            raise ValueError("Укажите хотя бы один показатель")
        content = []
        for name in dict.fromkeys(names):
            summary = report_data(prepared, options.report_type, options.period, options.period_end, name)
            content.append(SlideContent(f"Динамика: {name} ({options.period} — {options.period_end})", summary))
    else:
        summary = report_data(prepared, options.report_type, options.period, options.period_end, options.indicator)
        content = prepare_slides(summary, options.period, report_type=options.report_type,
                                 period_end=options.period_end, one_chart_per_slide=options.one_chart_per_slide)
    count = generate(content, destination, options.title, options.template, options.chart_type,
                     options.style, options.include_cover, options.subtitle, options.author, options.report_type,
                     options.one_chart_per_slide)
    logger.info("Сформирована презентация, слайдов: %s", count)
    return ReportResult(destination, count)
