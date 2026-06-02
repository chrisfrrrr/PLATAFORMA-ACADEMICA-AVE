# Plataforma Académica AVE UVG - Fase 2.1 Diagnóstico Canvas

Esta versión agrega un módulo de diagnóstico para identificar qué endpoints de Canvas permite consultar el token del asesor.

## Incluye

- Token Canvas desde la interfaz.
- Selección multicurso/aulas como secciones consolidadas.
- Diagnóstico Canvas por aula/sección.
- Prueba de endpoints:
  - Perfil del usuario.
  - Inscripciones / estudiantes.
  - Usuarios estudiantes del curso.
  - Actividades / assignments.
  - Módulos.
  - Entregas generales agrupadas.
  - Entregas generales sin agrupar.
  - Entregas por actividad individual.
- Carga académica con fallback para entregas por actividad individual.
- Dashboard inicial.
- Exportación CSV de base individual.

## Uso

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecutar la app:

```bash
streamlit run app.py
```

3. Flujo sugerido:

- Ir a **1. Configuración**.
- Pegar token de Canvas.
- Probar conexión.
- Ir a **2. Selección de aulas/secciones**.
- Cargar cursos y seleccionar aulas.
- Ir a **3. Diagnóstico Canvas**.
- Ejecutar diagnóstico para una sección.
- Revisar qué endpoints están disponibles.
- Ir a **4. Carga académica Fase 2.1**.
- Cargar datos académicos.
- Revisar dashboard.

## Nota

Si los endpoints de entregas aparecen como no disponibles, la app puede seguir trabajando con estudiantes, último ingreso y tiempo de actividad, pero el avance por actividades quedará limitado hasta contar con permisos suficientes o una ruta de Canvas habilitada.
