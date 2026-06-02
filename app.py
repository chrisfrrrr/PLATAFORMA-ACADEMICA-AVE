from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from modules.canvas_client import (
    CANVAS_BASE_URL,
    test_canvas_connection,
    get_canvas_courses,
    get_course_sections,
    collect_course_dataset,
)
from modules.supabase_client import test_supabase_connection
from modules.academic_metrics import consolidate_datasets, build_summary
from modules.ui_styles import apply_ave_styles, AVE_COLORS, metric_card

st.set_page_config(
    page_title="Plataforma Académica AVE - Fase 2",
    page_icon="📊",
    layout="wide",
)
apply_ave_styles()

# -------------------------------------------------------------------
# Estado de sesión
# -------------------------------------------------------------------
st.session_state.setdefault("canvas_token", "")
st.session_state.setdefault("courses", [])
st.session_state.setdefault("selected_course_ids", [])
st.session_state.setdefault("selected_course_labels", [])
st.session_state.setdefault("datasets", [])
st.session_state.setdefault("student_metrics_df", pd.DataFrame())

# -------------------------------------------------------------------
# Encabezado
# -------------------------------------------------------------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("assets/logo_ave.jpg", width=150)
with col_title:
    st.markdown(
        """
        <div class="ave-title">Plataforma Académica AVE UVG</div>
        <div class="ave-subtitle">
        Fase 2: carga de estudiantes, accesos, actividades, módulos y avance real desde Canvas.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------
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
        "2. Selección de aulas/secciones",
        "3. Carga académica Fase 2",
        "4. Dashboard inicial",
        "5. Resumen de Fase 2",
    ],
)

# -------------------------------------------------------------------
# 1. Configuración
# -------------------------------------------------------------------
if menu == "1. Configuración":
    st.header("1. Configuración de conexiones")
    st.write("En esta fase, cada asesor puede ingresar su token de Canvas directamente desde la aplicación.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Canvas LMS")
        st.code(CANVAS_BASE_URL, language="text")
        token_input = st.text_input(
            "Ingrese token personal de Canvas",
            value=st.session_state.get("canvas_token", ""),
            type="password",
            help="El token se guarda únicamente durante la sesión activa de Streamlit.",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Guardar token en sesión"):
                st.session_state["canvas_token"] = token_input.strip()
                st.success("Token guardado en esta sesión.")
        with c2:
            if st.button("Limpiar token"):
                st.session_state["canvas_token"] = ""
                st.warning("Token eliminado de la sesión.")

        if st.button("Probar conexión con Canvas"):
            ok, result = test_canvas_connection(token_input.strip() or None)
            if ok:
                st.success("Conexión con Canvas exitosa.")
                st.json(result)
            else:
                st.error("No se pudo conectar con Canvas.")
                st.write(result)

    with col2:
        st.subheader("Supabase")
        st.write("Supabase se mantiene en secrets porque representa la base institucional.")
        if st.button("Probar conexión con Supabase"):
            ok, result = test_supabase_connection()
            if ok:
                st.success(result)
            else:
                st.error("No se pudo conectar con Supabase.")
                st.write(result)

# -------------------------------------------------------------------
# 2. Selección de aulas/secciones
# -------------------------------------------------------------------
elif menu == "2. Selección de aulas/secciones":
    st.header("2. Selección de aulas Canvas que se unificarán como secciones")
    st.info(
        "En AVE, muchas secciones aparecen como cursos/aulas Canvas independientes. "
        "Por eso aquí puedes seleccionar varias aulas y analizarlas juntas como un mismo curso académico."
    )

    if st.button("Cargar cursos desde Canvas"):
        ok, courses = get_canvas_courses()
        if ok:
            st.session_state["courses"] = courses
            st.success(f"Se cargaron {len(courses)} cursos desde Canvas.")
        else:
            st.error("No se pudieron cargar los cursos.")
            st.write(courses)

    courses = st.session_state.get("courses", [])
    if courses:
        courses_df = pd.DataFrame([
            {
                "id": c.get("id"),
                "nombre": c.get("name"),
                "codigo": c.get("course_code"),
                "estado": c.get("workflow_state"),
                "total_estudiantes": c.get("total_students"),
            }
            for c in courses if c.get("name")
        ])
        filtro = st.text_input("Filtrar cursos por nombre", value="")
        if filtro:
            view_df = courses_df[courses_df["nombre"].str.contains(filtro, case=False, na=False)]
        else:
            view_df = courses_df

        st.dataframe(view_df, use_container_width=True, height=280)

        options = {f'{r["nombre"]} | ID: {r["id"]}': int(r["id"]) for _, r in view_df.iterrows()}
        selected = st.multiselect(
            "Seleccione una o varias aulas/secciones Canvas para consolidar",
            options=list(options.keys()),
            default=st.session_state.get("selected_course_labels", []),
        )
        st.session_state["selected_course_labels"] = selected
        st.session_state["selected_course_ids"] = [options[s] for s in selected]

        if selected:
            st.success(f"Se seleccionaron {len(selected)} aula(s)/sección(es) para el análisis.")
            st.write(pd.DataFrame({"aula_seccion": selected, "canvas_course_id": st.session_state["selected_course_ids"]}))

        with st.expander("Opción avanzada: consultar secciones internas de un curso Canvas"):
            if selected:
                course_id_internal = st.selectbox("Seleccione un aula para consultar secciones internas", st.session_state["selected_course_ids"])
                if st.button("Consultar secciones internas"):
                    ok, sections = get_course_sections(course_id_internal)
                    if ok:
                        st.dataframe(pd.DataFrame(sections), use_container_width=True)
                    else:
                        st.error("No se pudieron consultar secciones internas.")
                        st.write(sections)
            else:
                st.caption("Primero seleccione al menos un aula Canvas.")

# -------------------------------------------------------------------
# 3. Carga académica Fase 2
# -------------------------------------------------------------------
elif menu == "3. Carga académica Fase 2":
    st.header("3. Carga de estudiantes, actividades, módulos y avance real")

    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])

    if not selected_ids:
        st.warning("Primero selecciona las aulas/secciones en el menú 2.")
        st.stop()

    st.subheader("Rango de análisis")
    today = date.today()
    fecha_inicio, fecha_fin = st.date_input(
        "Seleccione el rango de fechas del análisis",
        value=(today - timedelta(days=7), today),
        help="En esta fase se guarda como referencia del corte. En fases siguientes se usará para comparar reportes históricos.",
    )

    st.write("Aulas/secciones seleccionadas:")
    st.dataframe(pd.DataFrame({"aula_seccion": selected_labels, "canvas_course_id": selected_ids}), use_container_width=True)

    st.warning(
        "La carga puede tardar si el curso tiene muchos estudiantes o muchas actividades. "
        "Esta fase intenta traer inscripciones, tareas, módulos y entregas."
    )

    if st.button("Cargar datos académicos desde Canvas"):
        datasets = []
        progress = st.progress(0)
        status = st.empty()
        total = len(selected_ids)

        for idx, (course_id, label) in enumerate(zip(selected_ids, selected_labels), start=1):
            course_name = label.split(" | ID:")[0]
            status.info(f"Cargando {idx}/{total}: {course_name}")
            ok, payload = collect_course_dataset(course_id, course_name)
            if ok:
                datasets.append(payload)
                st.success(f"Datos cargados: {course_name}")
                for warning_key in ["assignments_warning", "modules_warning", "submissions_warning"]:
                    if payload.get(warning_key):
                        st.warning(f"{course_name}: {payload[warning_key]}")
            else:
                st.error(f"No se pudo cargar {course_name}")
                st.write(payload)
            progress.progress(idx / total)

        st.session_state["datasets"] = datasets
        df = consolidate_datasets(datasets, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        st.session_state["student_metrics_df"] = df

        if not df.empty:
            st.success(f"Carga completada. Se consolidaron {len(df)} registros de estudiantes.")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("No se generaron registros consolidados. Revisa permisos del token o endpoints de Canvas.")

# -------------------------------------------------------------------
# 4. Dashboard inicial
# -------------------------------------------------------------------
elif menu == "4. Dashboard inicial":
    st.header("4. Dashboard inicial de avance académico")
    df = st.session_state.get("student_metrics_df", pd.DataFrame())

    if df is None or df.empty:
        st.warning("Primero carga los datos académicos en el menú 3.")
        st.stop()

    summary = build_summary(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Total estudiantes", summary["total_estudiantes"], AVE_COLORS["azul"])
    with c2:
        metric_card("Avance promedio", f'{summary["avance_promedio"]}%', AVE_COLORS["celeste"])
    with c3:
        metric_card("Nunca ingresó", summary["nunca_ingreso"], AVE_COLORS["rojo"])
    with c4:
        metric_card("Ingresó no inició", summary["ingreso_no_inicio"], AVE_COLORS["amarillo"])
    with c5:
        metric_card("Detenido módulo 1", summary["modulo_1"], AVE_COLORS["verde"])

    st.subheader("Resumen por aula/sección")
    by_course = df.groupby("curso_aula", dropna=False).agg(
        estudiantes=("canvas_user_id", "count"),
        avance_promedio=("avance_real_pct", "mean"),
        nunca_ingreso=("nunca_ingreso", "sum"),
        ingreso_no_inicio=("ingreso_no_inicio", "sum"),
        modulo_1=("inicio_y_modulo_1", "sum"),
    ).reset_index()
    by_course["avance_promedio"] = by_course["avance_promedio"].round(2)
    st.dataframe(by_course, use_container_width=True)

    st.subheader("Distribución por estado base")
    estado_df = df["estado_base"].value_counts().reset_index()
    estado_df.columns = ["estado_base", "cantidad"]
    st.bar_chart(estado_df, x="estado_base", y="cantidad", use_container_width=True)

    st.subheader("Base individual de estudiantes")
    filtro_estado = st.multiselect("Filtrar por estado base", sorted(df["estado_base"].dropna().unique()))
    view = df.copy()
    if filtro_estado:
        view = view[view["estado_base"].isin(filtro_estado)]
    st.dataframe(view, use_container_width=True, height=420)

    csv = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Descargar base individual en CSV",
        data=csv,
        file_name="base_individual_fase2.csv",
        mime="text/csv",
    )

# -------------------------------------------------------------------
# 5. Resumen de Fase 2
# -------------------------------------------------------------------
elif menu == "5. Resumen de Fase 2":
    st.header("5. Resumen de avance de Fase 2")
    checklist = pd.DataFrame([
        {"Elemento": "Token Canvas desde interfaz", "Estado": "Implementado"},
        {"Elemento": "Selección multicurso/aulas como secciones", "Estado": "Implementado"},
        {"Elemento": "Carga de estudiantes por aula", "Estado": "Implementado"},
        {"Elemento": "Carga de último ingreso y tiempo de actividad", "Estado": "Implementado"},
        {"Elemento": "Carga de actividades/tareas", "Estado": "Implementado"},
        {"Elemento": "Carga de módulos", "Estado": "Implementado"},
        {"Elemento": "Carga de entregas/submissions", "Estado": "Implementado"},
        {"Elemento": "Cálculo de avance real básico", "Estado": "Implementado"},
        {"Elemento": "Clasificación base inicial", "Estado": "Implementado"},
        {"Elemento": "Riesgo académico con brecha esperada", "Estado": "Pendiente Fase 3"},
        {"Elemento": "Guardar cortes en Supabase", "Estado": "Pendiente Fase 3"},
        {"Elemento": "PDF ejecutivo", "Estado": "Pendiente Fase 4"},
    ])
    st.dataframe(checklist, use_container_width=True)
    st.info(
        "Al terminar esta fase, la app ya puede traer estudiantes y generar una primera base individual. "
        "La siguiente fase será calcular avance esperado, brecha, nivel de riesgo y guardar el corte en Supabase."
    )
