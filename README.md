# Plataforma Académica AVE UVG - Fase 4.1

Esta versión incorpora el **reporte ejecutivo PDF avanzado** para análisis académico en AVE UVG.

## Incluye

- Conexión con Canvas mediante token ingresado desde la interfaz.
- Selección multicurso/aulas como secciones consolidadas.
- Diagnóstico Canvas.
- Carga académica de estudiantes, actividades, módulos y entregas.
- Cálculo de avance esperado, avance real y brecha.
- Clasificación de riesgo académico.
- Guardado de cortes históricos en Supabase.
- Comparación con reporte anterior.
- PDF ejecutivo enriquecido con:
  - indicadores generales;
  - gráficas de riesgo;
  - estados académicos del estudiantado;
  - velocidad de avance;
  - brecha real vs esperada;
  - comparación entre cohortes/secciones;
  - tendencia respecto al reporte anterior;
  - ranking de causas de riesgo;
  - estudiantes priorizados para seguimiento;
  - marca de agua del desarrollador.

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Supabase

Si ya ejecutaste `database/schema_fase3.sql` en una fase anterior, no necesitas recrear las tablas.

Configura `.streamlit/secrets.toml` con:

```toml
[supabase]
url = "https://TU-PROYECTO.supabase.co"
key = "TU_SERVICE_ROLE_KEY"
```

## Nota

Para que el PDF muestre tendencia histórica, primero debe existir al menos un corte guardado previamente en Supabase para el mismo curso consolidado.

## Actualización Fase 4.2

Se agregó un segundo reporte PDF independiente: **Reporte de estudiantes pendientes y sin ingreso**.

Este reporte se genera desde el menú **9. Reporte de estudiantes pendientes** e incluye:

- estudiantes que nunca ingresaron al curso;
- estudiantes que ingresaron pero no iniciaron actividades;
- estudiantes con actividades pendientes;
- estudiantes con brecha de avance relevante;
- resumen por aula/sección;
- listado operativo con correo, estado, avance, brecha, pendientes, última actividad y acción sugerida.

El reporte ejecutivo principal se mantiene en el menú 8 y este nuevo reporte operativo queda separado para seguimiento académico directo.
