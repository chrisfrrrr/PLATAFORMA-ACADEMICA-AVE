from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd


def _parse_dt(value):
    if not value:
        return None
    try:
        return pd.to_datetime(value, utc=True, errors="coerce")
    except Exception:
        return None


def _module_assignment_map(modules: List[dict]) -> Dict[int, Dict[str, Any]]:
    mapping: Dict[int, Dict[str, Any]] = {}
    for module_index, module in enumerate(modules or [], start=1):
        module_name = module.get("name") or f"Módulo {module_index}"
        for item in module.get("items") or []:
            if item.get("type") == "Assignment" and item.get("content_id"):
                mapping[int(item["content_id"])] = {
                    "module_index": module_index,
                    "module_name": module_name,
                }
    return mapping


def _flatten_grouped_submissions(submissions_payload) -> List[dict]:
    """Canvas puede devolver grouped=true como lista de grupos por usuario."""
    rows: List[dict] = []
    if not submissions_payload:
        return rows
    for item in submissions_payload:
        if isinstance(item, dict) and "submissions" in item:
            user_id = item.get("user_id") or item.get("id")
            for sub in item.get("submissions") or []:
                sub = dict(sub)
                sub["user_id"] = sub.get("user_id") or user_id
                rows.append(sub)
        elif isinstance(item, dict):
            rows.append(item)
    return rows


def build_course_student_metrics(dataset: Dict[str, Any], fecha_inicio=None, fecha_fin=None) -> pd.DataFrame:
    course_id = dataset.get("course_id")
    course_name = dataset.get("course_name")
    enrollments = dataset.get("enrollments") or []
    assignments = dataset.get("assignments") or []
    modules = dataset.get("modules") or []
    submissions_payload = dataset.get("submissions") or []

    published_assignments = [a for a in assignments if a.get("published", True)]
    total_activities = len(published_assignments)
    assignment_ids = {a.get("id") for a in published_assignments if a.get("id")}
    module_map = _module_assignment_map(modules)

    submissions = _flatten_grouped_submissions(submissions_payload)
    sub_by_user: Dict[int, List[dict]] = {}
    for sub in submissions:
        uid = sub.get("user_id")
        if uid is not None:
            try:
                sub_by_user.setdefault(int(uid), []).append(sub)
            except Exception:
                pass

    rows = []
    now = pd.Timestamp.utcnow()

    for enr in enrollments:
        user = enr.get("user") or {}
        user_id = user.get("id") or enr.get("user_id")
        if not user_id:
            continue
        try:
            user_id_int = int(user_id)
        except Exception:
            user_id_int = user_id

        user_subs = sub_by_user.get(user_id_int, []) if isinstance(user_id_int, int) else []
        valid_subs = [s for s in user_subs if not assignment_ids or s.get("assignment_id") in assignment_ids]
        completed = []
        last_submission_at = None
        max_module = None
        max_module_name = None

        for s in valid_subs:
            submitted = bool(s.get("submitted_at"))
            graded = s.get("score") is not None or s.get("grade") not in [None, ""]
            workflow_submitted = s.get("workflow_state") in ["submitted", "graded", "pending_review"]
            if submitted or graded or workflow_submitted:
                completed.append(s)
                dt = _parse_dt(s.get("submitted_at") or s.get("graded_at"))
                if dt is not None and not pd.isna(dt):
                    if last_submission_at is None or dt > last_submission_at:
                        last_submission_at = dt
                aid = s.get("assignment_id")
                if aid in module_map:
                    m_info = module_map[aid]
                    if max_module is None or m_info["module_index"] > max_module:
                        max_module = m_info["module_index"]
                        max_module_name = m_info["module_name"]

        activities_completed = len({s.get("assignment_id") for s in completed if s.get("assignment_id")})
        activities_pending = max(total_activities - activities_completed, 0) if total_activities else None
        avance_real = round((activities_completed / total_activities) * 100, 2) if total_activities else 0.0

        last_activity_at = _parse_dt(enr.get("last_activity_at"))
        total_activity_time = enr.get("total_activity_time") or 0
        total_activity_minutes = round(float(total_activity_time) / 60, 1) if total_activity_time else 0

        ultima_actividad_general = last_submission_at or last_activity_at
        dias_sin_actividad = None
        if ultima_actividad_general is not None and not pd.isna(ultima_actividad_general):
            dias_sin_actividad = int((now - ultima_actividad_general).total_seconds() // 86400)

        nunca_ingreso = pd.isna(last_activity_at) or last_activity_at is None
        ingreso_no_inicio = (not nunca_ingreso) and activities_completed == 0
        inicio_modulo_1 = activities_completed > 0 and (max_module == 1 or max_module is None)

        if nunca_ingreso:
            estado_base = "Nunca ingresó al curso"
        elif ingreso_no_inicio:
            estado_base = "Ingresó pero no inició actividades"
        elif inicio_modulo_1:
            estado_base = "Inició y se quedó en el primer módulo"
        else:
            estado_base = "Avance parcial registrado"

        rows.append({
            "canvas_course_id": course_id,
            "curso_aula": course_name,
            "canvas_user_id": user_id,
            "nombre": user.get("name") or user.get("sortable_name") or "Sin nombre",
            "correo": user.get("login_id") or user.get("email"),
            "section_id": enr.get("course_section_id"),
            "estado_inscripcion": enr.get("enrollment_state"),
            "ultimo_ingreso": last_activity_at,
            "ultima_entrega": last_submission_at,
            "ultima_actividad": ultima_actividad_general,
            "dias_sin_actividad": dias_sin_actividad,
            "tiempo_total_min": total_activity_minutes,
            "actividades_total": total_activities,
            "actividades_completadas": activities_completed,
            "actividades_pendientes": activities_pending,
            "avance_real_pct": avance_real,
            "modulo_maximo": max_module,
            "modulo_maximo_nombre": max_module_name,
            "nunca_ingreso": nunca_ingreso,
            "ingreso_no_inicio": ingreso_no_inicio,
            "inicio_y_modulo_1": inicio_modulo_1,
            "estado_base": estado_base,
        })

    return pd.DataFrame(rows)


def consolidate_datasets(datasets: List[Dict[str, Any]], fecha_inicio=None, fecha_fin=None) -> pd.DataFrame:
    frames = []
    for ds in datasets:
        df = build_course_student_metrics(ds, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_summary(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "total_estudiantes": 0,
            "avance_promedio": 0,
            "nunca_ingreso": 0,
            "ingreso_no_inicio": 0,
            "modulo_1": 0,
            "avance_parcial": 0,
        }
    return {
        "total_estudiantes": int(len(df)),
        "avance_promedio": round(float(df["avance_real_pct"].mean()), 2),
        "nunca_ingreso": int(df["nunca_ingreso"].sum()),
        "ingreso_no_inicio": int(df["ingreso_no_inicio"].sum()),
        "modulo_1": int(df["inicio_y_modulo_1"].sum()),
        "avance_parcial": int((df["estado_base"] == "Avance parcial registrado").sum()),
    }
