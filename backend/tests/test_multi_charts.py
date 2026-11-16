from pathlib import Path
import pytest
from pptx import Presentation
from app.models import ReportOptions
from app.orchestrator import run_report

SAMPLE = Path(__file__).resolve().parents[2] / 'samples' / 'finance_reports.csv'

@pytest.mark.parametrize('report_type,indicator', [('plan_fact',''),('expenses',''),('dynamics','Выручка,Аренда')])
def test_separate_charts(tmp_path, report_type, indicator):
    out = tmp_path / 'report.pptx'
    run_report(ReportOptions('2026-08' if report_type == 'dynamics' else '2026-10', 'Проверка', report_type=report_type,
                             period_end='2026-10', indicator=indicator,
                             one_chart_per_slide=True), out, SAMPLE)
    prs = Presentation(out)
    charts = [shape for slide in prs.slides for shape in slide.shapes if shape.has_chart]
    assert len(charts) >= 2
    assert len(charts) == len(prs.slides) - 1
