from pathlib import Path
from pptx import Presentation
from app.models import ReportOptions
from app.orchestrator import run_report

SAMPLE = Path(__file__).resolve().parents[2] / 'samples' / 'finance_reports.csv'

def test_two_periods_separate_slides(tmp_path):
    slides = [
        {'title': 'Выручка: сентябрь', 'report_type': 'plan_fact', 'period': '2026-09', 'indicator': 'Выручка', 'chart_type': 'column'},
        {'title': 'Выручка: октябрь', 'report_type': 'plan_fact', 'period': '2026-10', 'indicator': 'Выручка', 'chart_type': 'column'},
    ]
    target = tmp_path / 'result.pptx'
    run_report(ReportOptions('2026-10', 'Два месяца', slides_config=slides), target, SAMPLE)
    prs = Presentation(target)
    assert len(prs.slides) == 3
    for slide in list(prs.slides)[1:]:
        assert sum(shape.has_chart for shape in slide.shapes) == 1
    assert 'сентябрь' in ' '.join(sh.text for sh in prs.slides[1].shapes if sh.has_text_frame)
    assert 'октябрь' in ' '.join(sh.text for sh in prs.slides[2].shapes if sh.has_text_frame)
