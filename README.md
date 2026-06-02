# Plataforma Académica AVE UVG - Fase 2

## Qué incluye esta fase

Esta versión agrega la carga académica inicial desde Canvas:

- Token de Canvas desde la interfaz.
- Selección de varias aulas Canvas como secciones consolidadas.
- Carga de estudiantes inscritos.
- Carga de último ingreso y tiempo total de actividad.
- Carga de actividades/tareas del curso.
- Carga de módulos del curso.
- Carga de entregas/submissions cuando el token tiene permisos.
- Cálculo de avance real básico.
- Clasificación base inicial:
  - Nunca ingresó al curso.
  - Ingresó pero no inició actividades.
  - Inició y se quedó en el primer módulo.
  - Avance parcial registrado.
- Dashboard inicial.
- Descarga CSV de la base individual.

## Cómo ejecutar

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Crear archivo de secretos:

Copiar:

```text
.streamlit/secrets.toml.example
```

como:

```text
.streamlit/secrets.toml
```

3. Colocar credenciales de Supabase si se desea probar la conexión.

4. Ejecutar:

```bash
streamlit run app.py
```

## Flujo de uso

1. Ir a **Configuración**.
2. Pegar token personal de Canvas.
3. Probar conexión con Canvas.
4. Ir a **Selección de aulas/secciones**.
5. Cargar cursos desde Canvas.
6. Filtrar por nombre del curso, por ejemplo `Matemáticas`.
7. Seleccionar una o varias aulas/secciones Canvas.
8. Ir a **Carga académica Fase 2**.
9. Seleccionar rango de fechas.
10. Cargar datos académicos.
11. Revisar el **Dashboard inicial**.

## Nota importante

Algunos endpoints de Canvas dependen de permisos del token. Si la app puede traer estudiantes pero no entregas o módulos, mostrará una advertencia y continuará con la información disponible.

## Próxima fase

La Fase 3 incluirá:

- Avance esperado según fecha del curso.
- Brecha de avance.
- Modelo de riesgo académico.
- Ranking de causas de riesgo.
- Registro de cortes históricos en Supabase.
- Comparación contra reporte anterior.
