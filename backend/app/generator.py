from pathlib import Path
import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from .content import SlideContent

CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE,
}

STYLES = {
    "corporate": {"background": "FFFFFF", "title": "19324B", "accent": "2B6CB0", "text": "263445", "header": "DCEAF7", "secondary": "E8A23A"},
    "minimal": {"background": "FFFFFF", "title": "202020", "accent": "555555", "text": "333333", "header": "F0F0F0", "secondary": "A0A0A0"},
    "dark": {"background": "16202D", "title": "FFFFFF", "accent": "63C7D4", "text": "E7EDF4", "header": "304356", "secondary": "F2BD68"},
}

def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)

def fill_background(slide, color: str):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(color)

def text_box(slide, value, left, top, width, height, size, color, bold=False):
    shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.text = str(value)
    for paragraph in frame.paragraphs:
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = rgb(color)
    return shape

def add_cover(prs, title, subtitle, author, period, style):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill_background(slide, style["background"])
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(.23), prs.slide_height)
    stripe.fill.solid(); stripe.fill.fore_color.rgb = rgb(style["accent"])
    stripe.line.fill.background()
    text_box(slide, title, 1.0, 1.75, 11.2, 1.7, 36, style["title"], True)
    if subtitle.strip():
        text_box(slide, subtitle, 1.02, 3.55, 10.7, 1.0, 20, style["text"])
    if author.strip():
        text_box(slide, author, 1.02, 6.0, 10.5, .55, 15, style["text"])

def generate(slides: list[SlideContent], destination: Path, title: str,
             template: str = "standard", chart_type: str = "column", style: str = "corporate",
             include_cover: bool = True, subtitle: str = "", author: str = "",
             report_type: str = "plan_fact", one_chart_per_slide: bool = False) -> int:
    if template not in {"standard", "compact"}:
        raise ValueError("Неизвестный шаблон")
    if chart_type not in CHART_TYPES:
        raise ValueError("Неизвестный тип диаграммы")
    if style not in STYLES:
        raise ValueError("Неизвестный стиль презентации")
    theme = STYLES[style]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    if include_cover:
        period = slides[0].title if slides else ""
        add_cover(prs, title, subtitle, author, period, theme)
    for item in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        fill_background(slide, theme["background"])
        text_box(slide, item.title, .6, .35, 12, .75, 25, theme["title"], True)
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.6), Inches(1.12), Inches(1.4), Inches(.06))
        accent.fill.solid(); accent.fill.fore_color.rgb = rgb(theme["accent"])
        accent.line.fill.background()
        data = item.data
        item_report_type = item.report_type or report_type
        item_chart_type = item.chart_type or chart_type
        item_single = item.one_chart_per_slide or one_chart_per_slide
        if item_report_type == "plan_fact":
            headers = ["Показатель", "План", "Факт", "Отклонение", "Откл., %"]
            rows = [[str(r.category), f"{r.plan:,.2f}", f"{r.fact:,.2f}",
                     f"{r.deviation:,.2f}", "—" if pd.isna(r.deviation_pct) else f"{r.deviation_pct:.1f}%"]
                    for r in data.itertuples()]
        elif item_report_type == "dynamics":
            headers = ["Месяц", "План", "Факт", "Изм. к пред. мес., %"]
            rows = [[str(r.period), f"{r.plan:,.2f}", f"{r.fact:,.2f}",
                     "—" if pd.isna(r.change_pct) else f"{r.change_pct:.1f}%"]
                    for r in data.itertuples()]
        elif item_report_type == "expenses":
            headers = ["Статья расходов", "Факт", "Доля, %"]
            rows = [[str(r.category), f"{r.fact:,.2f}", f"{r.share_pct:.1f}%"]
                    for r in data.itertuples()]
        else:
            raise ValueError("Неизвестный тип отчета")
        table = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(.5), Inches(1.45), Inches(7.3), Inches(4.8)).table
        for j, head in enumerate(headers): table.cell(0, j).text = head
        for i, vals in enumerate(rows, 1):
            for j, val in enumerate(vals): table.cell(i, j).text = val
        for i in range(len(data) + 1):
            for j in range(len(headers)):
                cell = table.cell(i, j)
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(theme["header"] if i == 0 else theme["background"])
                for para in cell.text_frame.paragraphs:
                    para.font.name = "Aptos"
                    para.font.size = Pt(11 if template == "compact" else 12)
                    para.font.bold = i == 0
                    para.font.color.rgb = rgb(theme["text"])
        chart_data = CategoryChartData()
        if item_report_type == "dynamics":
            chart_data.categories = data["period"].tolist()
            chart_data.add_series("План", [float(v) for v in data["plan"]])
            chart_data.add_series("Факт", [float(v) for v in data["fact"]])
            selected_chart = XL_CHART_TYPE.LINE
        elif item_report_type == "expenses":
            if item_single:
                amount = float(data["fact"].iloc[0])
                total = amount / (float(data["share_pct"].iloc[0]) / 100)
                chart_data.categories = [str(data["category"].iloc[0]), "Прочие расходы"]
                chart_data.add_series("Доля расходов", [amount, max(0.0, total - amount)])
            else:
                chart_data.categories = data["category"].tolist()
                chart_data.add_series("Расходы", [float(v) for v in data["fact"]])
            selected_chart = XL_CHART_TYPE.PIE
        else:
            chart_data.categories = data["category"].tolist()
            chart_data.add_series("План", [float(v) for v in data["plan"]])
            chart_data.add_series("Факт", [float(v) for v in data["fact"]])
            selected_chart = CHART_TYPES[item_chart_type]
        chart = slide.shapes.add_chart(selected_chart, Inches(8.0), Inches(1.65), Inches(4.8), Inches(4.4), chart_data).chart
        chart.has_legend = True
        chart.chart_style = 10 if style == "corporate" else 13 if style == "minimal" else 12
        try:
            chart.plots[0].series[0].format.fill.solid()
            chart.plots[0].series[0].format.fill.fore_color.rgb = rgb(theme["accent"])
            if len(chart.series) > 1:
                chart.plots[0].series[1].format.fill.solid()
                chart.plots[0].series[1].format.fill.fore_color.rgb = rgb(theme["secondary"])
            if selected_chart == XL_CHART_TYPE.LINE:
                for series, color in zip(chart.series, (theme["accent"], theme["secondary"])):
                    series.format.line.color.rgb = rgb(color)
        except (AttributeError, IndexError):
            pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    prs.save(destination)
    return len(prs.slides)
