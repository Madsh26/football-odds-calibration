# Procedencia de datos

Fuente esperada: https://www.football-data.co.uk/englandm.php y https://www.football-data.co.uk/spainm.php.

Los CSV originales se conservan localmente en `raw/` y `raw_covid/` y se excluyen del repositorio. `processed/` contiene los datos necesarios para inspeccionar los resultados publicados. Las transformaciones y variables se explican en `../docs/DATA_DICTIONARY.md`.

`source_snapshot.csv` fija las huellas del análisis de calibración. `source_manifest.csv` y `covid_source_manifest.csv` documentan los originales utilizados. La fecha de descarga original de las copias suministradas es desconocida. No se ha supuesto una fecha retrospectiva.

Ejecute `python download_data.py` desde la raíz para obtener los archivos públicos faltantes. Las descargas nuevas registran URL, fecha UTC y SHA-256 en `downloads.json`, excluido de Git. El descargador compara las huellas históricas conocidas antes de guardar; si la fuente cambió, se detiene y solicita una revisión explícita de la versión de datos. Conservar las huellas evita presentar una ejecución con datos distintos como reproducción exacta.

Las cuotas de cierre de Bet365 no están disponibles antes de 2019/20. No se sustituyen por cuotas anteriores al cierre. Las medidas deportivas utilizan todos los partidos elegibles y cada medida de mercado usa su cobertura efectiva, documentada en `../reports/tables/covid_coverage.csv`.
