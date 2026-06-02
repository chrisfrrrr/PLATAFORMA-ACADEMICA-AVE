import requests
import streamlit as st

CANVAS_BASE_URL = "https://uvg.instructure.com"


def get_canvas_config():
    """
    Obtiene la configuración de Canvas.
    El enlace institucional queda fijo de fábrica y el token se toma desde
    st.session_state para que cada asesor lo ingrese desde la interfaz.
    """
    base_url = CANVAS_BASE_URL.rstrip("/")
    token = st.session_state.get("canvas_token", "").strip()

    if not token:
        raise ValueError("Debe ingresar un token de Canvas antes de consultar la API.")

    return base_url, token


def canvas_headers(token):
    """Encabezados de autorización para Canvas."""
    return {"Authorization": f"Bearer {token}"}


def test_canvas_connection():
    """Prueba la conexión con Canvas consultando el perfil del usuario autenticado."""
    try:
        base_url, token = get_canvas_config()
        url = f"{base_url}/api/v1/users/self/profile"
        response = requests.get(url, headers=canvas_headers(token), timeout=15)

        if response.status_code == 200:
            return True, response.json()

        return False, {"status_code": response.status_code, "message": response.text}
    except Exception as e:
        return False, str(e)


def get_canvas_courses():
    """Obtiene los cursos disponibles para el usuario autenticado."""
    try:
        base_url, token = get_canvas_config()
        url = f"{base_url}/api/v1/courses"
        params = {
            "per_page": 100,
            "include[]": ["term", "total_students"]
        }
        courses = []

        while url:
            response = requests.get(url, headers=canvas_headers(token), params=params, timeout=20)
            if response.status_code != 200:
                return False, {"status_code": response.status_code, "message": response.text}

            courses.extend(response.json())
            url = response.links.get("next", {}).get("url")
            params = None

        return True, courses
    except Exception as e:
        return False, str(e)


def get_course_sections(course_id):
    """Obtiene las secciones de un curso específico en Canvas."""
    try:
        base_url, token = get_canvas_config()
        url = f"{base_url}/api/v1/courses/{course_id}/sections"
        params = {
            "per_page": 100,
            "include[]": ["students"]
        }
        sections = []

        while url:
            response = requests.get(url, headers=canvas_headers(token), params=params, timeout=20)
            if response.status_code != 200:
                return False, {"status_code": response.status_code, "message": response.text}

            sections.extend(response.json())
            url = response.links.get("next", {}).get("url")
            params = None

        return True, sections
    except Exception as e:
        return False, str(e)
