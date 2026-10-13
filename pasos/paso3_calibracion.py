"""PASO 3 · Calibración, sesgo favorito–longshot, ligas y temporadas (pregunta principal y secundarias 1 y 2).

Uso:  python pasos/paso3_calibracion.py [--bootstrap-reps 200]      (requiere el paso 1)
"""
from _comun import ROOT, config, cargar, guardar, titulo
from src.analysis import analyze

cfg = config(reps=True)
d = cargar('paso1', 'pasos/paso1_datos.py')
titulo(f'PASO 3 · Calibración (bootstrap por bloques, {cfg["bootstrap_reps"]} réplicas)')
t = analyze(ROOT, cfg, d['matches'], d['y'], d['cubes'], d['params'])
guardar('paso3', dict(tables=t, cfg=cfg))

b = t['bias'].query('season=="all"')
print('Pendiente del error (pp por cada 10 pp de probabilidad; positiva = sesgo favorito–longshot):')
print(b.pivot_table(index=['league', 'operator'], columns='method', values='estimate').round(2).to_string())
print(f'\nPendientes significativas tras Holm: {int((b.p_holm < .05).sum())} de {len(b)}')
e = t['bin_sensitivity'].query('bins==10 and scheme=="equal_frequency"')
print('\nError medio de calibración por resultado, ECE (pp):')
print(e.pivot_table(index=['league', 'operator'], columns='method', values='macro_ece_pp').round(2).to_string())
s = t['scores'].query('season=="all" and method=="power"')
print('\nHabilidad RPS frente a la frecuencia histórica (potencia):'); print(s[['league', 'operator', 'rps', 'rpss']].round(4).to_string(index=False))
lg = t['league_differences'].query('season=="all"'); sd = t['season_differences']
print(f'\nSecundaria 1 · diferencias entre ligas significativas tras Holm: {int((lg.p_holm < .05).sum())} de {len(lg)}')
print(f'Secundaria 2 · diferencias entre temporadas significativas tras Holm: {int((sd.p_holm < .05).sum())} de {len(sd)}')
print('\nTablas guardadas en reports/tables/ (bias.csv, scores.csv, league_differences.csv, season_differences.csv, ...)')
