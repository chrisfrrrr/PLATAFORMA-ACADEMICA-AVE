# Plataforma Académica AVE UVG - Fase 3.1

Esta versión incluye:

- Token Canvas desde la interfaz.
- Selección de varias aulas Canvas como secciones consolidadas.
- Diagnóstico de permisos Canvas.
- Carga de estudiantes, actividades, módulos y entregas.
- Cálculo de avance esperado, avance real y brecha.
- Puntaje y nivel de riesgo académico.
- Ranking de causas de riesgo.
- Comparación por sección/aula.
- Guardado de cortes históricos en Supabase.
- Comparación inicial con reporte anterior.

## Uso local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Supabase

1. Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml`.
2. Colocar `url` y `key` de Supabase.
3. Ejecutar en Supabase SQL Editor el archivo:

```text
database/schema_fase3.sql
```

## Flujo recomendado

1. Configuración: ingresar token Canvas.
2. Selección: elegir aulas/secciones.
3. Diagnóstico: validar endpoints.
4. Carga académica: traer datos Canvas.
5. Análisis Fase 3.1: configurar fechas y calcular riesgo.
6. Guardar corte histórico: almacenar en Supabase.
7. Dashboard ejecutivo: revisar indicadores principales.


## Corrección Fase 3.1

Se corrigió el guardado histórico en Supabase para convertir valores vacíos de fecha, como NaT, a NULL antes de insertarlos en columnas timestamp.
