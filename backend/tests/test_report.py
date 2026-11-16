from pathlib import Path
import pandas as pd
import pytest
from pptx import Presentation
from app.validation import validate_and_prepare
from app.calculations import calculate
from app.models import ReportOptions
from app.orchestrator import run_report

def test_validation_missing_column():
    with pytest.raises(ValueError, match="обязательные"):
        validate_and_prepare(pd.DataFrame({"period": ["2026-10"]}))

def test_calculations():
    frame = pd.DataFrame({"period": ["2026-10", "2026-10"], "category": ["Выручка", "Выручка"],
                          "plan": [100, 50], "fact": [110, 60]})
    row = calculate(validate_and_prepare(frame), "2026-10").iloc[0]
    assert row["plan"] == 150
    assert row["fact"] == 170
    assert row["deviation"] == 20

def test_end_to_end(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("period,category,plan,fact\n2026-10,Revenue,100,120\n", encoding="utf-8")
    target = tmp_path / "report.pptx"
    result = run_report(ReportOptions("2026-10", "Тест"), target, source)
    assert result.slides == 2
    prs = Presentation(target)
    assert len(prs.slides) == 2
    assert any(shape.has_chart for shape in prs.slides[1].shapes)

@pytest.mark.parametrize("chart_type", ["column", "bar", "line"])
def test_chart_type_selection(tmp_path: Path, chart_type: str):
    from pptx.enum.chart import XL_CHART_TYPE
    source = tmp_path / "source.csv"
    source.write_text("period,category,plan,fact\n2026-10,Revenue,100,120\n", encoding="utf-8")
    target = tmp_path / "report.pptx"
    run_report(ReportOptions("2026-10", "Тест", chart_type=chart_type), target, source)
    prs = Presentation(target)
    chart = next(shape.chart for shape in prs.slides[1].shapes if shape.has_chart)
    assert chart.chart_type == {
        "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
        "bar": XL_CHART_TYPE.BAR_CLUSTERED,
        "line": XL_CHART_TYPE.LINE,
    }[chart_type]

def test_invalid_chart_type(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("period,category,plan,fact\n2026-10,Revenue,100,120\n", encoding="utf-8")
    with pytest.raises(ValueError, match="тип диаграммы"):
        run_report(ReportOptions("2026-10", "Тест", chart_type="pie"), tmp_path / "out.pptx", source)

def test_sql_dump_end_to_end(tmp_path: Path):
    source = tmp_path / "finance_reports.sql"
    source.write_text("CREATE TABLE finance (period TEXT, category TEXT, plan REAL, fact REAL);\n"
                      "INSERT INTO finance VALUES ('2026-10', 'Выручка', 100, 120);\n", encoding="utf-8")
    target = tmp_path / "out.pptx"
    result = run_report(ReportOptions("2026-10", "SQL-тест"), target, source)
    assert result.slides == 2
    assert len(Presentation(target).slides) == 2

def test_sql_dump_rejects_dangerous_statements(tmp_path: Path):
    from app.loader import load_file
    source = tmp_path / "unsafe.sql"
    source.write_text("CREATE TABLE finance (period TEXT, category TEXT, plan REAL, fact REAL);\n"
                      "DROP TABLE finance;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="разрешены только"):
        load_file(source)

@pytest.mark.parametrize('report_type,period,period_end,indicator,expected_chart', [
    ('plan_fact', '2026-10', '', '', 'COLUMN_CLUSTERED'),
    ('dynamics', '2026-08', '2026-10', 'Выручка', 'LINE'),
    ('expenses', '2026-10', '', '', 'PIE'),
])
def test_three_report_types(tmp_path, report_type, period, period_end, indicator, expected_chart):
    from pptx.enum.chart import XL_CHART_TYPE
    sample = Path(__file__).resolve().parents[2] / 'samples' / 'finance_reports.csv'
    dest = tmp_path / 'report.pptx'
    result = run_report(ReportOptions(period, 'Отчет', report_type=report_type,
                                      period_end=period_end, indicator=indicator), dest, sample)
    assert result.slides == 2
    presentation = Presentation(dest)
    chart = next(s.chart for s in presentation.slides[1].shapes if s.has_chart)
    assert chart.chart_type == getattr(XL_CHART_TYPE, expected_chart)


def test_dynamics_requires_indicator(tmp_path):
    sample = Path(__file__).resolve().parents[2] / 'samples' / 'finance_reports.csv'
    with pytest.raises(ValueError, match='показатель'):
        run_report(ReportOptions('2026-08', 'Отчет', report_type='dynamics', period_end='2026-10'),
                   tmp_path / 'out.pptx', sample)


def test_expenses_requires_kind(tmp_path):
    sample = tmp_path / 'simple.csv'
    sample.write_text('period,category,plan,fact\n2026-10,Аренда,10,12\n', encoding='utf-8')
    with pytest.raises(ValueError, match='kind=expense'):
        run_report(ReportOptions('2026-10', 'Отчет', report_type='expenses'), tmp_path / 'out.pptx', sample)
