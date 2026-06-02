# Plataforma Académica AVE UVG - Fase 1

Esta versión permite:

- Ingresar el token personal de Canvas desde la interfaz de Streamlit.
- Probar conexión con Canvas.
- Probar conexión con Supabase.
- Cargar cursos desde Canvas.
- Cargar secciones por curso.
- Seleccionar una o varias secciones para análisis posterior.

## Importante sobre el token de Canvas

El enlace de Canvas viene configurado de fábrica:

```text
https://uvg.instructure.com
```

Cada asesor debe pegar su token personal en la sección **1. Configuración** de la aplicación.
El token se guarda únicamente durante la sesión activa de Streamlit mediante `st.session_state`.
No se guarda en el código, no se guarda en `secrets.toml` y se puede limpiar desde la interfaz.

## Configuración de Supabase

Copiar el archivo:

```text
.streamlit/secrets.toml.example
```

como:

```text
.streamlit/secrets.toml
```

Luego colocar:

```toml
[supabase]
url = "URL_DE_SUPABASE"
key = "KEY_DE_SUPABASE"
```

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fase siguiente

La Fase 2 debe traer estudiantes, último acceso, actividades, módulos y avance real desde Canvas.
