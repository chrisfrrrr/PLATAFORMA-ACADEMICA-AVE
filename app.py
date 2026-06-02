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
    run_canvas_diagnostics,
)
from modules.supabase_client import test_supabase_connection, save_report_snapshot, get_previous_report
from modules.academic_metrics import (
    consolidate_datasets,
    add_expected_gap_and_risk,
    build_summary,
    risk_ranking,
    section_comparison,
)
from modules.ui_styles import apply_ave_styles, metric_card
from modules.report_pdf import generate_executive_pdf, generate_pending_students_pdf

st.set_page_config(page_title="Plataforma Académica AVE - Fase 4.2", page_icon="📊", layout="wide")
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
st.session_state.setdefault("summary", {})
st.session_state.setdefault("course_consolidated_name", "")
st.session_state.setdefault("last_saved_report_id", None)

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
        Fase 4.1: reporte ejecutivo PDF enriquecido con gráficas, tendencias, cohortes y ranking de causas.
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
        "3. Diagnóstico Canvas",
        "4. Carga académica",
        "5. Análisis Fase 4.1",
        "6. Guardar corte histórico",
        "7. Dashboard ejecutivo",
        "8. Reporte PDF ejecutivo",
        "9. Reporte de estudiantes pendientes",
        "10. Resumen de Fase 4.1",
    ],
)

# -------------------------------------------------------------------
# 1. Configuración
# -------------------------------------------------------------------
if menu == "1. Configuración":
    st.header("1. Configuración de conexiones")
    st.write("Cada asesor puede ingresar su token personal de Canvas directamente desde la aplicación.")

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
        st.write("Supabase se mantiene en secrets porque representa la base institucional de reportes históricos.")
        if st.button("Probar conexión con Supabase"):
            ok, result = test_supabase_connection()
            if ok:
                st.success(result)
            else:
                st.error("No se pudo conectar con Supabase.")
                st.write(result)
        st.caption("Para guardar cortes históricos, primero ejecuta el SQL incluido en database/schema_fase3.sql.")

# -------------------------------------------------------------------
# 2. Selección de aulas/secciones
# -------------------------------------------------------------------
elif menu == "2. Selección de aulas/secciones":
    st.header("2. Selección de aulas Canvas que se unificarán como secciones")
    st.info("Selecciona una o varias aulas Canvas para analizarlas juntas como un mismo curso académico.")

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
            {"id": c.get("id"), "nombre": c.get("name"), "codigo": c.get("course_code"), "estado": c.get("workflow_state"), "total_estudiantes": c.get("total_students")}
            for c in courses if c.get("name")
        ])
        filtro = st.text_input("Filtrar cursos por nombre", value="")
        view_df = courses_df[courses_df["nombre"].str.contains(filtro, case=False, na=False)] if filtro else courses_df
        st.dataframe(view_df, use_container_width=True, height=280)

        options = {f'{r["nombre"]} | ID: {r["id"]}': int(r["id"]) for _, r in view_df.iterrows()}
        selected = st.multiselect("Seleccione una o varias aulas/secciones Canvas para consolidar", options=list(options.keys()), default=st.session_state.get("selected_course_labels", []))
        st.session_state["selected_course_labels"] = selected
        st.session_state["selected_course_ids"] = [options[s] for s in selected]

        curso_nombre = st.text_input("Nombre del curso consolidado para el reporte", value=st.session_state.get("course_consolidated_name") or (filtro.strip() if filtro else "Curso consolidado AVE"))
        st.session_state["course_consolidated_name"] = curso_nombre.strip() or "Curso consolidado AVE"

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
# 3. Diagnóstico Canvas
# -------------------------------------------------------------------
elif menu == "3. Diagnóstico Canvas":
    st.header("3. Diagnóstico de permisos y endpoints de Canvas")
    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])
    if not selected_ids:
        st.warning("Primero selecciona al menos un aula/sección en el menú 2.")
        st.stop()

    options_diag = {label: cid for label, cid in zip(selected_labels, selected_ids)}
    selected_label_diag = st.selectbox("Seleccione un aula/sección para diagnosticar", options=list(options_diag.keys()))
    selected_course_diag = options_diag[selected_label_diag]
    st.code(selected_label_diag)

    if st.button("Ejecutar diagnóstico Canvas"):
        with st.spinner("Probando endpoints de Canvas..."):
            results, details = run_canvas_diagnostics(selected_course_diag)
        diag_df = pd.DataFrame(results)
        st.dataframe(diag_df, use_container_width=True, height=360)
        disponibles = int((diag_df["estado"] == "Disponible").sum())
        no_disponibles = int((diag_df["estado"] != "Disponible").sum())
        c1, c2 = st.columns(2)
        c1.success(f"Recursos disponibles: {disponibles}")
        c2.warning(f"Recursos no disponibles: {no_disponibles}")
        if not diag_df[diag_df["recurso"].str.contains("Entregas") & (diag_df["estado"] == "Disponible")].empty:
            st.success("El token sí tiene acceso a rutas de entregas. Puede calcularse avance académico con mayor precisión.")
        with st.expander("Ver detalles técnicos devueltos por Canvas"):
            st.caption("No se muestra el token. Solo se presentan respuestas o errores del API.")
            st.json(details)

# -------------------------------------------------------------------
# 4. Carga académica
# -------------------------------------------------------------------
elif menu == "4. Carga académica":
    st.header("4. Carga académica desde Canvas")
    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])
    if not selected_ids:
        st.warning("Primero selecciona aulas/secciones en el menú 2.")
        st.stop()

    st.write("Aulas/secciones seleccionadas:")
    st.dataframe(pd.DataFrame({"aula_seccion": selected_labels, "canvas_course_id": selected_ids}), use_container_width=True)

    if st.button("Cargar datos académicos desde Canvas"):
        datasets = []
        with st.spinner("Cargando estudiantes, actividades, módulos y entregas..."):
            for label, course_id in zip(selected_labels, selected_ids):
                course_name = label.split(" | ID:")[0]
                ok, payload = collect_course_dataset(course_id, course_name)
                if ok:
                    datasets.append(payload)
                    st.success(f"Datos cargados: {course_name}")
                    if payload.get("submissions_warning"):
                        st.warning(f"{course_name}: {payload.get('submissions_warning')}")
                else:
                    st.error(f"No se pudo cargar {course_name}")
                    st.write(payload)
        st.session_state["datasets"] = datasets
        raw_df = consolidate_datasets(datasets)
        st.session_state["student_metrics_df"] = raw_df
        st.success(f"Carga completada. Se consolidaron {len(raw_df)} registros de estudiantes.")
        st.dataframe(raw_df, use_container_width=True, height=360)

# -------------------------------------------------------------------
# 5. Análisis Fase 4.1
# -------------------------------------------------------------------
elif menu == "5. Análisis Fase 4.1":
    st.header("5. Análisis de avance, brecha y riesgo académico")
    raw_df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if raw_df.empty:
        st.warning("Primero realiza la carga académica en el menú 4.")
        st.stop()

    st.subheader("Parámetros del corte académico")
    today = date.today()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        fecha_inicio_curso = st.date_input("Fecha de inicio del curso", value=today - timedelta(days=21))
    with c2:
        fecha_fin_curso = st.date_input("Fecha de finalización del curso", value=today + timedelta(days=21))
    with c3:
        fecha_corte = st.date_input("Fecha de corte", value=today)
    with c4:
        dias_inactividad = st.number_input("Días para alerta de inactividad", min_value=1, max_value=30, value=5)

    if st.button("Calcular análisis Fase 4.1"):
        df = add_expected_gap_and_risk(raw_df, fecha_inicio_curso, fecha_fin_curso, fecha_corte, int(dias_inactividad))
        summary = build_summary(df)
        st.session_state["student_metrics_df"] = df
        st.session_state["summary"] = summary
        st.session_state["fase3_params"] = {
            "fecha_inicio_curso": str(fecha_inicio_curso),
            "fecha_fin_curso": str(fecha_fin_curso),
            "fecha_corte": str(fecha_corte),
            "dias_inactividad": int(dias_inactividad),
        }
        st.success("Análisis Fase 4.1 calculado correctamente.")

    df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if "nivel_riesgo" in df.columns:
        summary = st.session_state.get("summary") or build_summary(df)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Estudiantes", summary["total_estudiantes"], "Total consolidado")
        with m2:
            metric_card("Avance esperado", f'{summary["avance_esperado_promedio"]}%', "Según fecha de corte")
        with m3:
            metric_card("Avance real", f'{summary["avance_real_promedio"]}%', "Promedio Canvas")
        with m4:
            metric_card("Brecha", f'{summary["brecha_promedio"]}%', "Esperado - real")

        r1, r2, r3 = st.columns(3)
        with r1:
            metric_card("Riesgo bajo", summary["riesgo_bajo"], "Seguimiento regular")
        with r2:
            metric_card("Riesgo medio", summary["riesgo_medio"], "Seguimiento preventivo")
        with r3:
            metric_card("Riesgo alto", summary["riesgo_alto"], "Atención prioritaria")

        st.subheader("Ranking de causas de riesgo")
        rank_df = risk_ranking(df)
        st.dataframe(rank_df, use_container_width=True)
        if not rank_df.empty:
            st.bar_chart(rank_df.set_index("causa_riesgo")["cantidad"])

        st.subheader("Comparación por aula/sección")
        sec_df = section_comparison(df)
        st.dataframe(sec_df, use_container_width=True)

        st.subheader("Base individual con riesgo")
        st.dataframe(df, use_container_width=True, height=420)
        st.download_button(
            "Descargar base individual CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="base_individual_riesgo_ave.csv",
            mime="text/csv",
        )
    else:
        st.info("Configura los parámetros y presiona 'Calcular análisis Fase 4.1'.")

# -------------------------------------------------------------------
# 6. Guardar corte histórico
# -------------------------------------------------------------------
elif menu == "6. Guardar corte histórico":
    st.header("6. Guardar corte histórico en Supabase")
    df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if df.empty or "nivel_riesgo" not in df.columns:
        st.warning("Primero calcula el análisis Fase 4.1 en el menú 5.")
        st.stop()

    params = st.session_state.get("fase3_params", {})
    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])
    course_name = st.session_state.get("course_consolidated_name") or "Curso consolidado AVE"

    c1, c2 = st.columns(2)
    with c1:
        nombre_reporte = st.text_input("Nombre del reporte", value=f"Corte {course_name} - {date.today().isoformat()}")
        usuario_generador = st.text_input("Usuario generador", value="Asesor Académico AVE")
    with c2:
        fecha_inicio_analisis = st.date_input("Inicio del rango analizado", value=date.today() - timedelta(days=7))
        fecha_fin_analisis = st.date_input("Fin del rango analizado", value=date.today())

    st.info("Antes de guardar, confirma que ejecutaste el archivo database/schema_fase3.sql en Supabase.")

    if st.button("Guardar corte en Supabase"):
        aulas_canvas = [{"label": l, "canvas_course_id": cid} for l, cid in zip(selected_labels, selected_ids)]
        summary = st.session_state.get("summary") or build_summary(df)
        keep_cols = [
            "canvas_course_id", "curso_aula", "canvas_user_id", "nombre", "correo", "section_id", "estado_inscripcion",
            "ultimo_ingreso", "ultima_entrega", "ultima_actividad", "dias_sin_actividad", "tiempo_total_min",
            "actividades_total", "actividades_completadas", "actividades_pendientes", "avance_real_pct", "avance_esperado_pct",
            "brecha_pct", "modulo_maximo", "modulo_maximo_nombre", "estado_base", "puntaje_riesgo", "nivel_riesgo",
            "causa_principal_riesgo", "causas_riesgo", "recomendacion",
        ]
        rows = df[[c for c in keep_cols if c in df.columns]].to_dict(orient="records")
        ok, result = save_report_snapshot(
            nombre_reporte=nombre_reporte,
            curso_consolidado=course_name,
            fecha_inicio_analisis=str(fecha_inicio_analisis),
            fecha_fin_analisis=str(fecha_fin_analisis),
            fecha_inicio_curso=params.get("fecha_inicio_curso", str(fecha_inicio_analisis)),
            fecha_fin_curso=params.get("fecha_fin_curso", str(fecha_fin_analisis)),
            aulas_canvas=aulas_canvas,
            resumen=summary,
            student_rows=rows,
            usuario_generador=usuario_generador,
        )
        if ok:
            st.session_state["last_saved_report_id"] = result.get("reporte_id")
            st.success(f"Corte guardado correctamente. ID de reporte: {result.get('reporte_id')}. Estudiantes guardados: {result.get('estudiantes_guardados')}.")
        else:
            st.error("No se pudo guardar el corte histórico.")
            st.write(result)

    st.subheader("Comparar con reporte anterior")
    if st.button("Buscar reporte anterior en Supabase"):
        ok, previous = get_previous_report(course_name, st.session_state.get("last_saved_report_id"))
        if ok:
            st.success(f"Reporte anterior encontrado: {previous.get('nombre_reporte')}")
            prev_summary = previous.get("resumen") or {}
            current = st.session_state.get("summary") or build_summary(df)
            comp = pd.DataFrame([
                {"indicador": "Avance real promedio", "anterior": prev_summary.get("avance_real_promedio"), "actual": current.get("avance_real_promedio")},
                {"indicador": "Brecha promedio", "anterior": prev_summary.get("brecha_promedio"), "actual": current.get("brecha_promedio")},
                {"indicador": "Riesgo alto", "anterior": prev_summary.get("riesgo_alto"), "actual": current.get("riesgo_alto")},
                {"indicador": "Nunca ingresó", "anterior": prev_summary.get("nunca_ingreso"), "actual": current.get("nunca_ingreso")},
            ])
            st.dataframe(comp, use_container_width=True)
        else:
            st.warning(previous)

# -------------------------------------------------------------------
# 7. Dashboard ejecutivo
# -------------------------------------------------------------------
elif menu == "7. Dashboard ejecutivo":
    st.header("7. Dashboard ejecutivo")
    df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if df.empty or "nivel_riesgo" not in df.columns:
        st.warning("Primero calcula el análisis Fase 4.1 en el menú 5.")
        st.stop()
    summary = st.session_state.get("summary") or build_summary(df)

    st.subheader(st.session_state.get("course_consolidated_name") or "Curso consolidado AVE")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total estudiantes", summary["total_estudiantes"])
    c2.metric("Avance real promedio", f'{summary["avance_real_promedio"]}%')
    c3.metric("Avance esperado", f'{summary["avance_esperado_promedio"]}%')
    c4.metric("Brecha promedio", f'{summary["brecha_promedio"]}%')

    st.subheader("Distribución de riesgo")
    risk_dist = df["nivel_riesgo"].value_counts().reindex(["Bajo", "Medio", "Alto"]).fillna(0).astype(int)
    st.bar_chart(risk_dist)

    st.subheader("Estudiantes en riesgo alto")
    high = df[df["nivel_riesgo"] == "Alto"].sort_values(["puntaje_riesgo", "brecha_pct"], ascending=False)
    cols = ["nombre", "correo", "curso_aula", "avance_real_pct", "avance_esperado_pct", "brecha_pct", "dias_sin_actividad", "causa_principal_riesgo", "recomendacion"]
    st.dataframe(high[[c for c in cols if c in high.columns]], use_container_width=True, height=360)

# -------------------------------------------------------------------
# 8. Reporte PDF ejecutivo
# -------------------------------------------------------------------
elif menu == "8. Reporte PDF ejecutivo":
    st.header("8. Reporte PDF ejecutivo")
    df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if df.empty or "nivel_riesgo" not in df.columns:
        st.warning("Primero calcula el análisis Fase 4.1 en el menú 5.")
        st.stop()

    summary = st.session_state.get("summary") or build_summary(df)
    params = st.session_state.get("fase3_params", {})
    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])
    course_name = st.session_state.get("course_consolidated_name") or "Curso consolidado AVE"

    st.markdown(
        """
        Este módulo genera un PDF ejecutivo enriquecido con gráficas, resumen del curso,
        estados académicos, velocidad de avance, comparación entre cohortes/secciones,
        tendencia frente al reporte anterior, ranking de causas y estudiantes priorizados.
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        nombre_reporte_pdf = st.text_input(
            "Nombre del reporte PDF",
            value=f"Reporte ejecutivo {course_name} - {date.today().isoformat()}",
        )
        usuario_generador_pdf = st.text_input(
            "Responsable / usuario generador",
            value="Ing. Christian Pocol - Asesor Académico AVE",
        )
    with c2:
        fecha_inicio_pdf = st.date_input("Inicio del rango del PDF", value=date.today() - timedelta(days=7))
        fecha_fin_pdf = st.date_input("Fin del rango del PDF", value=date.today())

    st.subheader("Vista previa de indicadores incluidos")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Estudiantes", summary.get("total_estudiantes", 0))
    m2.metric("Avance real", f'{summary.get("avance_real_promedio", 0)}%')
    m3.metric("Brecha", f'{summary.get("brecha_promedio", 0)}%')
    m4.metric("Riesgo alto", summary.get("riesgo_alto", 0))

    aulas_canvas = [{"label": l, "canvas_course_id": cid} for l, cid in zip(selected_labels, selected_ids)]

    incluir_tendencia = st.checkbox("Incluir tendencia respecto al reporte anterior guardado en Supabase", value=True)
    previous_report_pdf = None
    if incluir_tendencia:
        ok_prev, prev = get_previous_report(course_name, st.session_state.get("last_saved_report_id"))
        if ok_prev:
            previous_report_pdf = prev
            st.success(f"Se incluirá tendencia con el reporte anterior: {prev.get('nombre_reporte')}")
        else:
            st.info("No se encontró reporte anterior. El PDF indicará que no existe corte previo disponible.")

    if st.button("Generar PDF ejecutivo avanzado"):
        try:
            pdf_bytes = generate_executive_pdf(
                df=df,
                summary=summary,
                course_name=course_name,
                report_name=nombre_reporte_pdf,
                fecha_inicio_analisis=str(fecha_inicio_pdf),
                fecha_fin_analisis=str(fecha_fin_pdf),
                fecha_corte=params.get("fecha_corte", str(fecha_fin_pdf)),
                usuario_generador=usuario_generador_pdf,
                aulas_canvas=aulas_canvas,
                logo_path="assets/logo_ave.jpg",
                previous_report=previous_report_pdf,
            )
            st.session_state["last_pdf_bytes"] = pdf_bytes
            st.success("PDF ejecutivo avanzado generado correctamente.")
        except Exception as e:
            st.error("No se pudo generar el PDF ejecutivo.")
            st.exception(e)

    if st.session_state.get("last_pdf_bytes"):
        safe_name = (nombre_reporte_pdf or "reporte_ejecutivo_ave").replace(" ", "_").replace("/", "-")
        st.download_button(
            "Descargar reporte ejecutivo PDF",
            data=st.session_state["last_pdf_bytes"],
            file_name=f"{safe_name}.pdf",
            mime="application/pdf",
        )
        st.info("El PDF incluye gráficas, colores AVE y marca de agua: Desarrollador Ing. Christian Pocol - Asesor Académico AVE.")

# -------------------------------------------------------------------
# 9. Resumen
# -------------------------------------------------------------------
elif menu == "9. Reporte de estudiantes pendientes":
    st.header("9. Reporte de estudiantes pendientes y sin ingreso")
    df = st.session_state.get("student_metrics_df", pd.DataFrame())
    if df.empty or "nivel_riesgo" not in df.columns:
        st.warning("Primero calcula el análisis Fase 4.1 en el menú 5.")
        st.stop()

    summary = st.session_state.get("summary") or build_summary(df)
    params = st.session_state.get("fase3_params", {})
    selected_ids = st.session_state.get("selected_course_ids", [])
    selected_labels = st.session_state.get("selected_course_labels", [])
    course_name = st.session_state.get("course_consolidated_name") or "Curso consolidado AVE"

    st.markdown(
        """
        Este segundo reporte está diseñado para seguimiento operativo. Incluye a estudiantes que nunca ingresaron,
        ingresaron pero no iniciaron actividades, tienen actividades pendientes o presentan brecha de avance.
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        nombre_reporte_pend = st.text_input(
            "Nombre del reporte de pendientes",
            value=f"Reporte estudiantes pendientes {course_name} - {date.today().isoformat()}",
        )
        usuario_generador_pend = st.text_input(
            "Responsable / usuario generador",
            value="Ing. Christian Pocol - Asesor Académico AVE",
            key="usuario_generador_pendientes",
        )
    with c2:
        fecha_inicio_pend = st.date_input("Inicio del rango", value=date.today() - timedelta(days=7), key="fecha_inicio_pendientes")
        fecha_fin_pend = st.date_input("Fin del rango", value=date.today(), key="fecha_fin_pendientes")

    # Vista previa del universo operativo
    preview = df.copy()
    mask = preview.get("nunca_ingreso", False).astype(bool) | preview.get("ingreso_no_inicio", False).astype(bool)
    if "actividades_pendientes" in preview.columns:
        mask = mask | (pd.to_numeric(preview["actividades_pendientes"], errors="coerce").fillna(0) > 0)
    if "brecha_pct" in preview.columns:
        mask = mask | (pd.to_numeric(preview["brecha_pct"], errors="coerce").fillna(0) >= 15)
    if "nivel_riesgo" in preview.columns:
        mask = mask | preview["nivel_riesgo"].astype(str).isin(["Alto", "Medio"])
    preview = preview[mask].copy()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pendientes priorizados", len(preview))
    m2.metric("Nunca ingresaron", int(preview.get("nunca_ingreso", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not preview.empty else 0)
    m3.metric("Ingresaron sin iniciar", int(preview.get("ingreso_no_inicio", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not preview.empty else 0)
    m4.metric("Riesgo alto/medio", int(preview["nivel_riesgo"].astype(str).isin(["Alto", "Medio"]).sum()) if not preview.empty and "nivel_riesgo" in preview else 0)

    cols = ["nombre", "correo", "curso_aula", "estado_base", "avance_real_pct", "avance_esperado_pct", "brecha_pct", "actividades_pendientes", "ultima_actividad", "causa_principal_riesgo", "recomendacion"]
    st.subheader("Vista previa de estudiantes incluidos")
    st.dataframe(preview[[c for c in cols if c in preview.columns]].head(100), use_container_width=True, height=340)

    aulas_canvas = [{"label": l, "canvas_course_id": cid} for l, cid in zip(selected_labels, selected_ids)]

    if st.button("Generar PDF de estudiantes pendientes"):
        try:
            pdf_bytes = generate_pending_students_pdf(
                df=df,
                summary=summary,
                course_name=course_name,
                report_name=nombre_reporte_pend,
                fecha_inicio_analisis=str(fecha_inicio_pend),
                fecha_fin_analisis=str(fecha_fin_pend),
                fecha_corte=params.get("fecha_corte", str(fecha_fin_pend)),
                usuario_generador=usuario_generador_pend,
                aulas_canvas=aulas_canvas,
                logo_path="assets/logo_ave.jpg",
            )
            st.session_state["last_pending_pdf_bytes"] = pdf_bytes
            st.success("PDF de estudiantes pendientes generado correctamente.")
        except Exception as e:
            st.error("No se pudo generar el PDF de estudiantes pendientes.")
            st.exception(e)

    if st.session_state.get("last_pending_pdf_bytes"):
        safe_name = (nombre_reporte_pend or "reporte_estudiantes_pendientes_ave").replace(" ", "_").replace("/", "-")
        st.download_button(
            "Descargar reporte de estudiantes pendientes PDF",
            data=st.session_state["last_pending_pdf_bytes"],
            file_name=f"{safe_name}.pdf",
            mime="application/pdf",
        )
        st.info("Este reporte es independiente del reporte ejecutivo y está orientado al seguimiento operativo de estudiantes.")

# -------------------------------------------------------------------
# 10. Resumen
# -------------------------------------------------------------------
elif menu == "10. Resumen de Fase 4.1":
    st.header("10. Resumen de Fase 4.1")
    st.write("Esta fase enriquece el reporte PDF con gráficas, estados académicos, tendencias, cohortes y ranking de causas.")
    checklist = pd.DataFrame([
        {"Elemento": "Selección multicurso/secciones", "Estado": "Implementado"},
        {"Elemento": "Carga de estudiantes, actividades, módulos y entregas", "Estado": "Implementado"},
        {"Elemento": "Avance esperado según fecha de corte", "Estado": "Implementado"},
        {"Elemento": "Avance real y brecha", "Estado": "Implementado"},
        {"Elemento": "Puntaje de riesgo académico", "Estado": "Implementado"},
        {"Elemento": "Ranking de causas de riesgo", "Estado": "Implementado"},
        {"Elemento": "Comparación por aula/sección", "Estado": "Implementado"},
        {"Elemento": "Guardado de corte histórico en Supabase", "Estado": "Implementado"},
        {"Elemento": "Comparación con reporte anterior", "Estado": "Inicial"},
        {"Elemento": "Reporte ejecutivo PDF enriquecido con gráficas", "Estado": "Implementado"},
    ])
    st.dataframe(checklist, use_container_width=True)
    st.info("La Fase 4.1 implementa el PDF ejecutivo avanzado con colores AVE, marca de agua, gráficas, tendencia histórica, comparación por cohortes/secciones y ranking de causas de riesgo.")
