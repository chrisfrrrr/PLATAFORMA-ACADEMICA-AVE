# Plataforma Académica AVE UVG - Fase 1

Esta versión incluye:

- Token de Canvas ingresado desde la interfaz de Streamlit.
- Conexión a Canvas LMS con URL institucional fija: `https://uvg.instructure.com`.
- Conexión a Supabase desde `secrets.toml`.
- Carga de cursos desde Canvas.
- Selección múltiple de cursos/aulas Canvas para analizarlos como secciones equivalentes.
- Consulta de secciones internas de un curso Canvas, en caso Canvas las tenga agrupadas dentro de un mismo curso.
- Colores institucionales AVE.
- Logo AVE incluido.

## Por qué hay dos formas de seleccionar secciones

Canvas puede organizar la información de dos maneras:

1. Varias secciones internas dentro de un mismo curso Canvas.
2. Cada sección como un curso/aula Canvas independiente.

En AVE parece utilizarse el segundo caso para algunos cursos, por ejemplo:

- Matemáticas - SECCIÓN - 10 - 2026 - 1
- Matemáticas - SECCIÓN - 20 - 2026 - 1

Por eso, la opción principal ahora es seleccionar varias aulas/cursos Canvas y consolidarlas para el análisis.

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuración de Supabase

Copiar:

```text
.streamlit/secrets.toml.example
```

como:

```text
.streamlit/secrets.toml
```

y completar:

```toml
[supabase]
url = "URL_DE_SUPABASE"
key = "KEY_DE_SUPABASE"
```

El token de Canvas ya no se coloca en secrets. Se pega directamente en la app.
