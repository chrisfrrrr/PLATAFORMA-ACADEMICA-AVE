# Plataforma Académica AVE UVG - Fase 3.2

Versión corregida para guardado histórico en Supabase.

## Corrección incluida

Esta versión corrige el error:

```text
invalid input syntax for type integer: "5.0"
```

El problema se producía porque algunos campos enteros provenientes de Pandas se estaban enviando a Supabase como texto decimal, por ejemplo `5.0`, aunque la tabla esperaba un `integer`.

Ahora la app limpia automáticamente:

- `NaT` -> `NULL`
- `NaN` -> `NULL`
- `5.0` -> `5` en columnas enteras
- porcentajes y métricas decimales -> `numeric`
- fechas vacías -> `NULL`

## Uso

1. Conserva tu archivo `.streamlit/secrets.toml`.
2. Ejecuta la app:

```bash
streamlit run app.py
```

3. Carga datos académicos.
4. Ejecuta el análisis de Fase 3.
5. Guarda el corte histórico en Supabase.

No es necesario volver a ejecutar `schema_fase3.sql` si las tablas ya existen.
