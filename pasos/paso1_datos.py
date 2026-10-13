"""PASO 1 · Lectura y validación de los datos (Premier League y LaLiga, 2022/23–2024/25).

Uso (desde la carpeta del proyecto):  python pasos/paso1_datos.py
"""
from _comun import ROOT, config, guardar, titulo
from src.data import load_data

cfg = config()
titulo('PASO 1 · Lectura y validación de los datos')
matches, y, cubes, params, base, manifest, coverage, excluded = load_data(ROOT, cfg)
base.to_csv(ROOT / 'data/processed/analytic.csv', index=False)
matches[['match_id', 'league', 'season', 'date', 'HomeTeam', 'AwayTeam', 'FTR', 'home_goals', 'away_goals']].to_csv(ROOT / 'data/processed/matches.csv', index=False)
manifest.to_csv(ROOT / 'data/source_manifest.csv', index=False)
coverage.to_csv(ROOT / 'reports/tables/coverage.csv', index=False); excluded.to_csv(ROOT / 'reports/tables/exclusions.csv', index=False)
guardar('paso1', dict(matches=matches, y=y, cubes=cubes, params=params, base=base))

print(f'Archivos leídos: {len(manifest)}  ·  partidos válidos: {len(matches)}  ·  registros partido–casa: {len(base)}')
print(f'Partidos excluidos: {len(excluded)}')
print('\nCobertura de cuotas de cierre por liga, temporada y casa:')
print(coverage[['league', 'season', 'operator', 'matches', 'eligible', 'coverage_pct']].to_string(index=False))
print('\nResultados observados (% local / empate / visitante):')
print((100 * matches.groupby('league').FTR.value_counts(normalize=True).unstack()[['H', 'D', 'A']]).round(1).to_string())
print('\nGuardado: data/processed/analytic.csv, data/processed/matches.csv, reports/tables/coverage.csv')
