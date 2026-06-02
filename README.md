# Plataforma Académica AVE UVG - Fase 1

Esta primera fase incluye:

- Conexión con Canvas LMS.
- Conexión con Supabase.
- Carga de cursos desde Canvas.
- Carga de secciones por curso.
- Selección múltiple de secciones.
- Estilos iniciales con colores AVE UVG.

## Instalación local

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Crear el archivo real de secretos:

Copiar:

```bash
.streamlit/secrets.toml.example
```

como:

```bash
.streamlit/secrets.toml
```

3. Completar credenciales:

```toml
[canvas]
base_url = "https://uvg.instructure.com"
token = "PEGAR_AQUI_TOKEN_CANVAS"

[supabase]
url = "PEGAR_AQUI_URL_SUPABASE"
key = "PEGAR_AQUI_SUPABASE_KEY"
```

4. Ejecutar:

```bash
streamlit run app.py
```

## Importante

El archivo `secrets.toml` real no se incluye por seguridad. Solo se incluye `secrets.toml.example`.
