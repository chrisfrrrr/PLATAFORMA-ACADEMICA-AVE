from __future__ import annotations

from typing import Any, Dict, List, Optional
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


def _submission_is_completed(sub: dict) -> bool:
    submitted = bool(sub.get("submitted_at"))
    graded = sub.get("score") is not None or sub.get("grade") not in [None, ""]
    workflow_submitted = sub.get("workflow_state") in ["submitted", "graded", "pending_review"]
    return submitted or graded or workflow_submitted


def _expected_progress(fecha_inicio_curso, fecha_fin_curso, fecha_corte) -> float:
    start = pd.to_datetime(fecha_inicio_curso).normalize()
    end = pd.to_datetime(fecha_fin_curso).normalize()
    cut = pd.to_datetime(fecha_corte).normalize()
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0
    elapsed = (cut - start).days
    total = (end - start).days
    value = (elapsed / total) * 100
    return round(float(max(0, min(100, value))), 2)


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
            if _submission_is_completed(s):
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
            "nunca_ingreso": bool(nunca_ingreso),
            "ingreso_no_inicio": bool(ingreso_no_inicio),
            "inicio_y_modulo_1": bool(inicio_modulo_1),
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


def add_expected_gap_and_risk(
    df: pd.DataFrame,
    fecha_inicio_curso,
    fecha_fin_curso,
    fecha_corte,
    inactive_days_threshold: int = 5,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    expected = _expected_progress(fecha_inicio_curso, fecha_fin_curso, fecha_corte)
    out["avance_esperado_pct"] = expected
    out["brecha_pct"] = (out["avance_esperado_pct"] - out["avance_real_pct"]).round(2)

    risk_rows = out.apply(lambda r: _risk_model(r, inactive_days_threshold), axis=1, result_type="expand")
    risk_rows.columns = ["puntaje_riesgo", "nivel_riesgo", "causa_principal_riesgo", "causas_riesgo", "recomendacion"]
    out = pd.concat([out, risk_rows], axis=1)
    return out


def _risk_model(row: pd.Series, inactive_days_threshold: int):
    score = 0
    causes = []

    if bool(row.get("nunca_ingreso")):
        score += 40
        causes.append("Falta de ingreso al curso")
    if bool(row.get("ingreso_no_inicio")):
        score += 35
        causes.append("Ingresó pero no inició actividades")
    if bool(row.get("inicio_y_modulo_1")):
        score += 15
        causes.append("Se quedó en el primer módulo")

    brecha = float(row.get("brecha_pct") or 0)
    if brecha >= 30:
        score += 30
        causes.append("Avance insuficiente")
    elif brecha >= 15:
        score += 15
        causes.append("Brecha moderada de avance")

    dias = row.get("dias_sin_actividad")
    try:
        dias_val = int(dias) if dias is not None and not pd.isna(dias) else None
    except Exception:
        dias_val = None
    if dias_val is not None and dias_val >= inactive_days_threshold:
        score += 20
        causes.append("Inactividad reciente")

    pendientes = row.get("actividades_pendientes")
    total = row.get("actividades_total")
    try:
        if pendientes is not None and total and float(total) > 0:
            pending_ratio = float(pendientes) / float(total)
            if pending_ratio >= 0.70:
                score += 20
                causes.append("Actividades pendientes")
            elif pending_ratio >= 0.40:
                score += 10
                causes.append("Pendientes moderados")
    except Exception:
        pass

    score = int(min(100, score))
    if score >= 61:
        level = "Alto"
    elif score >= 31:
        level = "Medio"
    else:
        level = "Bajo"

    if len(causes) >= 2:
        principal = "Combinación de factores"
    elif causes:
        principal = causes[0]
    else:
        principal = "Avance adecuado"

    recommendation = _recommendation(level, principal)
    return score, level, principal, "; ".join(causes) if causes else "Sin alertas críticas", recommendation


def _recommendation(level: str, principal: str) -> str:
    if principal == "Falta de ingreso al curso":
        return "Contactar de inmediato para verificar acceso, credenciales y comprensión inicial de la plataforma."
    if principal == "Ingresó pero no inició actividades":
        return "Enviar orientación específica sobre la primera actividad y confirmar que comprende qué debe realizar."
    if principal == "Combinación de factores":
        return "Priorizar seguimiento personalizado y registrar intervención académica con compromiso de avance."
    if principal == "Avance insuficiente":
        return "Revisar actividades pendientes y acordar un plan corto de recuperación."
    if principal == "Se quedó en el primer módulo":
        return "Verificar si existe dificultad conceptual o de navegación en el primer módulo."
    if level == "Medio":
        return "Dar seguimiento preventivo y monitorear avance en el próximo corte."
    return "Mantener monitoreo regular."


def build_summary(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "total_estudiantes": 0,
            "avance_esperado_promedio": 0,
            "avance_real_promedio": 0,
            "brecha_promedio": 0,
            "riesgo_bajo": 0,
            "riesgo_medio": 0,
            "riesgo_alto": 0,
            "nunca_ingreso": 0,
            "ingreso_no_inicio": 0,
            "modulo_1": 0,
            "avance_parcial": 0,
            "avance_insuficiente": 0,
            "actividades_pendientes": 0,
            "combinacion_factores": 0,
        }

    def count_col_bool(col):
        return int(df[col].sum()) if col in df.columns else 0

    return {
        "total_estudiantes": int(len(df)),
        "avance_esperado_promedio": round(float(df.get("avance_esperado_pct", pd.Series([0])).mean()), 2),
        "avance_real_promedio": round(float(df["avance_real_pct"].mean()), 2),
        "brecha_promedio": round(float(df.get("brecha_pct", pd.Series([0])).mean()), 2),
        "riesgo_bajo": int((df.get("nivel_riesgo") == "Bajo").sum()) if "nivel_riesgo" in df else 0,
        "riesgo_medio": int((df.get("nivel_riesgo") == "Medio").sum()) if "nivel_riesgo" in df else 0,
        "riesgo_alto": int((df.get("nivel_riesgo") == "Alto").sum()) if "nivel_riesgo" in df else 0,
        "nunca_ingreso": count_col_bool("nunca_ingreso"),
        "ingreso_no_inicio": count_col_bool("ingreso_no_inicio"),
        "modulo_1": count_col_bool("inicio_y_modulo_1"),
        "avance_parcial": int((df["estado_base"] == "Avance parcial registrado").sum()) if "estado_base" in df else 0,
        "avance_insuficiente": int((df.get("causas_riesgo", "").astype(str).str.contains("Avance insuficiente")).sum()) if "causas_riesgo" in df else 0,
        "actividades_pendientes": int((df.get("causas_riesgo", "").astype(str).str.contains("Actividades pendientes")).sum()) if "causas_riesgo" in df else 0,
        "combinacion_factores": int((df.get("causa_principal_riesgo") == "Combinación de factores").sum()) if "causa_principal_riesgo" in df else 0,
    }


def risk_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "causa_principal_riesgo" not in df.columns:
        return pd.DataFrame(columns=["causa_riesgo", "cantidad", "porcentaje"])
    ranking = df["causa_principal_riesgo"].fillna("Sin clasificación").value_counts().reset_index()
    ranking.columns = ["causa_riesgo", "cantidad"]
    ranking["porcentaje"] = (ranking["cantidad"] / len(df) * 100).round(2)
    return ranking


def section_comparison(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.groupby("curso_aula", dropna=False).agg(
        estudiantes=("canvas_user_id", "count"),
        avance_real_promedio=("avance_real_pct", "mean"),
        brecha_promedio=("brecha_pct", "mean"),
        riesgo_alto=("nivel_riesgo", lambda s: int((s == "Alto").sum())),
        riesgo_medio=("nivel_riesgo", lambda s: int((s == "Medio").sum())),
        nunca_ingreso=("nunca_ingreso", "sum"),
    ).reset_index().round(2)
