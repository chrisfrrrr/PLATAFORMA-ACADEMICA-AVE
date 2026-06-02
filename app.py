import streamlit as st
import pandas as pd

from modules.canvas_client import (
    CANVAS_BASE_URL,
    test_canvas_connection,
    get_canvas_courses,
    get_course_sections
)
from modules.supabase_client import test_supabase_connection
from modules.ui_styles import apply_ave_styles


st.set_page_config(
    page_title="Plataforma Académica AVE",
    page_icon="📊",
    layout="wide"
)

apply_ave_styles()


# ---------------------------------------------------------
# ESTADO INICIAL
# ---------------------------------------------------------

if "canvas_token" not in st.session_state:
    st.session_state["canvas_token"] = ""

if "canvas_user_profile" not in st.session_state:
    st.session_state["canvas_user_profile"] = None


# ---------------------------------------------------------
# ENCABEZADO
# ---------------------------------------------------------

col_logo, col_title = st.columns([1, 5])

with col_logo:
    try:
        st.image("assets/logo_ave.jpg", width=150)
    except Exception:
        st.info("Logo AVE no encontrado en assets/logo_ave.jpg")

with col_title:
    st.markdown(
        """
        <div class="ave-title">Plataforma Académica AVE UVG</div>
        <div class="ave-subtitle">
        Fase 1: conexión con Canvas, conexión con Supabase y carga inicial de cursos y secciones.
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("AVE UVG")
st.sidebar.caption("Análisis académico integrado")

if st.session_state.get("canvas_token"):
    st.sidebar.success("Token Canvas cargado en esta sesión")
else:
    st.sidebar.warning("Token Canvas pendiente")

menu = st.sidebar.radio(
    "Menú principal",
    [
        "1. Configuración",
        "2. Selección de curso y secciones",
        "3. Resumen de Fase 1"
    ]
)


# ---------------------------------------------------------
# SECCIÓN 1: CONFIGURACIÓN
# ---------------------------------------------------------

if menu == "1. Configuración":
    st.header("1. Configuración de conexiones")

    st.markdown(
        """
        En esta sección se valida que la aplicación pueda conectarse correctamente
        con Canvas LMS y con Supabase. El token de Canvas se ingresa desde esta pantalla
        para que cada asesor pueda utilizar su propio acceso sin editar archivos internos.
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Canvas LMS")
        st.caption("Enlace institucional configurado de fábrica")
        st.code(CANVAS_BASE_URL, language="text")

        canvas_token_input = st.text_input(
            "Token personal de Canvas",
            value=st.session_state.get("canvas_token", ""),
            type="password",
            placeholder="Pegue aquí su token de Canvas",
            help="El token queda guardado únicamente durante la sesión activa de Streamlit. No se escribe en el código ni en secrets.toml."
        )

        c1, c2 = st.columns([1, 1])

        with c1:
            if st.button("Guardar token en sesión"):
                st.session_state["canvas_token"] = canvas_token_input.strip()
                st.session_state["courses"] = []
                st.session_state["sections"] = []
                st.session_state["canvas_user_profile"] = None

                if st.session_state["canvas_token"]:
                    st.success("Token guardado para esta sesión.")
                else:
                    st.warning("Debe ingresar un token válido.")

        with c2:
            if st.button("Limpiar token"):
                st.session_state["canvas_token"] = ""
                st.session_state["canvas_user_profile"] = None
                st.session_state["courses"] = []
                st.session_state["sections"] = []
                st.warning("Token eliminado de la sesión.")

        if st.button("Probar conexión con Canvas"):
            st.session_state["canvas_token"] = canvas_token_input.strip()
            ok, result = test_canvas_connection()
            if ok:
                st.session_state["canvas_user_profile"] = result
                st.success("Conexión con Canvas exitosa.")

                perfil = {
                    "id": result.get("id"),
                    "nombre": result.get("name"),
                    "correo": result.get("primary_email"),
                    "login": result.get("login_id")
                }
                st.json(perfil)
            else:
                st.error("No se pudo conectar con Canvas.")
                st.write(result)

    with col2:
        st.subheader("Supabase")
        st.markdown(
            """
            La conexión de Supabase se mantiene en `secrets.toml` porque corresponde
            a la base de datos institucional de la aplicación.
            """
        )

        if st.button("Probar conexión con Supabase"):
            ok, result = test_supabase_connection()
            if ok:
                st.success(result)
            else:
                st.error("No se pudo conectar con Supabase.")
                st.write(result)


# ---------------------------------------------------------
# SECCIÓN 2: SELECCIÓN DE CURSO Y SECCIONES
# ---------------------------------------------------------

elif menu == "2. Selección de curso y secciones":
    st.header("2. Selección de curso y secciones")

    st.markdown(
        """
        En esta sección se cargan los cursos disponibles desde Canvas.
        Luego se selecciona un curso y se consultan sus secciones.
        """
    )

    if not st.session_state.get("canvas_token"):
        st.warning("Primero debe ingresar y probar su token de Canvas en la sección de Configuración.")
        st.stop()

    if "courses" not in st.session_state:
        st.session_state["courses"] = []

    if "sections" not in st.session_state:
        st.session_state["sections"] = []

    if st.button("Cargar cursos desde Canvas"):
        ok, courses = get_canvas_courses()
        if ok:
            st.session_state["courses"] = courses
            st.session_state["sections"] = []
            st.success(f"Se cargaron {len(courses)} cursos desde Canvas.")
        else:
            st.error("No se pudieron cargar los cursos.")
            st.write(courses)

    courses = st.session_state["courses"]

    if courses:
        courses_df = pd.DataFrame([
            {
                "id": c.get("id"),
                "nombre": c.get("name"),
                "codigo": c.get("course_code"),
                "estado": c.get("workflow_state"),
                "total_estudiantes": c.get("total_students")
            }
            for c in courses
        ])

        courses_df = courses_df.sort_values(by="nombre", na_position="last")

        st.subheader("Cursos disponibles")
        st.dataframe(courses_df, use_container_width=True)

        course_options = {
            f'{row["nombre"]} | ID: {row["id"]}': row["id"]
            for _, row in courses_df.iterrows()
            if row["nombre"]
        }

        selected_course_label = st.selectbox(
            "Seleccione el curso a analizar",
            options=list(course_options.keys())
        )

        selected_course_id = course_options[selected_course_label]
        st.session_state["selected_course_id"] = selected_course_id
        st.session_state["selected_course_label"] = selected_course_label

        st.info(f"Curso seleccionado: {selected_course_label}")

        if st.button("Cargar secciones del curso seleccionado"):
            ok, sections = get_course_sections(selected_course_id)
            if ok:
                st.session_state["sections"] = sections
                st.success(f"Se cargaron {len(sections)} secciones del curso.")
            else:
                st.error("No se pudieron cargar las secciones.")
                st.write(sections)

    sections = st.session_state["sections"]

    if sections:
        sections_df = pd.DataFrame([
            {
                "id": s.get("id"),
                "nombre": s.get("name"),
                "course_id": s.get("course_id"),
                "sis_section_id": s.get("sis_section_id"),
                "total_estudiantes": len(s.get("students", [])) if s.get("students") else None
            }
            for s in sections
        ])

        st.subheader("Secciones disponibles")
        st.dataframe(sections_df, use_container_width=True)

        section_options = {
            f'{row["nombre"]} | ID: {row["id"]}': row["id"]
            for _, row in sections_df.iterrows()
            if row["nombre"]
        }

        selected_sections = st.multiselect(
            "Seleccione una o varias secciones para el análisis",
            options=list(section_options.keys())
        )

        selected_section_ids = [section_options[item] for item in selected_sections]
        st.session_state["selected_section_ids"] = selected_section_ids

        if selected_section_ids:
            st.success(f"Se seleccionaron {len(selected_section_ids)} sección(es) para el análisis.")
            st.write("IDs seleccionados:")
            st.write(selected_section_ids)


# ---------------------------------------------------------
# SECCIÓN 3: RESUMEN DE FASE 1
# ---------------------------------------------------------

elif menu == "3. Resumen de Fase 1":
    st.header("3. Resumen de avance de Fase 1")

    checklist = pd.DataFrame(
        [
            {"Elemento": "Estructura del proyecto", "Estado": "Definido"},
            {"Elemento": "Colores institucionales AVE", "Estado": "Configurado"},
            {"Elemento": "Token Canvas desde interfaz", "Estado": "Implementado"},
            {"Elemento": "Conexión Canvas", "Estado": "Implementada"},
            {"Elemento": "Conexión Supabase", "Estado": "Implementada"},
            {"Elemento": "Carga de cursos", "Estado": "Implementada"},
            {"Elemento": "Carga de secciones", "Estado": "Implementada"},
            {"Elemento": "Selección múltiple de secciones", "Estado": "Implementada"},
            {"Elemento": "Cálculo de indicadores", "Estado": "Pendiente Fase 2"},
            {"Elemento": "Reporte PDF", "Estado": "Pendiente Fase 4"}
        ]
    )

    st.dataframe(checklist, use_container_width=True)

    st.info(
        """
        Al terminar esta fase, la aplicación ya debería permitir que cada asesor ingrese
        su propio token de Canvas desde la interfaz, conectarse con Canvas, conectarse con
        Supabase y seleccionar cursos/secciones de manera flexible.
        """
    )
