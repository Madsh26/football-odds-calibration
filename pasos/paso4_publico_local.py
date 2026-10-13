"""PASO 4 · ¿Influía el público local en los resultados? (pandemia, 2017/18–2024/25)

Uso:  python pasos/paso4_publico_local.py [--bootstrap-reps 200]      (no depende de los pasos anteriores)
"""
from _comun import ROOT, config, guardar, titulo
from src.covid import load_covid, analyze_covid

cfg = config(reps=True)
titulo(f'PASO 4 · Público local y pandemia (bootstrap por bloques, {cfg["bootstrap_reps"]} réplicas)')
m, manifest, coverage = load_covid(ROOT, cfg)
manifest.to_csv(ROOT / 'data/covid_source_manifest.csv', index=False); coverage.to_csv(ROOT / 'reports/tables/covid_coverage.csv', index=False)
print(f'Partidos: {len(m)}'); print(m.groupby(['league', 'period']).size().unstack().to_string())
ct = analyze_covid(ROOT, cfg, m)
guardar('paso4', dict(tables=ct))

sh = ct['covid_share_lost']
print('\nVentaja de local (puntos del local − puntos del visitante por partido):')
print(sh[['league', 'home_adv_with_fans', 'home_adv_closed', 'estimate', 'ci_low', 'ci_high']].rename(columns={
    'home_adv_with_fans': 'con_publico', 'home_adv_closed': 'puerta_cerrada', 'estimate': '%_perdido', 'ci_low': 'IC_inf', 'ci_high': 'IC_sup'}).round(2).to_string(index=False))
c = ct['covid_contrasts'].query('contrast=="closed_minus_with_fans"')
print('\nContraste principal (puerta cerrada − con público) con Holm por liga:')
print(c[['league', 'measure', 'estimate', 'ci_low', 'ci_high', 'p_holm']].round(3).to_string(index=False))
a = ct['covid_strength_adjusted'].query('term=="HA_closed_minus_with_fans"')
print('\nAjustado por fuerza de equipo–temporada:'); print(a[['league', 'outcome', 'estimate', 'ci_low', 'ci_high', 'p_holm']].round(3).to_string(index=False))
