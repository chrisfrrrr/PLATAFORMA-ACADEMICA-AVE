# Plataforma Académica AVE UVG - Fase 4

Esta versión incorpora el reporte ejecutivo PDF con identidad visual AVE.

## Incluye

- Token Canvas desde la interfaz.
- Selección multicurso/aulas Canvas como secciones consolidadas.
- Diagnóstico Canvas.
- Carga académica de estudiantes, actividades, módulos y entregas.
- Cálculo de avance esperado, avance real, brecha y riesgo académico.
- Ranking de causas de riesgo.
- Guardado de cortes históricos en Supabase.
- Generación de PDF ejecutivo con colores AVE y marca de agua.

## Colores AVE

- Azul: #0f1c75
- Celeste: #1c73f5
- Verde: #00ab0d
- Amarillo: #ffb500

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Supabase

Si ya ejecutaste `database/schema_fase3.sql` en la fase anterior, no necesitas crear tablas nuevas para esta fase.

## Recomendación

Usa la clave `service_role` en los secretos de Streamlit para guardar cortes históricos con RLS activado.
