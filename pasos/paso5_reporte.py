"""PASO 5 · Figuras y reporte HTML (reports/index.html).

Uso:  python pasos/paso5_reporte.py      (requiere los pasos 1, 3 y 4)
"""
import json, platform, webbrowser
from _comun import ROOT, config, cargar, titulo
from src.report import build_report

cfg = config()
d = cargar('paso1', 'pasos/paso1_datos.py'); p3 = cargar('paso3', 'pasos/paso3_calibracion.py'); p4 = cargar('paso4', 'pasos/paso4_publico_local.py')
titulo('PASO 5 · Figuras y reporte')
build_report(ROOT, p3['cfg'], d['matches'], d['y'], d['cubes'], d['params'], p3['tables'], p4['tables'])
(ROOT / 'reports/run_metadata.json').write_text(json.dumps(dict(python=platform.python_version(), config=p3['cfg'],
    matches=len(d['matches']), records=len(d['base'])), indent=2), encoding='utf-8')
print('Listo: reports/index.html, reports/findings.md y reports/figures/')
webbrowser.open((ROOT / 'reports/index.html').as_uri())
