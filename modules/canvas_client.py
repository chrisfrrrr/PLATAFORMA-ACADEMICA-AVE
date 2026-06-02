from __future__ import annotations

import requests
import streamlit as st
from typing import Any, Dict, List, Tuple, Optional

CANVAS_BASE_URL = "https://uvg.instructure.com"


def get_canvas_token() -> Optional[str]:
    return st.session_state.get("canvas_token")


def canvas_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _safe_canvas_message(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            if "errors" in data:
                return str(data.get("errors"))[:700]
            if "message" in data:
                return str(data.get("message"))[:700]
            return str(data)[:700]
        return str(data)[:700]
    except Exception:
        return response.text[:700]


def _paginate(url: str, token: str, params: Optional[dict] = None, timeout: int = 30) -> Tuple[bool, Any]:
    """Consulta endpoints Canvas con paginación Link header."""
    rows: List[Any] = []
    try:
        first_url = url
        while url:
            response = requests.get(url, headers=canvas_headers(token), params=params, timeout=timeout)
            if response.status_code != 200:
                return False, {
                    "status_code": response.status_code,
                    "message": _safe_canvas_message(response),
                    "url": first_url,
                }
            data = response.json()
            if isinstance(data, list):
                rows.extend(data)
            else:
                return True, data
            url = response.links.get("next", {}).get("url")
            params = None
        return True, rows
    except Exception as e:
        return False, {"status_code": "EXCEPTION", "message": str(e), "url": url}


def _format_warning(endpoint_name: str, detail: Any) -> str:
    if isinstance(detail, dict):
        code = detail.get("status_code", "sin código")
        msg = detail.get("message", "sin mensaje")
        return f"No se pudo cargar {endpoint_name}. Código Canvas: {code}. Detalle: {msg}"
    return f"No se pudo cargar {endpoint_name}. Detalle: {detail}"


def test_canvas_connection(token: Optional[str] = None):
    token = token or get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/users/self/profile"
    try:
        response = requests.get(url, headers=canvas_headers(token), timeout=15)
        if response.status_code == 200:
            return True, response.json()
        return False, {"status_code": response.status_code, "message": _safe_canvas_message(response)}
    except Exception as e:
        return False, str(e)


def get_canvas_courses():
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses"
    params = {"per_page": 100, "include[]": ["term", "total_students"]}
    return _paginate(url, token, params=params)


def get_course_sections(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/sections"
    params = {"per_page": 100, "include[]": ["students"]}
    return _paginate(url, token, params=params)


def get_course_enrollments(course_id: int):
    """Trae estudiantes inscritos y datos base de actividad desde Canvas."""
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/enrollments"
    params = {
        "per_page": 100,
        "type[]": "StudentEnrollment",
        "state[]": ["active", "invited", "creation_pending", "completed"],
        "include[]": ["user", "total_activity_time", "last_activity_at", "section"],
    }
    return _paginate(url, token, params=params)


def get_course_users(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/users"
    params = {"per_page": 100, "enrollment_type[]": "student", "include[]": ["email", "enrollments"]}
    return _paginate(url, token, params=params)


def get_course_assignments(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
    params = {"per_page": 100, "order_by": "position", "include[]": ["assignment_visibility"]}
    return _paginate(url, token, params=params)


def get_course_modules(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/modules"
    params = {"per_page": 100, "include[]": ["items"]}
    return _paginate(url, token, params=params)


def get_course_submissions(course_id: int):
    """
    Trae entregas de todos los estudiantes.
    Endpoint Canvas: /courses/:course_id/students/submissions grouped=true.
    """
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/students/submissions"
    params = {
        "per_page": 100,
        "student_ids[]": "all",
        "grouped": "true",
        "include[]": ["assignment"],
    }
    return _paginate(url, token, params=params, timeout=45)


def get_course_submissions_ungrouped(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/students/submissions"
    params = {"per_page": 100, "student_ids[]": "all", "include[]": ["assignment"]}
    return _paginate(url, token, params=params, timeout=45)


def get_assignment_submissions(course_id: int, assignment_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
    params = {"per_page": 100, "include[]": ["user"]}
    return _paginate(url, token, params=params, timeout=45)


def get_submissions_by_assignments(course_id: int, assignments: List[dict], max_assignments: Optional[int] = None):
    """Fallback: intenta traer entregas tarea por tarea."""
    all_rows: List[dict] = []
    tested = 0
    errors: List[Any] = []
    assignment_list = [a for a in assignments or [] if a.get("id")]
    if max_assignments:
        assignment_list = assignment_list[:max_assignments]
    for assignment in assignment_list:
        tested += 1
        ok, rows = get_assignment_submissions(course_id, int(assignment["id"]))
        if ok:
            for row in rows:
                row["assignment_id"] = row.get("assignment_id") or assignment.get("id")
                row["assignment"] = row.get("assignment") or assignment
                all_rows.append(row)
        else:
            errors.append({"assignment_id": assignment.get("id"), "error": rows})
            # Si falla por permisos desde la primera tarea, no seguimos castigando el API.
            if tested == 1:
                return False, {"tested_assignments": tested, "errors": errors[:3]}
    if all_rows:
        return True, all_rows
    if errors:
        return False, {"tested_assignments": tested, "errors": errors[:3], "message": "No se obtuvieron entregas por tarea."}
    return True, []


def run_canvas_diagnostics(course_id: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Prueba endpoints clave para identificar permisos reales del token."""
    results: List[Dict[str, Any]] = []
    details: Dict[str, Any] = {}

    def add_result(name: str, ok: bool, data: Any, endpoint: str):
        count = len(data) if ok and isinstance(data, list) else (1 if ok and data else 0)
        sample_keys = []
        if ok and isinstance(data, list) and data:
            sample_keys = list(data[0].keys())[:12] if isinstance(data[0], dict) else []
        elif ok and isinstance(data, dict):
            sample_keys = list(data.keys())[:12]
        if ok:
            status = "Disponible"
            message = f"Datos recibidos: {count}"
        else:
            status = "No disponible"
            if isinstance(data, dict):
                message = f'Código: {data.get("status_code", "sin código")}. {data.get("message", "")}'
            else:
                message = str(data)
        results.append({
            "recurso": name,
            "estado": status,
            "registros": count,
            "endpoint": endpoint,
            "detalle": message[:450],
            "campos_muestra": ", ".join(sample_keys),
        })
        details[name] = data

    ok, profile = test_canvas_connection()
    add_result("Perfil del usuario", ok, profile, "/users/self/profile")

    ok, enrollments = get_course_enrollments(course_id)
    add_result("Inscripciones / estudiantes con actividad", ok, enrollments, "/courses/:course_id/enrollments")

    ok, users = get_course_users(course_id)
    add_result("Usuarios estudiantes del curso", ok, users, "/courses/:course_id/users")

    ok, assignments = get_course_assignments(course_id)
    add_result("Actividades / assignments", ok, assignments, "/courses/:course_id/assignments")

    ok, modules = get_course_modules(course_id)
    add_result("Módulos con items", ok, modules, "/courses/:course_id/modules")

    ok, submissions_grouped = get_course_submissions(course_id)
    add_result("Entregas generales agrupadas", ok, submissions_grouped, "/courses/:course_id/students/submissions?grouped=true")

    ok, submissions_ungrouped = get_course_submissions_ungrouped(course_id)
    add_result("Entregas generales sin agrupar", ok, submissions_ungrouped, "/courses/:course_id/students/submissions")

    first_assignment_id = None
    if isinstance(assignments, list) and assignments:
        first_assignment_id = assignments[0].get("id")
    if first_assignment_id:
        ok, assignment_subs = get_assignment_submissions(course_id, int(first_assignment_id))
        add_result("Entregas por actividad individual", ok, assignment_subs, "/courses/:course_id/assignments/:assignment_id/submissions")
    else:
        add_result("Entregas por actividad individual", False, "No hay assignments disponibles para probar.", "/courses/:course_id/assignments/:assignment_id/submissions")

    return results, details


def collect_course_dataset(course_id: int, course_name: str):
    """Recopila estudiantes, tareas, módulos y entregas de un aula Canvas."""
    payload: Dict[str, Any] = {"course_id": course_id, "course_name": course_name}

    ok, enrollments = get_course_enrollments(course_id)
    if not ok:
        return False, {"step": "enrollments", "detail": enrollments, "course_id": course_id}
    payload["enrollments"] = enrollments

    ok, assignments = get_course_assignments(course_id)
    if not ok:
        payload["assignments_warning"] = _format_warning("actividades", assignments)
        assignments = []
    payload["assignments"] = assignments

    ok, modules = get_course_modules(course_id)
    if not ok:
        payload["modules_warning"] = _format_warning("módulos", modules)
        modules = []
    payload["modules"] = modules

    ok, submissions = get_course_submissions(course_id)
    if not ok:
        general_error = submissions
        # Fallback: si hay tareas, intenta obtener entregas tarea por tarea.
        ok_fallback, fallback_rows = get_submissions_by_assignments(course_id, assignments)
        if ok_fallback:
            submissions = fallback_rows
            payload["submissions_warning"] = (
                "El endpoint general de entregas no respondió, pero se pudieron cargar entregas por actividad individual."
            )
        else:
            submissions = []
            payload["submissions_warning"] = (
                _format_warning("entregas por endpoint general", general_error)
                + " | Fallback por actividad: "
                + _format_warning("entregas por actividad individual", fallback_rows)
            )
    payload["submissions"] = submissions

    return True, payload
