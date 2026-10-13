"""Utilidades compartidas por los scripts paso a paso.

Cada paso guarda su resultado en reports/cache/ para que el siguiente lo use.
Así cada script se puede correr por separado, en orden, y mostrar sus resultados.
"""
import os, sys, json, pickle, argparse
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1'); os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
sys.path.insert(0, str(ROOT))
CACHE = ROOT / 'reports/cache'


def config(argv=None, reps=False):
    p = argparse.ArgumentParser()
    if reps: p.add_argument('--bootstrap-reps', type=int, default=None, help='réplicas bootstrap (por defecto, las de config.json)')
    a = p.parse_args(argv)
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    if reps and a.bootstrap_reps: cfg['bootstrap_reps'] = a.bootstrap_reps
    (ROOT / 'data/processed').mkdir(parents=True, exist_ok=True)
    for d in ['tables', 'figures', 'cache']: (ROOT / 'reports' / d).mkdir(parents=True, exist_ok=True)
    return cfg


def guardar(nombre, obj):
    with open(CACHE / f'{nombre}.pkl', 'wb') as f: pickle.dump(obj, f)


def cargar(nombre, paso):
    f = CACHE / f'{nombre}.pkl'
    if not f.exists(): sys.exit(f'Falta el resultado de {paso}. Córralo primero.')
    with open(f, 'rb') as fh: return pickle.load(fh)


def titulo(t):
    print('\n' + '=' * 70 + f'\n{t}\n' + '=' * 70)
