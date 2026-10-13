# Registro de desarrollo

## 1 de octubre de 2026 — ampliación del periodo previo a la pandemia y cierre del proyecto

- Cuatro CSV adicionales (E0 y SP1 2017/18 y 2018/19) suministrados por el colaborador; el periodo "con público antes" pasa de ~280 a ~1.040 partidos por liga.
- Cuotas de cierre ausentes por casa se tratan como no disponibles (sin imputación); tabla `covid_coverage.csv` y tamaños efectivos por contraste.
- Modelo de ventaja de local ajustado por fuerza equipo–temporada con bootstrap por bloques (`covid_strength_adjusted.csv`) y prueba con datos sintéticos.
- Figura por temporada (`covid_seasons`), sensibilidad con solo temporadas desde 2019/20 y bloque de respuestas breves al inicio del reporte (`src/summary.py`).
- Verificación independiente: los contrastes principales se recalcularon desde los CSV crudos sin usar `src/` y coinciden.

## 1 de octubre de 2026 — pregunta secundaria 3: público local (COVID-19)

- Se verificó que los tres CSV de LaLiga 2022/23–2024/25 son idénticos (SHA-256) a la base española del desarrollo en R, y que el flujo reproduce exactamente las tablas entregadas.
- Nuevo módulo `src/covid.py` y `src/covid_report.py`: experimento natural de partidos sin público con E0 y SP1 2019/20–2024/25, usando potencia, bootstrap de bloques por liga–temporada y Holm del proyecto.
- Seis CSV adicionales en `data/raw_covid/` (E0 2019/20–2021/22 de copias locales del colaborador; SP1 2019/20–2021/22 de la base española). Huellas en `data/covid_source_manifest.csv`; fecha de descarga original desconocida.
- Sección nueva en `reports/index.html`, hallazgos en `findings.md`, seis tablas `covid_*.csv`, tres figuras `covid_*` y pruebas en `tests/test_covid.py`.
- El análisis principal (2022/23–2024/25) no cambia.

## 1 de octubre de 2026 — primera versión ejecutada

- Alcance fijado en E0/SP1, 2022/23–2024/25, cierre, B365/PS por cobertura común completa.
- Importación de copias locales y preservación de huellas; fechas de descarga desconocidas marcadas explícitamente.
- Reimplementación de proporcional, potencia, aditivo y Shin en Python, con validaciones y pruebas independientes.
- Comparaciones de métodos con grupos de extremos fijos; comprobaciones de pertenencia específica y umbrales alternativos.
- Inferencia por bloques temporales dentro de cada liga–temporada, comparaciones apareadas entre casas y familias de Holm declaradas.
- Referencia histórica dejando una temporada fuera, curvas por resultado y métricas por temporada.
- Reporte HTML autocontenido, figuras PNG/SVG, datos procesados y tablas exportadas.
- Documentación de límites, incluidos cancelación del resultado en el efecto directo del método y no identificación del reparto verdadero del margen.

El proyecto independiente excluye materiales de presentación, rúbricas, informe académico y documentos administrativos de la asignación.
