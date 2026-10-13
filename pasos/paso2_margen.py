"""PASO 2 · Margen de la casa y los cuatro métodos para quitarlo.

Uso:  python pasos/paso2_margen.py      (requiere el paso 1)
"""
import numpy as np, pandas as pd
from _comun import config, cargar, titulo
from src.methods import remove_margin

cfg = config()
d = cargar('paso1', 'pasos/paso1_datos.py')
m, params, cubes = d['matches'], d['params'], d['cubes']
titulo('PASO 2 · Margen y remoción del margen')
print('Margen medio por liga y casa (pp) = 100 × (1/cuota_H + 1/cuota_D + 1/cuota_A − 1):')
rows = []
for op in cfg['operators']:
    mp = params[op]['margin_pp']
    for lg in cfg['leagues']:
        mk = (m.league == lg).to_numpy()
        rows.append(dict(liga=lg, casa=op, media=mp[mk].mean(), mediana=np.median(mp[mk]), minimo=mp[mk].min(), maximo=mp[mk].max()))
print(pd.DataFrame(rows).round(2).to_string(index=False))

print('\nEjemplo didáctico: cuotas 1,40 · 4,50 · 8,00 (favorito · empate · improbable)')
q, k, z = remove_margin(np.array([[1.40, 4.50, 8.00]]))
ej = pd.DataFrame({'bruta': 1 / np.array([1.40, 4.50, 8.00]), **{met: q[met][0] for met in q}}, index=['favorito', 'empate', 'improbable'])
print((100 * ej).round(1).to_string()); print(f'Suma bruta = {100 * ej.bruta.sum():.1f} %  ·  k de potencia = {k[0]:.4f}  ·  z de Shin = {z[0]:.4f}')

print('\nComprobación: en todos los partidos y métodos las tres probabilidades suman 1:')
for op in cubes:
    for met, qq in cubes[op].items():
        print(f'  {op:5s} {met:13s} error máximo de la suma = {np.abs(qq.sum(axis=1) - 1).max():.1e}')
