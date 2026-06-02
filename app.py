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

DEFAULT_STATE = {
    "canvas_token": "",
    "canvas_user_profile": None,
    "courses": [],
    "sections": [],
    "selected_canvas_course_ids": [],
    "selected_canvas_courses_df": pd.DataFrame(),
    "selected_section_ids": [],
    "selected_sections_df": pd.DataFrame(),
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def normalize_courses(courses):
    """Convierte la respuesta de Canvas en DataFrame limpio."""
    df = pd.DataFrame([
        {
            "canvas_course_id": c.get("id"),
            "nombre": c.get("name"),
            "codigo": c.get("course_code"),
            "estado": c.get("workflow_state"),
            "total_estudiantes": c.get("total_students"),
        }
        for c in courses
    ])

    if not df.empty:
        df["nombre"] = df["nombre"].fillna("Sin nombre")
        df["codigo"] = df["codigo"].fillna("")
        df = df.sort_values(by="nombre", na_position="last")

    return df


def normalize_sections(sections):
    """Convierte la respuesta de secciones Canvas en DataFrame limpio."""
    df = pd.DataFrame([
        {
            "canvas_section_id": s.get("id"),
            "nombre": s.get("name"),
            "canvas_course_id": s.get("course_id"),
            "sis_section_id": s.get("sis_section_id"),
            "total_estudiantes": len(s.get("students", [])) if s.get("students") else None,
        }
        for s in sections
    ])

    if not df.empty:
        df["nombre"] = df["nombre"].fillna("Sin nombre")
        df = df.sort_values(by="nombre", na_position="last")

    return df


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
        Fase 1: conexión con Canvas, conexión con Supabase y selección flexible de cursos/secciones.
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
        "2. Selección de cursos/secciones",
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
                st.session_state["selected_canvas_course_ids"] = []
                st.session_state["selected_section_ids"] = []

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
                st.session_state["selected_canvas_course_ids"] = []
                st.session_state["selected_section_ids"] = []
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
# SECCIÓN 2: SELECCIÓN FLEXIBLE
# ---------------------------------------------------------

elif menu == "2. Selección de cursos/secciones":
    st.header("2. Selección de cursos/secciones")

    st.markdown(
        """
        En Canvas, algunas veces cada sección aparece como una sección interna de un mismo curso;
        pero en otros casos cada sección aparece como un curso independiente, por ejemplo:
        `Matemáticas - SECCIÓN - 10`, `Matemáticas - SECCIÓN - 20`, etc.

        Por eso esta pantalla permite trabajar de dos formas:
        **seleccionar varias aulas/curso Canvas como secciones equivalentes**, o bien
        **consultar las secciones internas de un curso específico**.
        """
    )

    if not st.session_state.get("canvas_token"):
        st.warning("Primero debe ingresar y probar su token de Canvas en la sección de Configuración.")
        st.stop()

    if st.button("Cargar cursos desde Canvas"):
        ok, courses = get_canvas_courses()
        if ok:
            st.session_state["courses"] = courses
            st.session_state["sections"] = []
            st.session_state["selected_canvas_course_ids"] = []
            st.session_state["selected_section_ids"] = []
            st.success(f"Se cargaron {len(courses)} cursos desde Canvas.")
        else:
            st.error("No se pudieron cargar los cursos.")
            st.write(courses)

    courses = st.session_state.get("courses", [])

    if courses:
        courses_df = normalize_courses(courses)

        st.subheader("Cursos disponibles")

        filtro = st.text_input(
            "Filtrar cursos por nombre o código",
            placeholder="Ejemplo: Matemáticas, Comunicación, Experiencia Virtual"
        )

        courses_filtered = courses_df.copy()
        if filtro.strip():
            f = filtro.strip().lower()
            courses_filtered = courses_filtered[
                courses_filtered["nombre"].str.lower().str.contains(f, na=False) |
                courses_filtered["codigo"].astype(str).str.lower().str.contains(f, na=False)
            ]

        st.dataframe(courses_filtered, use_container_width=True)

        st.markdown("### A. Seleccionar varias aulas/curso Canvas como secciones del análisis")
        st.caption(
            "Use esta opción cuando Canvas le muestra cada sección como un curso separado. "
            "Esta parece ser la forma correcta para su caso, porque Matemáticas sección 10 aparece como un curso con 159 estudiantes."
        )

        course_options = {
            f'{row["nombre"]} | ID: {row["canvas_course_id"]}': int(row["canvas_course_id"])
            for _, row in courses_filtered.iterrows()
            if row["canvas_course_id"] is not None
        }

        selected_course_labels = st.multiselect(
            "Seleccione una o varias secciones/aulas Canvas para unificar el análisis",
            options=list(course_options.keys()),
            help="Puede seleccionar Matemáticas sección 10 y Matemáticas sección 20 para analizarlas como un solo curso consolidado."
        )

        selected_course_ids = [course_options[label] for label in selected_course_labels]
        st.session_state["selected_canvas_course_ids"] = selected_course_ids

        if selected_course_ids:
            selected_courses_df = courses_df[courses_df["canvas_course_id"].isin(selected_course_ids)].copy()
            st.session_state["selected_canvas_courses_df"] = selected_courses_df

            st.success(f"Se seleccionaron {len(selected_course_ids)} aula(s)/curso(s) Canvas para consolidar el análisis.")
            st.dataframe(selected_courses_df, use_container_width=True)

        st.divider()

        st.markdown("### B. Consultar secciones internas de un curso Canvas")
        st.caption(
            "Use esta opción solo si un mismo curso Canvas contiene varias secciones internas. "
            "Si el resultado muestra una sola sección, entonces debe usar la opción A."
        )

        internal_course_options = {
            f'{row["nombre"]} | ID: {row["canvas_course_id"]}': int(row["canvas_course_id"])
            for _, row in courses_filtered.iterrows()
            if row["canvas_course_id"] is not None
        }

        selected_internal_course_label = st.selectbox(
            "Seleccione un curso para consultar sus secciones internas",
            options=list(internal_course_options.keys())
        )

        selected_internal_course_id = internal_course_options[selected_internal_course_label]

        if st.button("Cargar secciones internas del curso seleccionado"):
            ok, sections = get_course_sections(selected_internal_course_id)
            if ok:
                st.session_state["sections"] = sections
                st.success(f"Se cargaron {len(sections)} sección(es) interna(s) del curso.")
            else:
                st.error("No se pudieron cargar las secciones internas.")
                st.write(sections)

    sections = st.session_state.get("sections", [])

    if sections:
        sections_df = normalize_sections(sections)

        st.subheader("Secciones internas disponibles")
        st.dataframe(sections_df, use_container_width=True)

        section_options = {
            f'{row["nombre"]} | ID: {row["canvas_section_id"]}': int(row["canvas_section_id"])
            for _, row in sections_df.iterrows()
            if row["canvas_section_id"] is not None
        }

        selected_sections = st.multiselect(
            "Seleccione una o varias secciones internas para el análisis",
            options=list(section_options.keys())
        )

        selected_section_ids = [section_options[item] for item in selected_sections]
        st.session_state["selected_section_ids"] = selected_section_ids

        if selected_section_ids:
            selected_sections_df = sections_df[sections_df["canvas_section_id"].isin(selected_section_ids)].copy()
            st.session_state["selected_sections_df"] = selected_sections_df
            st.success(f"Se seleccionaron {len(selected_section_ids)} sección(es) interna(s) para el análisis.")
            st.dataframe(selected_sections_df, use_container_width=True)

    st.divider()
    st.subheader("Resumen de selección actual")

    selected_course_ids = st.session_state.get("selected_canvas_course_ids", [])
    selected_section_ids = st.session_state.get("selected_section_ids", [])

    col_a, col_b = st.columns(2)

    with col_a:
        st.metric("Aulas/cursos Canvas seleccionados", len(selected_course_ids))
        if selected_course_ids:
            st.write(selected_course_ids)

    with col_b:
        st.metric("Secciones internas seleccionadas", len(selected_section_ids))
        if selected_section_ids:
            st.write(selected_section_ids)

    if selected_course_ids or selected_section_ids:
        st.success("La selección quedó guardada en la sesión. En Fase 2 se usará para traer estudiantes y métricas.")
    else:
        st.info("Seleccione al menos una aula/curso Canvas o una sección interna para dejar listo el análisis.")


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
            {"Elemento": "Selección múltiple de cursos Canvas como secciones", "Estado": "Implementada"},
            {"Elemento": "Consulta de secciones internas Canvas", "Estado": "Implementada"},
            {"Elemento": "Cálculo de indicadores", "Estado": "Pendiente Fase 2"},
            {"Elemento": "Reporte PDF", "Estado": "Pendiente Fase 4"},
        ]
    )

    st.dataframe(checklist, use_container_width=True)

    st.info(
        """
        Esta versión corrige el caso donde Canvas maneja cada sección como un curso/aula independiente.
        Ahora puede seleccionar varias aulas Canvas y consolidarlas como secciones de un mismo análisis.
        """
    )
