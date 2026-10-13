"""Verificación independiente (sin importar el código de src/).

Recalcula desde los CSV originales, con fórmulas escritas aparte, cinco cifras
del informe y las compara con las tablas que produjo run_all.py:
  V1  partidos válidos por liga (1.140 cada una)
  V2  margen medio por liga y casa (Tabla de margen)
  V3  probabilidades del método de potencia (Σ = 1) y pendiente del error
  V4  ECE con 10 intervalos (método de potencia)
  V5  ventaja de local con y sin público en la Premier (puntos por partido)
Uso: python verificacion/verificar_independiente.py   (después de run_all.py)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / 'reports/tables'
ok_total = True


def check(nombre, propio, informe, tol):
    global ok_total
    ok = abs(propio - informe) <= tol
    ok_total &= ok
    print(f"{'OK ' if ok else 'FALLA'} {nombre}: recalculado = {propio:.4f} · tabla = {informe:.4f}")


def leer(liga):
    frames = []
    for s in ['2022-23', '2023-24', '2024-25']:
        d = pd.read_csv(ROOT / 'data/raw' / f'{liga}_{s}.csv', encoding='utf-8-sig')
        d = d[d.HomeTeam.notna() & d.FTR.isin(['H', 'D', 'A'])]
        d['season'] = s
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def potencia(p):
    k = brentq(lambda k: (p ** k).sum() - 1, 1, 10)
    return p ** k


margin = pd.read_csv(T / 'margin.csv'); bias = pd.read_csv(T / 'bias.csv'); scores = pd.read_csv(T / 'scores.csv')
for liga in ['E0', 'SP1']:
    d = leer(liga)
    check(f'V1 partidos {liga}', len(d), 1140, 0)
    for casa in ['B365', 'PS']:
        o = d[[f'{casa}CH', f'{casa}CD', f'{casa}CA']].to_numpy(float)
        p = 1 / o
        m = 100 * (p.sum(axis=1) - 1)
        ref = margin[(margin.league == liga) & (margin.season == 'all') & (margin.operator == casa)].mean_pp.iloc[0]
        check(f'V2 margen medio {liga} {casa} (pp)', m.mean(), ref, 1e-6)
        q = np.array([potencia(r) for r in p])
        y = np.column_stack([(d.FTR == r).to_numpy(float) for r in 'HDA'])
        x = (10 * q).ravel(); e = (100 * (y - q)).ravel()
        pend = np.polyfit(x, e, 1)[0]
        ref = bias[(bias.league == liga) & (bias.season == 'all') & (bias.operator == casa) & (bias.method == 'power')].estimate.iloc[0]
        check(f'V3 pendiente del error {liga} {casa}', pend, ref, 1e-6)
        ece = []
        for j in range(3):
            bordes = np.unique(np.quantile(q[:, j], np.linspace(0, 1, 11)))
            grupo = np.searchsorted(bordes[1:-1], q[:, j], side='left')
            ece.append(sum((grupo == g).mean() * abs(y[grupo == g, j].mean() - q[grupo == g, j].mean()) for g in np.unique(grupo)))
        ref = scores[(scores.league == liga) & (scores.season == 'all') & (scores.operator == casa) & (scores.method == 'power')].macro_ece_pp.iloc[0]
        check(f'V4 ECE 10 intervalos {liga} {casa} (pp)', 100 * np.mean(ece), ref, 1e-6)

# V5: público local en la Premier, 2017/18–2024/25
filas = []
for s in ['2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25']:
    carpeta = 'raw' if s in ['2022-23', '2023-24', '2024-25'] else 'raw_covid'
    d = pd.read_csv(ROOT / 'data' / carpeta / f'E0_{s}.csv', encoding='utf-8-sig')
    d = d[d.HomeTeam.notna()]
    filas.append(d)
d = pd.concat(filas, ignore_index=True)
d['fecha'] = pd.to_datetime(d.Date, dayfirst=True)
pts = np.select([d.FTR == 'H', d.FTR == 'D'], [3, 0], -3)
aforo_minimo = ((d.fecha >= '2020-12-02') & (d.fecha <= '2020-12-26')) | ((d.fecha >= '2021-05-18') & (d.fecha <= '2021-05-23'))
cerrado = (d.fecha > '2020-03-09') & (d.fecha <= '2021-07-31') & ~aforo_minimo
con_publico = (d.fecha <= '2020-03-09') | (d.fecha > '2021-07-31')
pm = pd.read_csv(T / 'covid_period_means.csv')
ref = lambda p: pm[(pm.league == 'E0') & (pm.period == p) & (pm.measure == 'points_diff')].estimate.iloc[0]
check('V5 ventaja local Premier con público (puntos)', pts[con_publico].mean(), ref('with_fans'), 1e-9)
check('V5 ventaja local Premier sin público (puntos)', pts[cerrado].mean(), ref('closed'), 1e-9)
print('\nRESULTADO:', 'todas las cifras coinciden' if ok_total else 'HAY DIFERENCIAS: revisar antes de entregar')
