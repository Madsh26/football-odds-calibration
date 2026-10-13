"""Paso 6 · Robustez pedida en la revisión: dependencia, potencia, equivalencia,
umbrales del FLB, ECE nulo, aforo, placebo, cinco sustituciones e inventario de Holm.

Uso: python pasos/paso6_robustez.py [--bootstrap-reps N]
Requiere haber corrido run_all.py (o los pasos 1–5) para tener las tablas base.
"""
from _comun import ROOT, config, titulo
import time
from src.data import load_data
from src.covid import load_covid
from src.robustness import calibration_robustness, covid_robustness, hypothesis_inventory
from src.robustness_plots import robustness_plots


def main():
    cfg = config(reps=True); t0 = time.perf_counter(); tdir = ROOT / 'reports/tables'
    titulo('PASO 6 · Robustez y respuesta a la revisión')
    matches, y, cubes, params, *_ = load_data(ROOT, cfg)
    out = calibration_robustness(cfg, matches, y, cubes, params)
    cm, _, _ = load_covid(ROOT, cfg)
    out.update(covid_robustness(cfg, cm))
    for name, df in out.items(): df.to_csv(tdir / f'{name}.csv', index=False, float_format='%.12g')
    inv, fam = hypothesis_inventory(tdir)
    inv.to_csv(tdir / 'inventario_hipotesis.csv', index=False, float_format='%.12g')
    fam.to_csv(tdir / 'familias_holm.csv', index=False, float_format='%.12g')
    robustness_plots(ROOT, cfg, out)
    print(f'Listo en {time.perf_counter() - t0:.0f} s. Tablas robust_*.csv, covid_robust_*.csv, inventario_hipotesis.csv y familias_holm.csv')


if __name__ == '__main__':
    main()
