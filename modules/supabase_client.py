from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import math

import pandas as pd
import streamlit as st
from supabase import create_client


INTEGER_FIELDS = {
    "id",
    "reporte_id",
    "total_estudiantes",
    "riesgo_bajo",
    "riesgo_medio",
    "riesgo_alto",
    "nunca_ingreso",
    "ingreso_no_inicio",
    "modulo_1",
    "avance_parcial",
    "avance_insuficiente",
    "actividades_pendientes",
    "combinacion_factores",
    "canvas_course_id",
    "canvas_user_id",
    "section_id",
    "dias_sin_actividad",
    "actividades_total",
    "actividades_completadas",
    "modulo_maximo",
    "puntaje_riesgo",
}

NUMERIC_FIELDS = {
    "avance_esperado_promedio",
    "avance_real_promedio",
    "brecha_promedio",
    "tiempo_total_min",
    "avance_real_pct",
    "avance_esperado_pct",
    "brecha_pct",
}

TIMESTAMP_FIELDS = {
    "ultimo_ingreso",
    "ultima_entrega",
    "ultima_actividad",
    "fecha_registro",
    "fecha_generacion",
}


def _to_int_or_none(value: Any) -> Optional[int]:
    """Convierte enteros que Pandas puede dejar como 5.0 o '5.0'."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() in {"nan", "nat", "none", "null"}:
            return None
        try:
            return int(float(text))
        except Exception:
            return None

    try:
        return int(float(value))
    except Exception:
        return None


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() in {"nan", "nat", "none", "null"}:
            return None
        text = text.replace("%", "")
        try:
            return float(text)
        except Exception:
            return None

    try:
        return float(value)
    except Exception:
        return None


def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def test_supabase_connection():
    try:
        client = get_supabase_client()
        if client:
            return True, "Conexión con Supabase creada correctamente."
        return False, "No se pudo crear el cliente de Supabase."
    except Exception as e:
        return False, str(e)


def _clean_value(value: Any) -> Any:
    """Convierte valores de Pandas/Numpy a formatos aceptados por Supabase.

    Canvas puede devolver campos vacíos que Pandas representa como NaT o NaN.
    Supabase/PostgreSQL no acepta el texto "NaT" en columnas timestamptz, por eso
    estos valores se transforman explícitamente a None antes de guardar.
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, float) and math.isnan(value):
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return None

    if isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_clean_value(v) for v in value]

    return value


def _clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}

    for key, value in record.items():
        if key in INTEGER_FIELDS:
            cleaned[key] = _to_int_or_none(value)
        elif key in NUMERIC_FIELDS:
            cleaned[key] = _to_float_or_none(value)
        elif key in TIMESTAMP_FIELDS:
            cleaned[key] = _clean_value(value)
        else:
            cleaned[key] = _clean_value(value)

    return cleaned


def save_report_snapshot(
    nombre_reporte: str,
    curso_consolidado: str,
    fecha_inicio_analisis: str,
    fecha_fin_analisis: str,
    fecha_inicio_curso: str,
    fecha_fin_curso: str,
    aulas_canvas: List[Dict[str, Any]],
    resumen: Dict[str, Any],
    student_rows: List[Dict[str, Any]],
    usuario_generador: str = "Asesor AVE",
) -> Tuple[bool, Any]:
    """Guarda un corte del reporte en Supabase.

    Requiere las tablas sugeridas en database/schema_fase3.sql.
    Si las tablas no existen, se devuelve el error para que el usuario lo vea en Streamlit.
    """
    try:
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        report_payload = {
            "nombre_reporte": nombre_reporte,
            "curso_consolidado": curso_consolidado,
            "fecha_inicio_analisis": fecha_inicio_analisis,
            "fecha_fin_analisis": fecha_fin_analisis,
            "fecha_inicio_curso": fecha_inicio_curso,
            "fecha_fin_curso": fecha_fin_curso,
            "aulas_canvas": aulas_canvas,
            "usuario_generador": usuario_generador,
            "fecha_generacion": now,
        }
        report_res = client.table("reportes_ave").insert(report_payload).execute()
        report_data = report_res.data or []
        if not report_data:
            return False, "Supabase no devolvió el reporte insertado."
        report_id = report_data[0]["id"]

        resumen_payload = dict(resumen)
        resumen_payload["reporte_id"] = report_id
        client.table("resumen_reportes_ave").insert(_clean_record(resumen_payload)).execute()

        detalle_payload = []
        for row in student_rows:
            r = _clean_record(row)
            r["reporte_id"] = report_id
            detalle_payload.append(r)

        # Inserción por lotes para evitar payloads demasiado grandes.
        batch_size = 300
        for i in range(0, len(detalle_payload), batch_size):
            client.table("reporte_estudiantes_ave").insert(detalle_payload[i:i + batch_size]).execute()

        return True, {"reporte_id": report_id, "estudiantes_guardados": len(detalle_payload)}
    except Exception as e:
        return False, str(e)


def get_previous_report(curso_consolidado: str, current_report_id: Optional[int] = None) -> Tuple[bool, Any]:
    """Obtiene el reporte previo más reciente para comparar tendencia."""
    try:
        client = get_supabase_client()
        q = client.table("reportes_ave").select("id,nombre_reporte,curso_consolidado,fecha_generacion").eq("curso_consolidado", curso_consolidado).order("fecha_generacion", desc=True).limit(2)
        res = q.execute()
        rows = res.data or []
        if current_report_id:
            rows = [r for r in rows if r.get("id") != current_report_id]
        if not rows:
            return False, "No hay reportes previos guardados para este curso consolidado."
        previous = rows[0]
        summary_res = client.table("resumen_reportes_ave").select("*").eq("reporte_id", previous["id"]).limit(1).execute()
        previous["resumen"] = (summary_res.data or [{}])[0]
        return True, previous
    except Exception as e:
        return False, str(e)
