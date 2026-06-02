from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import math
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfbase.pdfmetrics import stringWidth

AVE_BLUE = "#0f1c75"
AVE_LIGHT_BLUE = "#1c73f5"
AVE_GREEN = "#00ab0d"
AVE_YELLOW = "#ffb500"
AVE_GRAY = "#f2f4f8"
AVE_DARK = "#25304a"


def _safe(value, default=""):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return value


def _pct(value):
    value = _safe(value, 0)
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"


def _num(value):
    value = _safe(value, 0)
    try:
        if float(value).is_integer():
            return str(int(value))
        return f"{float(value):.1f}"
    except Exception:
        return str(value)


def _short(text, max_chars=46):
    text = str(_safe(text, ""))
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AveTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor(AVE_BLUE),
        alignment=TA_LEFT,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="AveSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor(AVE_DARK),
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AveSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor(AVE_BLUE),
        spaceBefore=12,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="AveBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor(AVE_DARK),
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AveSmall",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor(AVE_DARK),
    ))
    styles.add(ParagraphStyle(
        name="AveMetric",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor(AVE_BLUE),
    ))
    styles.add(ParagraphStyle(
        name="AveMetricLabel",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor(AVE_DARK),
    ))
    return styles


def _table(data, col_widths=None, font_size=7.4, header_bg=AVE_BLUE):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9dde7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
    ]))
    return table


def _metric_cards(summary: dict, styles):
    cards = [
        ("Total estudiantes", _num(summary.get("total_estudiantes"))),
        ("Avance real", _pct(summary.get("avance_real_promedio"))),
        ("Avance esperado", _pct(summary.get("avance_esperado_promedio"))),
        ("Brecha promedio", _pct(summary.get("brecha_promedio"))),
        ("Riesgo alto", _num(summary.get("riesgo_alto"))),
        ("Nunca ingresó", _num(summary.get("nunca_ingreso"))),
    ]
    row = []
    for label, value in cards:
        row.append([Paragraph(value, styles["AveMetric"]), Paragraph(label, styles["AveMetricLabel"])])
    t = Table([row], colWidths=[1.35 * inch] * len(cards))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f8ff")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e6ff")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e6ff")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _summary_text(summary: dict, course_name: str, styles):
    total = _num(summary.get("total_estudiantes"))
    real = _pct(summary.get("avance_real_promedio"))
    esperado = _pct(summary.get("avance_esperado_promedio"))
    brecha = _pct(summary.get("brecha_promedio"))
    alto = _num(summary.get("riesgo_alto"))
    medio = _num(summary.get("riesgo_medio"))
    bajo = _num(summary.get("riesgo_bajo"))
    text = (
        f"Durante el corte analizado del curso <b>{course_name}</b>, se consolidaron <b>{total}</b> estudiantes. "
        f"El avance real promedio fue de <b>{real}</b>, frente a un avance esperado de <b>{esperado}</b>, "
        f"lo cual genera una brecha promedio de <b>{brecha}</b>. La distribución del riesgo académico identificó "
        f"<b>{alto}</b> estudiantes en riesgo alto, <b>{medio}</b> en riesgo medio y <b>{bajo}</b> en riesgo bajo. "
        "Estos resultados permiten priorizar acciones de seguimiento académico, especialmente en estudiantes con falta de ingreso, actividades pendientes o avance insuficiente."
    )
    return Paragraph(text, styles["AveBody"])


def _bar_table(title, rows, styles, label_col="causa_riesgo", value_col="cantidad", max_items=8):
    rows = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame()
    story = [Paragraph(title, styles["AveSection"])]
    if rows.empty or label_col not in rows.columns or value_col not in rows.columns:
        story.append(Paragraph("No hay datos disponibles para este apartado.", styles["AveBody"]))
        return story
    rows = rows.head(max_items)
    max_val = max([float(x or 0) for x in rows[value_col].tolist()] + [1])
    data = [["Indicador", "Cantidad", "Visual"]]
    for _, r in rows.iterrows():
        val = float(_safe(r.get(value_col), 0) or 0)
        bars = "█" * max(1, int(round((val / max_val) * 20))) if val > 0 else ""
        data.append([_short(r.get(label_col), 52), _num(val), bars])
    story.append(_table(data, col_widths=[3.8 * inch, 0.8 * inch, 2.4 * inch], font_size=7.5, header_bg=AVE_LIGHT_BLUE))
    return story


def _footer_canvas(canvas, doc, course_name=""):
    canvas.saveState()
    w, h = landscape(letter)
    # Marca de agua diagonal
    canvas.setFillColor(colors.Color(0.1, 0.1, 0.1, alpha=0.06))
    canvas.setFont("Helvetica-Bold", 22)
    canvas.translate(w / 2, h / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, "Desarrollador: Ing. Christian Pocol - Asesor Academico AVE")
    canvas.rotate(-35)
    canvas.translate(-w / 2, -h / 2)

    # Header line
    canvas.setStrokeColor(colors.HexColor(AVE_BLUE))
    canvas.setLineWidth(1.2)
    canvas.line(0.45 * inch, h - 0.45 * inch, w - 0.45 * inch, h - 0.45 * inch)
    canvas.setStrokeColor(colors.HexColor(AVE_GREEN))
    canvas.setLineWidth(2)
    canvas.line(0.45 * inch, h - 0.49 * inch, 2.4 * inch, h - 0.49 * inch)
    canvas.setStrokeColor(colors.HexColor(AVE_YELLOW))
    canvas.line(2.45 * inch, h - 0.49 * inch, 3.25 * inch, h - 0.49 * inch)
    canvas.setStrokeColor(colors.HexColor(AVE_LIGHT_BLUE))
    canvas.line(3.3 * inch, h - 0.49 * inch, 4.25 * inch, h - 0.49 * inch)

    # Footer
    canvas.setFillColor(colors.HexColor(AVE_DARK))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(0.55 * inch, 0.32 * inch, "AVE UVG - Reporte ejecutivo de indicadores academicos")
    canvas.drawRightString(w - 0.55 * inch, 0.32 * inch, f"Pagina {doc.page}")
    canvas.restoreState()


def generate_executive_pdf(
    df: pd.DataFrame,
    summary: dict,
    course_name: str,
    report_name: str,
    fecha_inicio_analisis: str,
    fecha_fin_analisis: str,
    fecha_corte: str | None = None,
    usuario_generador: str = "Asesor Academico AVE",
    aulas_canvas: list | None = None,
    logo_path: str = "assets/logo_ave.jpg",
) -> bytes:
    """Genera un PDF ejecutivo AVE y lo devuelve como bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.55 * inch,
        title=report_name,
    )
    styles = _make_styles()
    story = []

    logo = None
    if logo_path and Path(logo_path).exists():
        logo = Image(logo_path, width=1.25 * inch, height=0.82 * inch)

    title_block = [
        Paragraph("Reporte ejecutivo de indicadores academicos", styles["AveTitle"]),
        Paragraph(f"<b>Curso:</b> {course_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Reporte:</b> {report_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Rango analizado:</b> {fecha_inicio_analisis} al {fecha_fin_analisis} &nbsp;&nbsp; <b>Fecha de corte:</b> {fecha_corte or fecha_fin_analisis}", styles["AveSubtitle"]),
        Paragraph(f"<b>Generado por:</b> {usuario_generador} &nbsp;&nbsp; <b>Fecha de generacion:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["AveSubtitle"]),
    ]
    header_data = [[logo if logo else "", title_block]]
    header = Table(header_data, colWidths=[1.45 * inch, 8.2 * inch])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(header)
    story.append(Spacer(1, 0.18 * inch))
    story.append(_metric_cards(summary, styles))
    story.append(Spacer(1, 0.14 * inch))
    story.append(Paragraph("Resumen ejecutivo", styles["AveSection"]))
    story.append(_summary_text(summary, course_name, styles))

    aulas_canvas = aulas_canvas or []
    if aulas_canvas:
        story.append(Paragraph("Aulas/secciones consolidadas", styles["AveSection"]))
        aulas_data = [["Aula/seccion", "Canvas course ID"]]
        for item in aulas_canvas[:8]:
            if isinstance(item, dict):
                aulas_data.append([_short(item.get("label", ""), 70), str(item.get("canvas_course_id", ""))])
        story.append(_table(aulas_data, col_widths=[6.5 * inch, 1.6 * inch], font_size=7.5, header_bg=AVE_BLUE))

    # Distribucion y causas
    story.append(Spacer(1, 0.05 * inch))
    risk_counts = pd.DataFrame({
        "nivel_riesgo": ["Bajo", "Medio", "Alto"],
        "cantidad": [summary.get("riesgo_bajo", 0), summary.get("riesgo_medio", 0), summary.get("riesgo_alto", 0)],
    })
    story.extend(_bar_table("Distribucion de riesgo academico", risk_counts, styles, "nivel_riesgo", "cantidad", max_items=3))

    story.append(PageBreak())

    # Ranking de causas
    if "causa_principal_riesgo" in df.columns:
        rank = df["causa_principal_riesgo"].fillna("Sin clasificar").value_counts().reset_index()
        rank.columns = ["causa_riesgo", "cantidad"]
    elif "causa_riesgo" in df.columns:
        rank = df["causa_riesgo"].fillna("Sin clasificar").value_counts().reset_index()
        rank.columns = ["causa_riesgo", "cantidad"]
    else:
        rank = pd.DataFrame()
    story.extend(_bar_table("Ranking de causas de riesgo", rank, styles, "causa_riesgo", "cantidad", max_items=10))

    # Comparacion por seccion
    story.append(Paragraph("Comparacion por aula/seccion", styles["AveSection"]))
    if "curso_aula" in df.columns:
        sec = df.groupby("curso_aula", dropna=False).agg(
            estudiantes=("canvas_user_id", "count"),
            avance_real_pct=("avance_real_pct", "mean"),
            avance_esperado_pct=("avance_esperado_pct", "mean"),
            brecha_pct=("brecha_pct", "mean"),
            riesgo_alto=("nivel_riesgo", lambda s: int((s == "Alto").sum())),
        ).reset_index()
        sec_data = [["Aula/seccion", "Est.", "Avance real", "Esperado", "Brecha", "Riesgo alto"]]
        for _, r in sec.iterrows():
            sec_data.append([
                _short(r["curso_aula"], 54),
                _num(r["estudiantes"]),
                _pct(r["avance_real_pct"]),
                _pct(r["avance_esperado_pct"]),
                _pct(r["brecha_pct"]),
                _num(r["riesgo_alto"]),
            ])
        story.append(_table(sec_data, col_widths=[4.2 * inch, 0.55 * inch, 0.9 * inch, 0.85 * inch, 0.75 * inch, 0.85 * inch], font_size=7.2, header_bg=AVE_BLUE))
    else:
        story.append(Paragraph("No se encontro la columna de aula/seccion en la base individual.", styles["AveBody"]))

    story.append(PageBreak())

    # Estudiantes de riesgo alto
    story.append(Paragraph("Estudiantes priorizados para seguimiento", styles["AveSection"]))
    if "nivel_riesgo" in df.columns:
        high = df[df["nivel_riesgo"].eq("Alto")].copy()
    else:
        high = df.copy()
    if "puntaje_riesgo" in high.columns:
        high = high.sort_values(["puntaje_riesgo", "brecha_pct"], ascending=False, na_position="last")
    high = high.head(25)
    if high.empty:
        story.append(Paragraph("No se identificaron estudiantes en riesgo alto para este corte.", styles["AveBody"]))
    else:
        data = [["Estudiante", "Correo", "Aula", "Real", "Brecha", "Dias sin act.", "Causa", "Recomendacion"]]
        for _, r in high.iterrows():
            data.append([
                _short(r.get("nombre"), 28),
                _short(r.get("correo"), 30),
                _short(r.get("curso_aula"), 26),
                _pct(r.get("avance_real_pct")),
                _pct(r.get("brecha_pct")),
                _num(r.get("dias_sin_actividad")),
                _short(r.get("causa_principal_riesgo", r.get("causa_riesgo", "")), 28),
                _short(r.get("recomendacion", ""), 45),
            ])
        story.append(_table(data, col_widths=[1.35 * inch, 1.45 * inch, 1.2 * inch, 0.45 * inch, 0.5 * inch, 0.55 * inch, 1.3 * inch, 1.65 * inch], font_size=6.2, header_bg=AVE_BLUE))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph("Nota: la tabla muestra hasta 25 estudiantes priorizados por puntaje de riesgo y brecha academica.", styles["AveSmall"]))

    # Cierre
    story.append(Spacer(1, 0.14 * inch))
    story.append(Paragraph("Sugerencia de uso", styles["AveSection"]))
    story.append(Paragraph(
        "Este reporte debe utilizarse como insumo de seguimiento academico. Se recomienda revisar los casos de riesgo alto, registrar intervenciones y comparar el resultado con el siguiente corte historico para validar mejoras o nuevos estancamientos.",
        styles["AveBody"],
    ))

    doc.build(story, onFirstPage=lambda c, d: _footer_canvas(c, d, course_name), onLaterPages=lambda c, d: _footer_canvas(c, d, course_name))
    return buffer.getvalue()
