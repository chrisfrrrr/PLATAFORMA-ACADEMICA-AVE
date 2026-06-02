from __future__ import annotations

import requests
import streamlit as st
from typing import Any, Dict, List, Tuple, Optional

CANVAS_BASE_URL = "https://uvg.instructure.com"


def get_canvas_token() -> Optional[str]:
    return st.session_state.get("canvas_token")


def canvas_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _paginate(url: str, token: str, params: Optional[dict] = None, timeout: int = 30) -> Tuple[bool, Any]:
    """Consulta endpoints Canvas con paginación Link header."""
    rows: List[Any] = []
    try:
        while url:
            response = requests.get(url, headers=canvas_headers(token), params=params, timeout=timeout)
            if response.status_code != 200:
                return False, {"status_code": response.status_code, "message": response.text, "url": url}
            data = response.json()
            if isinstance(data, list):
                rows.extend(data)
            else:
                return True, data
            url = response.links.get("next", {}).get("url")
            params = None
        return True, rows
    except Exception as e:
        return False, str(e)


def test_canvas_connection(token: Optional[str] = None):
    token = token or get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/users/self/profile"
    try:
        response = requests.get(url, headers=canvas_headers(token), timeout=15)
        if response.status_code == 200:
            return True, response.json()
        return False, {"status_code": response.status_code, "message": response.text}
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


def get_course_assignments(course_id: int):
    token = get_canvas_token()
    if not token:
        return False, "No hay token de Canvas cargado en la sesión."
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
    params = {
        "per_page": 100,
        "bucket": "future",
        "include[]": ["submission", "assignment_visibility"],
        "order_by": "position",
    }
    # bucket=future puede ser restrictivo en algunos Canvas, por eso usamos endpoint general si falla desde app.
    ok, result = _paginate(url, token, params=params)
    if ok:
        return ok, result
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
    params = {"per_page": 100, "order_by": "position"}
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
    Trae entregas de todos los estudiantes. En cursos grandes puede tardar.
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


def collect_course_dataset(course_id: int, course_name: str):
    """Recopila estudiantes, tareas, módulos y entregas de un aula Canvas."""
    payload: Dict[str, Any] = {"course_id": course_id, "course_name": course_name}

    ok, enrollments = get_course_enrollments(course_id)
    if not ok:
        return False, {"step": "enrollments", "detail": enrollments, "course_id": course_id}
    payload["enrollments"] = enrollments

    ok, assignments = get_course_assignments(course_id)
    if not ok:
        assignments = []
        payload["assignments_warning"] = "No se pudieron cargar actividades. Se continuará con datos de acceso."
    payload["assignments"] = assignments

    ok, modules = get_course_modules(course_id)
    if not ok:
        modules = []
        payload["modules_warning"] = "No se pudieron cargar módulos. Se continuará sin módulo máximo."
    payload["modules"] = modules

    ok, submissions = get_course_submissions(course_id)
    if not ok:
        submissions = []
        payload["submissions_warning"] = "No se pudieron cargar entregas. Se continuará con datos de acceso."
    payload["submissions"] = submissions

    return True, payload
