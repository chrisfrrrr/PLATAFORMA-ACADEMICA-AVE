from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
from supabase import create_client


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


def _clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}
    for k, v in record.items():
        if hasattr(v, "isoformat"):
            clean[k] = v.isoformat()
        elif str(type(v)).find("Timestamp") >= 0:
            clean[k] = None if str(v) == "NaT" else v.isoformat()
        elif v != v:  # NaN
            clean[k] = None
        else:
            clean[k] = v
    return clean


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
