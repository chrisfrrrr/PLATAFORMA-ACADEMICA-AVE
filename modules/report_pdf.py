from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import math
import textwrap
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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

AVE_BLUE = "#0f1c75"
AVE_LIGHT_BLUE = "#1c73f5"
AVE_GREEN = "#00ab0d"
AVE_YELLOW = "#ffb500"
AVE_GRAY = "#f2f4f8"
AVE_DARK = "#25304a"
AVE_RED = "#d64045"
AVE_ORANGE = "#f08c00"


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


def _wrap_label(text, width=22):
    text = str(_safe(text, ""))
    return "\n".join(textwrap.wrap(text, width=width)) if text else ""


def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AveTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26,
        textColor=colors.HexColor(AVE_BLUE), alignment=TA_LEFT, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="AveSubtitle", parent=styles["Normal"], fontSize=10, leading=14,
        textColor=colors.HexColor(AVE_DARK), alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AveSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=18,
        textColor=colors.HexColor(AVE_BLUE), spaceBefore=10, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="AveBody", parent=styles["Normal"], fontSize=9.4, leading=13,
        textColor=colors.HexColor(AVE_DARK), alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AveSmall", parent=styles["Normal"], fontSize=7.3, leading=9,
        textColor=colors.HexColor(AVE_DARK),
    ))
    styles.add(ParagraphStyle(
        name="AveMetric", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=18,
        alignment=TA_CENTER, textColor=colors.HexColor(AVE_BLUE),
    ))
    styles.add(ParagraphStyle(
        name="AveMetricLabel", parent=styles["Normal"], fontSize=8, leading=10,
        alignment=TA_CENTER, textColor=colors.HexColor(AVE_DARK),
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
    top_problem = "sin alertas críticas"
    if summary.get("combinacion_factores", 0):
        top_problem = "combinación de factores"
    elif summary.get("actividades_pendientes", 0):
        top_problem = "actividades pendientes"
    elif summary.get("nunca_ingreso", 0):
        top_problem = "falta de ingreso al curso"
    text = (
        f"Durante el corte analizado del curso <b>{course_name}</b>, se consolidaron <b>{total}</b> estudiantes. "
        f"El avance real promedio fue de <b>{real}</b>, frente a un avance esperado de <b>{esperado}</b>, "
        f"generando una brecha promedio de <b>{brecha}</b>. La distribución identificó <b>{alto}</b> estudiantes "
        f"en riesgo alto, <b>{medio}</b> en riesgo medio y <b>{bajo}</b> en riesgo bajo. El factor de atención principal "
        f"se relaciona con <b>{top_problem}</b>, por lo que se recomienda priorizar seguimiento focalizado y comparar "
        "estos resultados con el siguiente corte histórico."
    )
    return Paragraph(text, styles["AveBody"])


def _fig_to_image(fig, width=4.6 * inch, height=2.5 * inch):
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    bio.seek(0)
    return Image(bio, width=width, height=height)


def _bar_chart(labels, values, title="", color=AVE_LIGHT_BLUE, horizontal=False, width=4.7 * inch, height=2.55 * inch):
    labels = [str(l) for l in labels]
    values = [float(v or 0) for v in values]
    fig_w, fig_h = (6.8, 3.4) if horizontal else (6.2, 3.4)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    if horizontal:
        y = range(len(labels))
        ax.barh(y, values, color=color)
        ax.set_yticks(y)
        ax.set_yticklabels([_wrap_label(l, 26) for l in labels], fontsize=8)
        ax.invert_yaxis()
        for i, v in enumerate(values):
            ax.text(v + max(values + [1]) * 0.015, i, _num(v), va="center", fontsize=8)
    else:
        x = range(len(labels))
        ax.bar(x, values, color=color)
        ax.set_xticks(x)
        ax.set_xticklabels([_wrap_label(l, 13) for l in labels], fontsize=8)
        for i, v in enumerate(values):
            ax.text(i, v + max(values + [1]) * 0.02, _num(v), ha="center", fontsize=8)
    ax.set_title(title, fontsize=11, color=AVE_BLUE, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x" if horizontal else "y", alpha=0.25)
    return _fig_to_image(fig, width, height)


def _donut_chart(labels, values, title="", width=4.1 * inch, height=2.65 * inch):
    values = [float(v or 0) for v in values]
    labels = [str(l) for l in labels]
    fig, ax = plt.subplots(figsize=(5.6, 3.5))
    colors_list = [AVE_RED, AVE_ORANGE, AVE_YELLOW, AVE_LIGHT_BLUE, AVE_GREEN, AVE_BLUE]
    if sum(values) <= 0:
        values = [1]
        labels = ["Sin datos"]
    wedges, _ = ax.pie(values, startangle=90, colors=colors_list[:len(values)], wedgeprops=dict(width=0.42, edgecolor="white"))
    ax.legend(wedges, [f"{l}: {_num(v)}" for l, v in zip(labels, values)], loc="center left", bbox_to_anchor=(0.92, 0.5), fontsize=8, frameon=False)
    ax.set_title(title, fontsize=11, color=AVE_BLUE, fontweight="bold")
    ax.axis("equal")
    return _fig_to_image(fig, width, height)


def _expected_vs_real_chart(real, expected, gap, width=4.6 * inch, height=2.45 * inch):
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    labels = ["Avance real", "Avance esperado", "Brecha"]
    values = [float(real or 0), float(expected or 0), max(float(gap or 0), 0)]
    cols = [AVE_GREEN, AVE_LIGHT_BLUE, AVE_YELLOW]
    ax.bar(labels, values, color=cols)
    ax.set_ylim(0, max(100, max(values + [1]) * 1.15))
    ax.set_ylabel("Porcentaje")
    ax.set_title("Velocidad de avance: esperado, real y brecha", fontsize=11, color=AVE_BLUE, fontweight="bold")
    for i, v in enumerate(values):
        ax.text(i, v + 2, _pct(v), ha="center", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    return _fig_to_image(fig, width, height)


def _grouped_section_chart(sec_df, width=5.0 * inch, height=2.7 * inch):
    if sec_df is None or sec_df.empty:
        return None
    labels = [_short(x, 18) for x in sec_df["curso_aula"].tolist()]
    real = sec_df["avance_real_pct"].fillna(0).astype(float).tolist()
    expected = sec_df["avance_esperado_pct"].fillna(0).astype(float).tolist()
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    width_bar = 0.36
    ax.bar([i - width_bar/2 for i in x], real, width_bar, label="Real", color=AVE_GREEN)
    ax.bar([i + width_bar/2 for i in x], expected, width_bar, label="Esperado", color=AVE_LIGHT_BLUE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([_wrap_label(l, 12) for l in labels], fontsize=8)
    ax.set_ylim(0, 105)
    ax.set_title("Avance real vs esperado por aula/sección", fontsize=11, color=AVE_BLUE, fontweight="bold")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    return _fig_to_image(fig, width, height)


def _trend_chart(current: dict, previous_summary: dict | None, width=4.7 * inch, height=2.6 * inch):
    if not previous_summary:
        return None
    indicators = ["Avance real", "Brecha", "Riesgo alto", "Nunca ingresó"]
    prev_vals = [
        previous_summary.get("avance_real_promedio", 0),
        previous_summary.get("brecha_promedio", 0),
        previous_summary.get("riesgo_alto", 0),
        previous_summary.get("nunca_ingreso", 0),
    ]
    curr_vals = [
        current.get("avance_real_promedio", 0),
        current.get("brecha_promedio", 0),
        current.get("riesgo_alto", 0),
        current.get("nunca_ingreso", 0),
    ]
    x = range(len(indicators))
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    w = 0.36
    ax.bar([i - w/2 for i in x], prev_vals, w, label="Anterior", color=AVE_GRAY, edgecolor=AVE_DARK)
    ax.bar([i + w/2 for i in x], curr_vals, w, label="Actual", color=AVE_LIGHT_BLUE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([_wrap_label(l, 12) for l in indicators], fontsize=8)
    ax.set_title("Tendencia respecto al reporte anterior", fontsize=11, color=AVE_BLUE, fontweight="bold")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    return _fig_to_image(fig, width, height)


def _state_counts(df: pd.DataFrame, summary: dict) -> pd.DataFrame:
    total = int(summary.get("total_estudiantes", len(df) if df is not None else 0) or 0)
    n_nunca = int(summary.get("nunca_ingreso", 0) or 0)
    n_no_inicio = int(summary.get("ingreso_no_inicio", 0) or 0)
    n_mod1 = int(summary.get("modulo_1", 0) or 0)
    if df is not None and not df.empty:
        parcial_detenido = int(((df.get("avance_real_pct", pd.Series([0]*len(df))) > 0) & (df.get("brecha_pct", pd.Series([0]*len(df))) > 10) & (df.get("dias_sin_actividad", pd.Series([0]*len(df))).fillna(0) >= 5)).sum())
        adecuado = int((df.get("nivel_riesgo", pd.Series([""]*len(df))) == "Bajo").sum())
    else:
        parcial_detenido = int(summary.get("avance_parcial", 0) or 0)
        adecuado = max(total - n_nunca - n_no_inicio - n_mod1 - parcial_detenido, 0)
    rows = [
        ("Nunca ingresó al curso", n_nunca),
        ("Ingresó pero no inició actividades", n_no_inicio),
        ("Inició y se quedó en el primer módulo", n_mod1),
        ("Avanzó parcialmente y se detuvo", parcial_detenido),
        ("Avance adecuado / seguimiento regular", adecuado),
    ]
    out = pd.DataFrame(rows, columns=["estado", "cantidad"])
    out["porcentaje"] = (out["cantidad"] / total * 100).round(1) if total else 0
    return out


def _section_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "curso_aula" not in df.columns:
        return pd.DataFrame()
    return df.groupby("curso_aula", dropna=False).agg(
        estudiantes=("canvas_user_id", "count"),
        avance_real_pct=("avance_real_pct", "mean"),
        avance_esperado_pct=("avance_esperado_pct", "mean"),
        brecha_pct=("brecha_pct", "mean"),
        riesgo_alto=("nivel_riesgo", lambda s: int((s == "Alto").sum())),
        nunca_ingreso=("nunca_ingreso", "sum"),
        ingreso_no_inicio=("ingreso_no_inicio", "sum"),
    ).reset_index().round(2)


def _risk_criticality(row):
    try:
        est = max(float(row.get("estudiantes", 0)), 1)
        brecha = max(float(row.get("brecha_pct", 0)), 0)
        alto = float(row.get("riesgo_alto", 0)) / est * 100
        nunca = float(row.get("nunca_ingreso", 0)) / est * 100
        score = min(100, round((brecha * 0.45) + (alto * 0.4) + (nunca * 0.15), 1))
        return score
    except Exception:
        return 0


def _cause_rank(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["causa_riesgo", "cantidad", "porcentaje"])
    col = "causa_principal_riesgo" if "causa_principal_riesgo" in df.columns else "causa_riesgo"
    if col not in df.columns:
        return pd.DataFrame(columns=["causa_riesgo", "cantidad", "porcentaje"])
    rank = df[col].fillna("Sin clasificar").value_counts().reset_index()
    rank.columns = ["causa_riesgo", "cantidad"]
    rank["porcentaje"] = (rank["cantidad"] / len(df) * 100).round(1)
    return rank


def _trend_table(current: dict, previous_summary: dict | None, styles):
    if not previous_summary:
        return Paragraph("No existe un corte previo disponible para comparación histórica. Al guardar más cortes, esta sección mostrará tendencia entre reportes.", styles["AveBody"])
    rows = [["Indicador", "Anterior", "Actual", "Cambio", "Lectura"]]
    fields = [
        ("Avance real promedio", "avance_real_promedio", True, True),
        ("Brecha promedio", "brecha_promedio", True, False),
        ("Riesgo alto", "riesgo_alto", False, False),
        ("Nunca ingresó", "nunca_ingreso", False, False),
        ("Actividades pendientes", "actividades_pendientes", False, False),
    ]
    for label, key, is_pct, higher_better in fields:
        prev = float(previous_summary.get(key, 0) or 0)
        curr = float(current.get(key, 0) or 0)
        diff = curr - prev
        good = diff > 0 if higher_better else diff < 0
        if abs(diff) < 0.001:
            lectura = "Se mantuvo"
            symbol = "="
        elif good:
            lectura = "Mejoró"
            symbol = "↑" if higher_better else "↓"
        else:
            lectura = "Empeoró"
            symbol = "↓" if higher_better else "↑"
        fmt = _pct if is_pct else _num
        rows.append([label, fmt(prev), fmt(curr), f"{symbol} {fmt(abs(diff))}", lectura])
    return _table(rows, col_widths=[2.4*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.2*inch], font_size=7.2, header_bg=AVE_BLUE)


def _footer_canvas(canvas, doc, course_name=""):
    canvas.saveState()
    w, h = landscape(letter)
    canvas.setFillColor(colors.Color(0.1, 0.1, 0.1, alpha=0.06))
    canvas.setFont("Helvetica-Bold", 22)
    canvas.translate(w / 2, h / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, "Desarrollador: Ing. Christian Pocol - Asesor Academico AVE")
    canvas.rotate(-35)
    canvas.translate(-w / 2, -h / 2)
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
    canvas.setFillColor(colors.HexColor(AVE_DARK))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(0.55 * inch, 0.32 * inch, "AVE UVG - Reporte ejecutivo enriquecido de indicadores academicos")
    canvas.drawRightString(w - 0.55 * inch, 0.32 * inch, f"Pagina {doc.page}")
    canvas.restoreState()




def _pending_status(row: pd.Series) -> str:
    """Clasifica estudiantes pendientes para el reporte operativo."""
    if bool(row.get("nunca_ingreso")):
        return "Nunca ingresó al curso"
    if bool(row.get("ingreso_no_inicio")):
        return "Ingresó pero no inició actividades"
    try:
        pendientes = float(row.get("actividades_pendientes") or 0)
        total = float(row.get("actividades_total") or 0)
        if total > 0 and pendientes > 0:
            return "Tiene actividades pendientes"
    except Exception:
        pass
    try:
        brecha = float(row.get("brecha_pct") or 0)
        if brecha >= 15:
            return "Tiene brecha de avance"
    except Exception:
        pass
    return "Seguimiento regular"


def _pending_priority(row: pd.Series) -> int:
    if bool(row.get("nunca_ingreso")):
        return 1
    if bool(row.get("ingreso_no_inicio")):
        return 2
    try:
        if float(row.get("brecha_pct") or 0) >= 30:
            return 3
    except Exception:
        pass
    try:
        pendientes = float(row.get("actividades_pendientes") or 0)
        total = float(row.get("actividades_total") or 0)
        if total > 0 and pendientes / total >= 0.40:
            return 4
    except Exception:
        pass
    return 5


def _pending_action(status: str) -> str:
    if status == "Nunca ingresó al curso":
        return "Contacto inmediato para validar acceso, credenciales y orientación inicial."
    if status == "Ingresó pero no inició actividades":
        return "Enviar guía de primera actividad y confirmar comprensión de instrucciones."
    if status == "Tiene actividades pendientes":
        return "Solicitar plan corto de recuperación de actividades pendientes."
    if status == "Tiene brecha de avance":
        return "Revisar avance esperado y acordar meta de recuperación para el próximo corte."
    return "Mantener monitoreo preventivo."


def _build_pending_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    work = df.copy()
    if "estado_pendiente" not in work.columns:
        work["estado_pendiente"] = work.apply(_pending_status, axis=1)
    work["prioridad_pendiente"] = work.apply(_pending_priority, axis=1)
    work["accion_sugerida"] = work["estado_pendiente"].apply(_pending_action)

    mask = (
        work.get("nunca_ingreso", False).astype(bool)
        | work.get("ingreso_no_inicio", False).astype(bool)
    )
    if "actividades_pendientes" in work.columns:
        mask = mask | (pd.to_numeric(work["actividades_pendientes"], errors="coerce").fillna(0) > 0)
    if "brecha_pct" in work.columns:
        mask = mask | (pd.to_numeric(work["brecha_pct"], errors="coerce").fillna(0) >= 15)
    if "nivel_riesgo" in work.columns:
        mask = mask | work["nivel_riesgo"].astype(str).isin(["Alto", "Medio"])

    work = work[mask].copy()
    sort_cols = [c for c in ["prioridad_pendiente", "puntaje_riesgo", "brecha_pct", "actividades_pendientes"] if c in work.columns]
    ascending = [True] + [False] * (len(sort_cols) - 1)
    if sort_cols:
        work = work.sort_values(sort_cols, ascending=ascending, na_position="last")
    return work


def generate_pending_students_pdf(
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
    """Genera un segundo PDF operativo con estudiantes pendientes y sin ingreso."""
    pending = _build_pending_df(df)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.55 * inch,
        title=report_name,
    )
    styles = _make_styles()
    story = []

    logo = Image(logo_path, width=1.25 * inch, height=0.82 * inch) if logo_path and Path(logo_path).exists() else ""
    title_block = [
        Paragraph("Reporte de estudiantes pendientes y sin ingreso", styles["AveTitle"]),
        Paragraph(f"<b>Curso:</b> {course_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Reporte:</b> {report_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Rango analizado:</b> {fecha_inicio_analisis} al {fecha_fin_analisis} &nbsp;&nbsp; <b>Fecha de corte:</b> {fecha_corte or fecha_fin_analisis}", styles["AveSubtitle"]),
        Paragraph(f"<b>Generado por:</b> {usuario_generador} &nbsp;&nbsp; <b>Fecha de generacion:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["AveSubtitle"]),
    ]
    header = Table([[logo, title_block]], colWidths=[1.45 * inch, 8.3 * inch])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(header)
    story.append(Spacer(1, 0.14 * inch))

    total_pend = len(pending)
    n_nunca = int(pending.get("nunca_ingreso", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not pending.empty else 0
    n_no_inicio = int(pending.get("ingreso_no_inicio", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not pending.empty else 0
    n_pendientes = int((pd.to_numeric(pending.get("actividades_pendientes", pd.Series(dtype=float)), errors="coerce").fillna(0) > 0).sum()) if not pending.empty else 0
    n_brecha = int((pd.to_numeric(pending.get("brecha_pct", pd.Series(dtype=float)), errors="coerce").fillna(0) >= 15).sum()) if not pending.empty else 0

    cards = [
        ("Pendientes priorizados", _num(total_pend)),
        ("Nunca ingresaron", _num(n_nunca)),
        ("Ingresaron sin iniciar", _num(n_no_inicio)),
        ("Con actividades pendientes", _num(n_pendientes)),
        ("Con brecha >= 15%", _num(n_brecha)),
        ("Total del curso", _num(summary.get("total_estudiantes", len(df) if df is not None else 0))),
    ]
    row = [[Paragraph(value, styles["AveMetric"]), Paragraph(label, styles["AveMetricLabel"])] for label, value in cards]
    metric_table = Table([row], colWidths=[1.42 * inch] * len(cards))
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f8ff")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e6ff")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e6ff")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Propósito del reporte", styles["AveSection"]))
    story.append(Paragraph(
        "Este reporte operativo separa a los estudiantes que requieren seguimiento inmediato por falta de ingreso, ausencia de inicio, actividades pendientes o brecha de avance. Su finalidad es facilitar el contacto académico y priorizar acciones de acompañamiento.",
        styles["AveBody"],
    ))
    story.append(Spacer(1, 0.10 * inch))

    if not pending.empty:
        status_counts = pending["estado_pendiente"].value_counts().reset_index()
        status_counts.columns = ["estado", "cantidad"]
        status_img = _bar_chart(status_counts["estado"].tolist(), status_counts["cantidad"].tolist(), title="Distribución de estudiantes pendientes", horizontal=True, color=AVE_ORANGE, width=5.0*inch, height=2.7*inch)
        status_data = [["Estado", "Cantidad"]]
        for _, r in status_counts.iterrows():
            status_data.append([_short(r["estado"], 44), _num(r["cantidad"])])
        story.append(Table([[status_img, _table(status_data, col_widths=[2.6*inch, 0.9*inch], font_size=7.1, header_bg=AVE_BLUE)]], colWidths=[5.25*inch, 3.8*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))

        sec_col = "curso_aula" if "curso_aula" in pending.columns else None
        if sec_col:
            sec_counts = pending.groupby(sec_col).size().reset_index(name="cantidad").sort_values("cantidad", ascending=False)
            sec_data = [["Aula/sección", "Pendientes", "Nunca ingresó", "Ingresó sin iniciar"]]
            for _, r in sec_counts.iterrows():
                sec_name = r[sec_col]
                block = pending[pending[sec_col].eq(sec_name)]
                sec_data.append([
                    _short(sec_name, 52), _num(r["cantidad"]),
                    _num(block.get("nunca_ingreso", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
                    _num(block.get("ingreso_no_inicio", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
                ])
            story.append(KeepTogether([
                Paragraph("Pendientes por aula/sección", styles["AveSection"]),
                _table(sec_data, col_widths=[5.2*inch, 1.0*inch, 1.1*inch, 1.2*inch], font_size=7.0, header_bg=AVE_BLUE),
            ]))
    else:
        story.append(Paragraph("No se identificaron estudiantes pendientes bajo los criterios definidos para este corte.", styles["AveBody"]))

    story.append(PageBreak())
    story.append(Paragraph("Listado operativo de estudiantes pendientes", styles["AveSection"]))
    if pending.empty:
        story.append(Paragraph("No hay estudiantes para mostrar.", styles["AveBody"]))
    else:
        data = [["No.", "Estudiante", "Correo", "Aula/sección", "Estado", "Real", "Esperado", "Brecha", "Pend.", "Última act.", "Acción sugerida"]]
        for i, (_, r) in enumerate(pending.iterrows(), start=1):
            last_act = _safe(r.get("ultima_actividad"), "Sin registro")
            try:
                if hasattr(last_act, "strftime"):
                    last_act = last_act.strftime("%Y-%m-%d")
            except Exception:
                pass
            data.append([
                str(i), _short(r.get("nombre"), 25), _short(r.get("correo"), 27), _short(r.get("curso_aula"), 24),
                _short(r.get("estado_pendiente"), 28), _pct(r.get("avance_real_pct")), _pct(r.get("avance_esperado_pct")), _pct(r.get("brecha_pct")),
                _num(r.get("actividades_pendientes")), str(last_act)[:10], _short(r.get("accion_sugerida"), 48),
            ])
        story.append(_table(data, col_widths=[0.32*inch, 1.18*inch, 1.25*inch, 1.05*inch, 1.18*inch, 0.45*inch, 0.52*inch, 0.48*inch, 0.38*inch, 0.62*inch, 2.0*inch], font_size=5.7, header_bg=AVE_BLUE))
        story.append(Spacer(1, 0.08*inch))
        story.append(Paragraph("Sugerencia: usar este listado como base de contacto y actualizar el resultado de la intervención en el siguiente corte histórico.", styles["AveSmall"]))

    doc.build(story, onFirstPage=lambda c, d: _footer_canvas(c, d, course_name), onLaterPages=lambda c, d: _footer_canvas(c, d, course_name))
    return buffer.getvalue()

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
    previous_report: dict | None = None,
) -> bytes:
    """Genera un PDF ejecutivo AVE enriquecido con graficas, comparativos y tendencia."""
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

    logo = Image(logo_path, width=1.25 * inch, height=0.82 * inch) if logo_path and Path(logo_path).exists() else ""
    title_block = [
        Paragraph("Reporte ejecutivo enriquecido de indicadores academicos", styles["AveTitle"]),
        Paragraph(f"<b>Curso:</b> {course_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Reporte:</b> {report_name}", styles["AveSubtitle"]),
        Paragraph(f"<b>Rango analizado:</b> {fecha_inicio_analisis} al {fecha_fin_analisis} &nbsp;&nbsp; <b>Fecha de corte:</b> {fecha_corte or fecha_fin_analisis}", styles["AveSubtitle"]),
        Paragraph(f"<b>Generado por:</b> {usuario_generador} &nbsp;&nbsp; <b>Fecha de generacion:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["AveSubtitle"]),
    ]
    header = Table([[logo, title_block]], colWidths=[1.45 * inch, 8.2 * inch])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(header)
    story.append(Spacer(1, 0.16 * inch))
    story.append(_metric_cards(summary, styles))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Resumen ejecutivo", styles["AveSection"]))
    story.append(_summary_text(summary, course_name, styles))

    risk_img = _donut_chart(
        ["Bajo", "Medio", "Alto"],
        [summary.get("riesgo_bajo", 0), summary.get("riesgo_medio", 0), summary.get("riesgo_alto", 0)],
        title="Distribución general de riesgo",
        width=4.15 * inch,
        height=2.35 * inch,
    )
    speed_img = _expected_vs_real_chart(
        summary.get("avance_real_promedio", 0), summary.get("avance_esperado_promedio", 0), summary.get("brecha_promedio", 0),
        width=4.35 * inch,
        height=2.35 * inch,
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(Table([[risk_img, speed_img]], colWidths=[4.45*inch, 4.65*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))

    aulas_canvas = aulas_canvas or []
    if aulas_canvas:
        story.append(Paragraph("Aulas/secciones consolidadas", styles["AveSection"]))
        aulas_data = [["Aula/seccion", "Canvas course ID"]]
        for item in aulas_canvas[:10]:
            if isinstance(item, dict):
                aulas_data.append([_short(item.get("label", ""), 70), str(item.get("canvas_course_id", ""))])
        story.append(_table(aulas_data, col_widths=[6.5 * inch, 1.6 * inch], font_size=7.3, header_bg=AVE_BLUE))

    story.append(PageBreak())

    # Página 2: estados académicos
    story.append(Paragraph("Estado académico del estudiantado", styles["AveSection"]))
    state_df = _state_counts(df, summary)
    state_img = _bar_chart(state_df["estado"].tolist(), state_df["cantidad"].tolist(), title="Estados críticos y avance del curso", horizontal=True, color=AVE_LIGHT_BLUE, width=5.25*inch, height=3.05*inch)
    state_table = [["Estado", "Cantidad", "%"]]
    for _, r in state_df.iterrows():
        state_table.append([_short(r["estado"], 48), _num(r["cantidad"]), _pct(r["porcentaje"])])
    story.append(Table([[state_img, _table(state_table, col_widths=[2.4*inch, 0.75*inch, 0.65*inch], font_size=7.1, header_bg=AVE_BLUE)]], colWidths=[5.55*inch, 3.85*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(Spacer(1, 0.14*inch))
    story.append(Paragraph(
        "Lectura: esta sección permite identificar en qué punto del recorrido se concentra la pérdida de participación: acceso inicial, inicio de actividades, permanencia en el primer módulo o estancamiento posterior.",
        styles["AveBody"],
    ))

    # Página 3: velocidad de avance y cohortes
    story.append(PageBreak())
    story.append(Paragraph("Velocidad de avance y brecha académica", styles["AveSection"]))
    sec_df = _section_dataframe(df)
    chart_sec = _grouped_section_chart(sec_df, width=5.25*inch, height=2.9*inch) if not sec_df.empty else None
    if chart_sec:
        story.append(Table([[speed_img, chart_sec]], colWidths=[4.35*inch, 5.25*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))
    else:
        story.append(speed_img)
    story.append(Spacer(1, 0.12*inch))
    story.append(Paragraph(
        f"El avance esperado a la fecha es de <b>{_pct(summary.get('avance_esperado_promedio'))}</b>, mientras que el avance real promedio es de <b>{_pct(summary.get('avance_real_promedio'))}</b>. La brecha promedio resultante es de <b>{_pct(summary.get('brecha_promedio'))}</b>.",
        styles["AveBody"],
    ))

    story.append(Paragraph("Diferencias importantes entre cohortes / secciones", styles["AveSection"]))
    if not sec_df.empty:
        sec_df["criticidad"] = sec_df.apply(_risk_criticality, axis=1)
        sec_sorted = sec_df.sort_values("criticidad", ascending=False)
        sec_data = [["Aula/sección", "Est.", "Real", "Esperado", "Brecha", "Riesgo alto", "Nunca ingresó", "Criticidad"]]
        for _, r in sec_sorted.iterrows():
            sec_data.append([
                _short(r["curso_aula"], 42), _num(r["estudiantes"]), _pct(r["avance_real_pct"]), _pct(r["avance_esperado_pct"]),
                _pct(r["brecha_pct"]), _num(r["riesgo_alto"]), _num(r["nunca_ingreso"]), _num(r["criticidad"]),
            ])
        story.append(_table(sec_data, col_widths=[3.0*inch, 0.45*inch, 0.7*inch, 0.75*inch, 0.65*inch, 0.75*inch, 0.85*inch, 0.75*inch], font_size=6.7, header_bg=AVE_BLUE))
    else:
        story.append(Paragraph("No se encontró información suficiente para comparar secciones.", styles["AveBody"]))

    # Página 4: tendencia histórica
    story.append(PageBreak())
    story.append(Paragraph("Tendencia respecto al reporte anterior", styles["AveSection"]))
    previous_summary = (previous_report or {}).get("resumen") if previous_report else None
    trend_img = _trend_chart(summary, previous_summary, width=4.9*inch, height=2.7*inch)
    trend_table = _trend_table(summary, previous_summary, styles)
    if trend_img:
        story.append(Table([[trend_img, trend_table]], colWidths=[5.0*inch, 4.3*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Reporte anterior utilizado: <b>{_safe((previous_report or {}).get('nombre_reporte'), 'Sin nombre')}</b>.", styles["AveSmall"]))
    else:
        story.append(trend_table)
    story.append(Spacer(1, 0.14*inch))
    story.append(Paragraph("Interpretación: una mejora deseable implica aumento del avance real, reducción de brecha, disminución de riesgo alto y reducción de estudiantes que nunca ingresaron.", styles["AveBody"]))

    # Página 5: ranking causas
    story.append(PageBreak())
    story.append(Paragraph("Ranking de causas de riesgo", styles["AveSection"]))
    rank = _cause_rank(df)
    if not rank.empty:
        rank_img = _bar_chart(rank["causa_riesgo"].head(10).tolist(), rank["cantidad"].head(10).tolist(), title="Causas principales de riesgo", horizontal=True, color=AVE_ORANGE, width=5.25*inch, height=3.0*inch)
        rank_data = [["Causa", "Cantidad", "%"]]
        for _, r in rank.head(10).iterrows():
            rank_data.append([_short(r["causa_riesgo"], 42), _num(r["cantidad"]), _pct(r["porcentaje"])])
        story.append(Table([[rank_img, _table(rank_data, col_widths=[2.35*inch, 0.75*inch, 0.65*inch], font_size=7.0, header_bg=AVE_BLUE)]], colWidths=[5.55*inch, 3.75*inch], style=[("VALIGN", (0,0), (-1,-1), "TOP")]))
    else:
        story.append(Paragraph("No hay causas de riesgo disponibles para este corte.", styles["AveBody"]))
    story.append(Spacer(1, 0.12*inch))
    story.append(Paragraph("Este ranking ayuda a priorizar acciones: acceso inicial, orientación sobre primeras actividades, recuperación de pendientes, acompañamiento por brecha de avance o intervención integral cuando existe combinación de factores.", styles["AveBody"]))

    # Página 6: estudiantes priorizados
    story.append(PageBreak())
    story.append(Paragraph("Estudiantes priorizados para seguimiento", styles["AveSection"]))
    high = df[df["nivel_riesgo"].eq("Alto")].copy() if "nivel_riesgo" in df.columns else df.copy()
    if "puntaje_riesgo" in high.columns:
        high = high.sort_values(["puntaje_riesgo", "brecha_pct"], ascending=False, na_position="last")
    high = high.head(28)
    if high.empty:
        story.append(Paragraph("No se identificaron estudiantes en riesgo alto para este corte.", styles["AveBody"]))
    else:
        data = [["Estudiante", "Correo", "Aula", "Real", "Esperado", "Brecha", "Días", "Causa", "Recomendación"]]
        for _, r in high.iterrows():
            data.append([
                _short(r.get("nombre"), 25), _short(r.get("correo"), 27), _short(r.get("curso_aula"), 22),
                _pct(r.get("avance_real_pct")), _pct(r.get("avance_esperado_pct")), _pct(r.get("brecha_pct")),
                _num(r.get("dias_sin_actividad")), _short(r.get("causa_principal_riesgo", r.get("causa_riesgo", "")), 24),
                _short(r.get("recomendacion", ""), 40),
            ])
        story.append(_table(data, col_widths=[1.18*inch, 1.25*inch, 1.0*inch, 0.43*inch, 0.50*inch, 0.48*inch, 0.38*inch, 1.05*inch, 1.55*inch], font_size=5.8, header_bg=AVE_BLUE))
        story.append(Spacer(1, 0.08*inch))
        story.append(Paragraph("Nota: la tabla muestra hasta 28 estudiantes priorizados por puntaje de riesgo y brecha académica.", styles["AveSmall"]))

    story.append(Spacer(1, 0.12*inch))
    story.append(Paragraph("Sugerencia de uso", styles["AveSection"]))
    story.append(Paragraph(
        "Este reporte debe utilizarse como insumo de seguimiento académico. Se recomienda registrar intervenciones, contactar primero a los estudiantes en riesgo alto y evaluar el siguiente corte para confirmar si la brecha disminuye.",
        styles["AveBody"],
    ))

    doc.build(story, onFirstPage=lambda c, d: _footer_canvas(c, d, course_name), onLaterPages=lambda c, d: _footer_canvas(c, d, course_name))
    return buffer.getvalue()
